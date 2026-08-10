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
            
        await show_question(update, context, question_data)
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


async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_data: dict):
    if not question_data or not question_data.get('question_text'):
        return await show_attempt_results(update, context, {})
        
    current = question_data.get('current_index', question_data.get('current', 1))
    total = 15
    q_text = question_data.get('question_text', '')
    
    text = (
        f"📝 <b>Савол {current} / {total}:</b>\n\n"
        f"<b>{q_text}</b>\n\n"
        f"⏱ <i>Вақт: 30 сония</i>"
    )
    
    answers = question_data.get('answers', [])
    keyboard = get_answer_keyboard(answers)
    
    if update.callback_query:
        try:
            msg = await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        except Exception:
            msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=keyboard, parse_mode='HTML')
    else:
        msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=keyboard, parse_mode='HTML')
        
    context.user_data['current_msg_id'] = msg.message_id
    context.user_data['current_question_order'] = question_data.get('display_order', current)


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
    
    try:
        result = await bot_api.submit_answer(attempt_id, order, answer_id)
        
        if result.get("completed"):
            return await show_attempt_results(update, context, result)

        next_q = result.get("next_question")
        if next_q:
            await show_question(update, context, next_q)
        else:
            return await show_attempt_results(update, context, result)

        return TEST_IN_PROGRESS

    except Exception as e:
        logger.error("Error submitting answer: %s", e, exc_info=True)
        return TEST_IN_PROGRESS


async def show_attempt_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results: dict):
    attempt_id = context.user_data.get('attempt_id')
    if not results and attempt_id:
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
        await update.callback_query.edit_message_text(text, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode='HTML')
        
    return TOPIC_SELECT
