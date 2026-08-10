import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from .. import messages
from ..keyboards import get_answer_keyboard, get_seminar_confirm_keyboard
from ..api_client import bot_api

logger = logging.getLogger(__name__)

TOPIC_SELECT = 20
TEST_IN_PROGRESS = 22
SEMINAR_CONFIRM = 23


# ─── Background countdown task ────────────────────────────────────────────────
async def _countdown_task(context: ContextTypes.DEFAULT_TYPE, chat_id: int,
                          msg_id: int, q_text: str, answers: list,
                          current: int, total: int, seconds: int,
                          attempt_id: str, display_order: int):
    """
    Background task: edits the question message every 5s to show countdown.
    Stops when the question is answered or timer hits 0.
    """
    task_key = f"countdown_{chat_id}_{display_order}"
    remaining = seconds

    while remaining > 0:
        await asyncio.sleep(5)
        remaining -= 5
        remaining = max(0, remaining)

        # Check if still the active question (user might have answered)
        if context.user_data.get("current_question_order") != display_order:
            return  # Question was answered, stop countdown

        timer_bar = "🟩" * (remaining // 5) + "⬜" * ((seconds - remaining) // 5)
        text = (
            f"📝 <b>Савол {current} / {total}:</b>\n\n"
            f"<b>{q_text}</b>\n\n"
            f"⏱ <i>Вақт: {remaining} сония</i>\n"
            f"{timer_bar}"
        )
        keyboard = get_answer_keyboard(answers)
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=text, reply_markup=keyboard, parse_mode="HTML"
            )
        except Exception:
            pass  # Message may have been deleted or already answered

        if remaining <= 0:
            break

    # Timer expired — mark question timed out if not yet answered
    if context.user_data.get("current_question_order") == display_order:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=(
                    f"📝 <b>Савол {current} / {total}:</b>\n\n"
                    f"<b>{q_text}</b>\n\n"
                    f"⏱ <i>⌛ Вақт тугади!</i>"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

        # Auto-advance via timeout API
        try:
            aq_id = context.user_data.get(f"aqid_{display_order}")
            if aq_id:
                res = await bot_api.handle_timeout(aq_id)
                # If attempt completed, show results
                if res.get("attempt_completed"):
                    await asyncio.sleep(1)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⏰ Вақт тугади. Тест якунланди.\n\n"
                             f"📊 Натижа: {res.get('score', 0)} / 15",
                        parse_mode="HTML"
                    )
                else:
                    # Get and show next question
                    next_q = res.get("next_question")
                    if next_q:
                        context.user_data["current_question_order"] = next_q["display_order"]
                        await asyncio.sleep(1)
                        new_msg = await context.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                f"⏰ Вақт тугади!\n\n"
                                f"📝 <b>Савол {next_q['current_index']} / 15:</b>\n\n"
                                f"<b>{next_q.get('question_text', '')}</b>\n\n"
                                f"⏱ <i>Вақт: 30 сония</i>"
                            ),
                            reply_markup=get_answer_keyboard(next_q.get("answers", [])),
                            parse_mode="HTML"
                        )
                        context.user_data["current_msg_id"] = new_msg.message_id
                        context.user_data[f"aqid_{next_q['display_order']}"] = next_q.get("attempt_question_id")
                        # Start new countdown
                        asyncio.create_task(_countdown_task(
                            context, chat_id, new_msg.message_id,
                            next_q.get("question_text", ""), next_q.get("answers", []),
                            next_q["current_index"], 15, 30,
                            attempt_id, next_q["display_order"]
                        ))
        except Exception as e:
            logger.error("Auto-timeout error: %s", e)


# ─── Start Test ───────────────────────────────────────────────────────────────
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    topic_id = context.user_data.get('current_topic_id')
    user_id = update.effective_user.id

    if not topic_id:
        if query:
            await query.edit_message_text("⚠️ Илтимос, аввал мавзуни танланг.")
        else:
            await update.message.reply_text("⚠️ Илтимос, аввал мавзуни танланг.")
        return TOPIC_SELECT

    try:
        attempt_number = 1
        attempt_data = await bot_api.start_attempt(user_id, topic_id, attempt_number)

        # If attempt already exists — resume it automatically
        err_msg = attempt_data.get("error", "")
        if "already exists" in str(err_msg).lower():
            try:
                resume_data = await bot_api.get_employee_topic_status(user_id, topic_id)
                existing_attempt_id = resume_data.get("in_progress_attempt_id") or resume_data.get("attempt1_id")
                if existing_attempt_id:
                    context.user_data['attempt_id'] = existing_attempt_id
                    res = await bot_api.get_current_question(existing_attempt_id)
                    question_data = res.get("question")
                    if question_data:
                        await show_question(update, context, question_data, existing_attempt_id)
                        return TEST_IN_PROGRESS
                    else:
                        results = await bot_api.get_attempt_results(existing_attempt_id)
                        return await show_attempt_results(update, context, results)
            except Exception as e2:
                logger.warning("Could not resume attempt: %s", e2)
            err_display = "⚠️ Бу мавзуда тест аллақачон бошланган. Тестлар рўйхатига қайтяпмиз."
            if query:
                await query.edit_message_text(err_display)
            else:
                await update.message.reply_text(err_display)
            return TOPIC_SELECT

        if "error" in attempt_data or not attempt_data.get("attempt_id"):
            err_msg = attempt_data.get("error", "Тестни бошлашда хатолик юз берди.")
            if "completed first" in str(err_msg).lower() or "permissionerror" in str(err_msg).lower():
                err_msg = "Аввалги мавзуни тугатмасдан кейинги мавзуга ўтиб бўлмайди."
            if query:
                await query.edit_message_text(f"⚠️ {err_msg}")
            else:
                await update.message.reply_text(f"⚠️ {err_msg}")
            return TOPIC_SELECT

        attempt_id = attempt_data["attempt_id"]
        context.user_data['attempt_id'] = attempt_id

        question_data = attempt_data.get("first_question")
        if not question_data:
            res = await bot_api.get_current_question(attempt_id)
            question_data = res.get("question")

        await show_question(update, context, question_data, attempt_id)
        return TEST_IN_PROGRESS

    except Exception as e:
        logger.error("Error starting test for user %s topic %s: %s", user_id, topic_id, e, exc_info=True)
        err_text = "⚠️ Тестни бошлашда хатолик юз берди. Илтимос, қайта уриниб кўринг."
        if "completed first" in str(e).lower():
            err_text = "⚠️ Аввалги мавзуни тугатмасдан кейинги мавзуга ўтиб бўлмайди."
        if query:
            await query.edit_message_text(err_text)
        else:
            await update.message.reply_text(err_text)
        return TOPIC_SELECT


