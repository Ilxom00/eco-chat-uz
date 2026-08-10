from telegram import Update
from telegram.ext import ContextTypes
from .. import messages
from ..keyboards import get_topic_list_keyboard, get_start_test_keyboard
from ..api_client import bot_api

TOPIC_SELECT = 20
TEST_CONFIRM = 21

async def show_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        topics = await bot_api.get_topics(update.effective_user.id)
        keyboard = get_topic_list_keyboard(topics)
        if update.callback_query:
            await update.callback_query.edit_message_text(messages.TOPIC_LIST_HEADER, reply_markup=keyboard)
        else:
            await update.message.reply_text(messages.TOPIC_LIST_HEADER, reply_markup=keyboard)
        return TOPIC_SELECT
    except Exception:
        if update.callback_query:
            await update.callback_query.answer(messages.ERROR_NETWORK)
        else:
            await update.message.reply_text(messages.ERROR_NETWORK)

async def handle_topic_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "ignore":
        return TOPIC_SELECT
        
    if query.data.startswith("topic:"):
        topic_id = int(query.data.split(":")[1])
        context.user_data['current_topic_id'] = topic_id
        
        try:
            topic = await bot_api.get_topic(topic_id)
            text = messages.TEST_INTRO.format(topic_name=topic['name'])
            await query.edit_message_text(text, reply_markup=get_start_test_keyboard())
            return TEST_CONFIRM
        except Exception:
            await query.edit_message_text(messages.ERROR_NETWORK)
            return TOPIC_SELECT

async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await show_topics(update, context)
