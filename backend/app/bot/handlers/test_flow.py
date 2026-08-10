"""
test_flow.py — Telegram Bot Test Flow Handler
ROOT BUG FIX:
  callback_data = ans:{question_display_order}:{answer_uuid}
  Previously was ans:{answer_idx+1}:{answer_uuid} which caused wrong question lookup!
  Now question display_order (1-15) is embedded in callback, matching AttemptQuestion.display_order.
"""
import logging
import asyncio
import time
from telegram import Update
from telegram.ext import ContextTypes
from ..keyboards import get_answer_keyboard, format_answers_text
from ..api_client import bot_api

logger = logging.getLogger(__name__)

TOPIC_SELECT = 20
TEST_IN_PROGRESS = 22
SEMINAR_CONFIRM = 23

QUESTION_TIMER = 60  # seconds


# ─── Cancel countdown helper ───────────────────────────────────────────────────
def _cancel_countdown(context: ContextTypes.DEFAULT_TYPE):
    task = context.user_data.pop("countdown_task", None)
    if task and not task.done():
        task.cancel()


# ─── Build question message text ──────────────────────────────────────────────
def _build_msg(qdata: dict, remaining: int) -> str:
    current = qdata.get("current_index", qdata.get("display_order", 1))
    q_text = qdata.get("question_text", "")
    answers = qdata.get("answers", [])
    answers_text = format_answers_text(answers)

    total_blocks = 12
    filled = min(total_blocks, remaining // 5)
    empty = total_blocks - filled
    bar = "🟩" * filled + "⬜" * empty

    return (
        f"📝 <b>Савол {current} / 15:</b>\n\n"
        f"{q_text}\n\n"
        f"━━━━━━━━━━━━\n"
        f"{answers_text}\n\n"
        f"⏱ <i>Вақт: {remaining} сония</i>  {bar}"
    )


# ─── Countdown background task ────────────────────────────────────────────────
async def _run_countdown(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    msg_id: int,
    qdata: dict,
    attempt_id: str,
    display_order: int,
    aq_id: str,
    deadline_unix: float,
):
    try:
        update_interval = 5

        while True:
            await asyncio.sleep(update_interval)
            remaining = max(0, int(deadline_unix - time.time()))

            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=_build_msg(qdata, remaining),
                    # Pass question display_order to keyboard so callback is correct
                    reply_markup=get_answer_keyboard(qdata.get("answers", []), display_order),
                    parse_mode="HTML",
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                pass

            if remaining <= 0:
                break

        # Timeout: show expired message
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=(
                    f"📝 <b>Савол {qdata.get('current_index', display_order)} / 15:</b>\n\n"
                    f"{qdata.get('question_text', '')}\n\n"
                    f"⌛ <b>Вақт тугади!</b>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

        await asyncio.sleep(1.5)

        res = await bot_api.handle_timeout(aq_id)

        if res.get("attempt_completed"):
            score = res.get("score_so_far", 0)
            pct = round(score / 15 * 100)
            icon = "🎉" if pct >= 70 else "📊"
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{icon} <b>Тест якунланди!</b>\n\n"
                     f"👤 <b>Натижангиз:</b> {score} / 15 ({pct}%)\n\n"
                     f"Маълумотлар сақланди.",
                parse_mode="HTML",
            )
        else:
            next_q = res.get("next_question")
            if next_q and next_q.get("question_text"):
                new_dl = time.time() + QUESTION_TIMER
                dorder = next_q.get("display_order", display_order + 1)
                aq_next = next_q.get("attempt_question_id", "")
                new_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=_build_msg(next_q, QUESTION_TIMER),
                    reply_markup=get_answer_keyboard(next_q.get("answers", []), dorder),
                    parse_mode="HTML",
                )
                context.user_data["current_msg_id"] = new_msg.message_id
                task = asyncio.create_task(_run_countdown(
                    context, chat_id, new_msg.message_id,
                    next_q, attempt_id, dorder, aq_next, new_dl,
                ))
                context.user_data["countdown_task"] = task

    except asyncio.CancelledError:
        pass  # User answered — clean exit


# ─── Show Question ─────────────────────────────────────────────────────────────
async def show_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    question_data: dict,
    attempt_id: str = None,
):
    if not question_data or not question_data.get("question_text"):
        return await show_attempt_results(update, context, {})

    _cancel_countdown(context)

    aq_id = question_data.get("attempt_question_id", "")
    display_order = question_data.get("display_order", 1)

    deadline_unix = time.time() + QUESTION_TIMER
    text = _build_msg(question_data, QUESTION_TIMER)
    # CRITICAL: pass display_order so callback_data = ans:{display_order}:{uuid}
    keyboard = get_answer_keyboard(question_data.get("answers", []), display_order)

    chat_id = update.effective_chat.id
    if update.callback_query:
        try:
            msg = await update.callback_query.edit_message_text(
                text, reply_markup=keyboard, parse_mode="HTML"
            )
        except Exception:
            msg = await context.bot.send_message(
                chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode="HTML"
            )
    else:
        msg = await context.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode="HTML"
        )

    context.user_data["current_msg_id"] = msg.message_id

    if attempt_id and aq_id:
        task = asyncio.create_task(_run_countdown(
            context, chat_id, msg.message_id,
            question_data, attempt_id, display_order, aq_id, deadline_unix,
        ))
        context.user_data["countdown_task"] = task