# ─── Show Question with Countdown ────────────────────────────────────────────
async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        question_data: dict, attempt_id: str = None):
    if not question_data or not question_data.get('question_text'):
        return await show_attempt_results(update, context, {})

    current = question_data.get('current_index', question_data.get('current', 1))
    total = 15
    q_text = question_data.get('question_text', '')
    remaining = question_data.get('remaining_seconds', 30)
    answers = question_data.get('answers', [])
    display_order = question_data.get('display_order', current)
    aq_id = question_data.get('attempt_question_id')

    text = (
        f"📝 <b>Савол {current} / {total}:</b>\n\n"
        f"<b>{q_text}</b>\n\n"
        f"⏱ <i>Вақт: {remaining} сония</i>"
    )
    keyboard = get_answer_keyboard(answers)

    chat_id = update.effective_chat.id
    if update.callback_query:
        try:
            msg = await update.callback_query.edit_message_text(
                text, reply_markup=keyboard, parse_mode='HTML')
        except Exception:
            msg = await context.bot.send_message(
                chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode='HTML')
    else:
        msg = await context.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode='HTML')

    context.user_data['current_msg_id'] = msg.message_id
    context.user_data['current_question_order'] = display_order
    if aq_id:
        context.user_data[f"aqid_{display_order}"] = aq_id

    # Start countdown background task
    if attempt_id and remaining > 0:
        asyncio.create_task(_countdown_task(
            context, chat_id, msg.message_id,
            q_text, answers, current, total, remaining,
            attempt_id, display_order
        ))


# ─── Handle Answer ────────────────────────────────────────────────────────────
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
    attempt_id = context.user_data.get('attempt_id')

    # Mark question as answered to stop countdown
    context.user_data['current_question_order'] = -1

    try:
        result = await bot_api.submit_answer(attempt_id, order, answer_id)

        # Check completion — key is 'attempt_completed' from test_engine
        if result.get("attempt_completed") or result.get("completed"):
            return await show_attempt_results(update, context, result)

        next_q = result.get("next_question")
        if next_q:
            context.user_data['current_question_order'] = next_q.get('display_order', order + 1)
            await show_question(update, context, next_q, attempt_id)
        else:
            # Fallback: fetch next question from server
            try:
                res = await bot_api.get_current_question(attempt_id)
                next_q2 = res.get("question")
                if next_q2 and next_q2.get("question_text"):
                    context.user_data['current_question_order'] = next_q2.get('display_order', order + 1)
                    await show_question(update, context, next_q2, attempt_id)
                else:
                    return await show_attempt_results(update, context, result)
            except Exception:
                return await show_attempt_results(update, context, result)

        return TEST_IN_PROGRESS

    except Exception as e:
        logger.error("Error submitting answer: %s", e, exc_info=True)
        return TEST_IN_PROGRESS


# ─── Show Results ─────────────────────────────────────────────────────────────
async def show_attempt_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results: dict):
    attempt_id = context.user_data.get('attempt_id')
    if not results or not results.get('score') and results.get('score') != 0:
        if attempt_id:
            results = await bot_api.get_attempt_results(attempt_id)

    score = results.get('score', 0)
    total = 15
    pct = round((score / total) * 100) if total > 0 else 0

    status_icon = "🎉" if pct >= 70 else "📊"
    text = (
        f"{status_icon} <b>Тест якунланди!</b>\n\n"
        f"👤 <b>Натижангиз:</b> {score} / {total} ({pct}%)\n\n"
        f"Маълумотлар сақланди."
    )

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode='HTML')
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=text, parse_mode='HTML')
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text, parse_mode='HTML')

    return TOPIC_SELECT
