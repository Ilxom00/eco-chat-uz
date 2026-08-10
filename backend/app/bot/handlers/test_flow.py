"""
test_flow.py — Telegram Bot Test Flow Handler
FIXED:
  - asyncio.Task properly stored and cancelled to prevent repeated questions
  - 60s timer per question
  - Correct answer detection fixed (uses ans index, not answer_id mismatch)
  - Long button text wrapping via keyboards.py
  - Fireworks 🎉 on correct answer (1.5s)
  - Auto-advance on timeout
"""
import logging
import asyncio
import time
from telegram import Update
from telegram.ext import ContextTypes
from ..keyboards import get_answer_keyboard
from ..api_client import bot_api

logger = logging.getLogger(__name__)

TOPIC_SELECT = 20
TEST_IN_PROGRESS = 22
SEMINAR_CONFIRM = 23

QUESTION_TIMER = 60   # 60 seconds per question


# ─── Cancel helper ─────────────────────────────────────────────────────────────
def _cancel_countdown(context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current countdown task if running."""
    task = context.user_data.pop("countdown_task", None)
    if task and not task.done():
        task.cancel()


# ─── Countdown background task ────────────────────────────────────────────────
async def _run_countdown(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    msg_id: int,
    q_text: str,
    answers: list,
    current: int,
    total: int,
    attempt_id: str,
    display_order: int,
    aq_id: str,
    deadline_unix: float,
):
    """
    Background countdown: edits message every 5s. Auto-advances on timeout.
    Uses asyncio.Task cancellation for clean stop when user answers.
    """
    try:
        update_interval = 5

        while True:
            await asyncio.sleep(update_interval)
            remaining = max(0, int(deadline_unix - time.time()))

            # Build progress bar (12 blocks for 60s, each = 5s)
            total_blocks = 12
            filled = min(total_blocks, remaining // 5)
            empty = total_blocks - filled
            bar = "🟩" * filled + "⬜" * empty

            text = (
                f"📝 <b>Савол {current} / {total}:</b>\n\n"
                f"<b>{q_text}</b>\n\n"
                f"⏱ <i>Вақт: {remaining} сония</i>\n"
                f"{bar}"
            )

            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=text,
                    reply_markup=get_answer_keyboard(answers),
                    parse_mode="HTML",
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                pass

            if remaining <= 0:
                break

        # Timer expired — show timeout message
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=(
                    f"📝 <b>Савол {current} / {total}:</b>\n\n"
                    f"<b>{q_text}</b>\n\n"
                    f"⌛ <i>Вақт тугади!</i>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

        await asyncio.sleep(1.5)

        # Call server timeout handler
        try:
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
                    new_msg = await context.bot.send_message(
                        chat_id=chat_id,
                        text=_q_text(next_q, QUESTION_TIMER),
                        reply_markup=get_answer_keyboard(next_q.get("answers", [])),
                        parse_mode="HTML",
                    )
                    dorder = next_q.get("display_order", current + 1)
                    aq_next = next_q.get("attempt_question_id", "")
                    task = asyncio.create_task(_run_countdown(
                        context, chat_id, new_msg.message_id,
                        next_q["question_text"], next_q.get("answers", []),
                        next_q.get("current_index", current + 1), total,
                        attempt_id, dorder, aq_next, new_dl,
                    ))
                    context.user_data["countdown_task"] = task
                    context.user_data["current_msg_id"] = new_msg.message_id
                    context.user_data[f"aqid_{dorder}"] = aq_next
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Auto-timeout advance error: %s", e)

    except asyncio.CancelledError:
        pass  # Task was cancelled (user answered) — clean exit


# ─── Text builder helper ───────────────────────────────────────────────────────
def _q_text(qdata: dict, remaining: int) -> str:
    current = qdata.get("current_index", qdata.get("display_order", 1))
    total = 15
    q_text = qdata.get("question_text", "")
    total_blocks = 12
    filled = min(total_blocks, remaining // 5)
    empty = total_blocks - filled
    bar = "🟩" * filled + "⬜" * empty
    return (
        f"📝 <b>Савол {current} / {total}:</b>\n\n"
        f"<b>{q_text}</b>\n\n"
        f"⏱ <i>Вақт: {remaining} сония</i>\n"
        f"{bar}"
    )


# ─── Show Question ─────────────────────────────────────────────────────────────
async def show_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    question_data: dict,
    attempt_id: str = None,
):
    if not question_data or not question_data.get("question_text"):
        return await show_attempt_results(update, context, {})

    # Cancel previous countdown before showing new question
    _cancel_countdown(context)

    current = question_data.get("current_index", question_data.get("display_order", 1))
    q_text = question_data.get("question_text", "")
    answers = question_data.get("answers", [])
    display_order = question_data.get("display_order", current)
    aq_id = question_data.get("attempt_question_id", "")

    deadline_unix = time.time() + QUESTION_TIMER
    text = _q_text(question_data, QUESTION_TIMER)
    keyboard = get_answer_keyboard(answers)

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
    if aq_id:
        context.user_data[f"aqid_{display_order}"] = aq_id

    # Start new countdown task
    if attempt_id and aq_id:
        task = asyncio.create_task(_run_countdown(
            context, chat_id, msg.message_id,
            q_text, answers, current, 15,
            attempt_id, display_order, aq_id, deadline_unix,
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
        msg_text = "⚠️ Илтимос, аввал мавзуни танланг."
        if query:
            await query.edit_message_text(msg_text)
        else:
            await update.message.reply_text(msg_text)
        return TOPIC_SELECT

    try:
        attempt_data = await bot_api.start_attempt(user_id, topic_id, 1)
        err_msg = attempt_data.get("error", "")

        # Attempt already exists — try to resume
        if "already exists" in str(err_msg).lower():
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
                    else:
                        results = await bot_api.get_attempt_results(eid)
                        return await show_attempt_results(update, context, results)
            except Exception as e2:
                logger.warning("Resume error: %s", e2)
            if query:
                await query.edit_message_text("⚠️ Тест аллақачон бошланган.")
            else:
                await update.message.reply_text("⚠️ Тест аллақачон бошланган.")
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
        err_text = "⚠️ Тестни бошлашда хатолик юз берди."
        if query:
            await query.edit_message_text(err_text)
        else:
            await update.message.reply_text(err_text)
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

    order = int(parts[1])
    answer_id = parts[2]
    attempt_id = context.user_data.get("attempt_id")

    # CRITICAL: Cancel countdown immediately to prevent double-advance
    _cancel_countdown(context)

    try:
        result = await bot_api.submit_answer(attempt_id, order, answer_id)
        is_correct = result.get("is_correct", False)
        attempt_completed = result.get("attempt_completed", False)

        # Feedback: correct or wrong (brief, non-blocking)
        if is_correct:
            try:
                await query.edit_message_text(
                    "✅ <b>Тўғри жавоб!</b> 🎉🎉🎉\n\n⏳ Кейинги савол...",
                    parse_mode="HTML"
                )
                await asyncio.sleep(1.5)
            except Exception:
                pass
        else:
            try:
                await query.edit_message_text(
                    "❌ <b>Нотўғри жавоб.</b>\n\n⏳ Кейинги савол...",
                    parse_mode="HTML"
                )
                await asyncio.sleep(1.0)
            except Exception:
                pass

        if attempt_completed:
            return await show_attempt_results(update, context, result)

        # Show next question
        next_q = result.get("next_question")
        if next_q and next_q.get("question_text"):
            await show_question(update, context, next_q, attempt_id)
        else:
            # Fallback: fetch from server
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
    # Cancel any running countdown
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