# ─── Start Test ───────────────────────────────────────────────────────────────
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    topic_id = context.user_data.get("current_topic_id")
    user_id = update.effective_user.id

    if not topic_id:
        txt = "⚠️ Илтимос, аввал мавзуни танланг."
        if query:
            await query.edit_message_text(txt)
        else:
            await update.message.reply_text(txt)
        return TOPIC_SELECT

    try:
        attempt_data = await bot_api.start_attempt(user_id, topic_id, 1)
        err_msg = str(attempt_data.get("error", ""))

        if "already exists" in err_msg.lower():
            try:
                resume_data = await bot_api.get_employee_topic_status(user_id, topic_id)
                eid = resume_data.get("in_progress_attempt_id") or resume_data.get("attempt1_id")
                if eid:
                    context.user_data["attempt_id"] = eid
                    res = await bot_api.get_current_question(eid)
                    qdata = res.get("question")
                    if qdata and qdata.get("question_text"):
                        await show_question(update, context, qdata, eid)
                        return TEST_IN_PROGRESS
                    results = await bot_api.get_attempt_results(eid)
                    return await show_attempt_results(update, context, results)
            except Exception as e2:
                logger.warning("Resume error: %s", e2)
            txt = "⚠️ Тест аллақачон бошланган."
            if query:
                await query.edit_message_text(txt)
            else:
                await update.message.reply_text(txt)
            return TOPIC_SELECT

        if "error" in attempt_data or not attempt_data.get("attempt_id"):
            err = attempt_data.get("error", "Тестни бошлашда хатолик юз берди.")
            if "completed first" in str(err).lower():
                err = "Аввалги мавзуни тугатмасдан кейинги мавзуга ўтиб бўлмайди."
            if query:
                await query.edit_message_text(f"⚠️ {err}")
            else:
                await update.message.reply_text(f"⚠️ {err}")
            return TOPIC_SELECT

        attempt_id = attempt_data["attempt_id"]
        context.user_data["attempt_id"] = attempt_id

        qdata = attempt_data.get("first_question")
        if not qdata:
            res = await bot_api.get_current_question(attempt_id)
            qdata = res.get("question")

        await show_question(update, context, qdata, attempt_id)
        return TEST_IN_PROGRESS

    except Exception as e:
        logger.error("start_test error: %s", e, exc_info=True)
        txt = "⚠️ Тестни бошлашда хатолик юз берди."
        if query:
            await query.edit_message_text(txt)
        else:
            await update.message.reply_text(txt)
        return TOPIC_SELECT


# ─── Handle Answer ─────────────────────────────────────────────────────────────
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    data = query.data if query else ""
    if not data.startswith("ans:"):
        return TEST_IN_PROGRESS

    parts = data.split(":")
    if len(parts) < 3:
        return TEST_IN_PROGRESS

    # parts[1] = question display_order (1-15), parts[2] = answer UUID
    question_order = int(parts[1])
    answer_id = parts[2]
    attempt_id = context.user_data.get("attempt_id")

    # Cancel countdown IMMEDIATELY
    _cancel_countdown(context)

    try:
        result = await bot_api.submit_answer(attempt_id, question_order, answer_id)

        # Idempotent: double-tap or already answered — ignore silently
        if result.get("idempotent_response"):
            logger.debug("Idempotent answer for q=%s, ignoring", question_order)
            return TEST_IN_PROGRESS

        is_correct = result.get("is_correct", False)
        attempt_completed = result.get("attempt_completed", False)

        # Brief feedback
        if is_correct:
            try:
                await query.edit_message_text(
                    "✅ <b>Тўғри жавоб!</b> 🎉🎉🎉\n\n⏳ Кейинги савол...",
                    parse_mode="HTML",
                )
                await asyncio.sleep(1.5)
            except Exception:
                pass
        else:
            try:
                await query.edit_message_text(
                    "❌ <b>Нотўғри жавоб.</b>\n\n⏳ Кейинги савол...",
                    parse_mode="HTML",
                )
                await asyncio.sleep(1.0)
            except Exception:
                pass

        if attempt_completed:
            return await show_attempt_results(update, context, result)

        next_q = result.get("next_question")
        if next_q and next_q.get("question_text"):
            await show_question(update, context, next_q, attempt_id)
        else:
            try:
                res = await bot_api.get_current_question(attempt_id)
                next_q2 = res.get("question")
                if next_q2 and next_q2.get("question_text"):
                    await show_question(update, context, next_q2, attempt_id)
                else:
                    return await show_attempt_results(update, context, result)
            except Exception:
                return await show_attempt_results(update, context, result)

        return TEST_IN_PROGRESS

    except Exception as e:
        logger.error("handle_answer error: %s", e, exc_info=True)
        return TEST_IN_PROGRESS


# ─── Show Results ──────────────────────────────────────────────────────────────
async def show_attempt_results(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    results: dict,
):
    _cancel_countdown(context)

    attempt_id = context.user_data.get("attempt_id")
    if not results or "score" not in results:
        if attempt_id:
            results = await bot_api.get_attempt_results(attempt_id)

    score = results.get("score", 0)
    total = 15
    pct = round((score / total) * 100) if total > 0 else 0
    icon = "🎉" if pct >= 70 else "📊"

    text = (
        f"{icon} <b>Тест якунланди!</b>\n\n"
        f"👤 <b>Натижангиз:</b> {score} / {total} ({pct}%)\n\n"
        f"Маълумотлар сақланди."
    )

    chat_id = update.effective_chat.id
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")

    return TOPIC_SELECT
