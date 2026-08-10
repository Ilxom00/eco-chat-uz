# -*- coding: utf-8 -*-
import logging
from telegram import Update
from telegram.ext import ContextTypes
from .. import messages
from ..keyboards import get_topic_list_keyboard
from ..api_client import bot_api
from . import test_flow

logger = logging.getLogger(__name__)

TOPIC_SELECT = 20
TEST_IN_PROGRESS = 22


async def show_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        topics = await bot_api.get_topics(user_id)
        keyboard = get_topic_list_keyboard(topics)
        if update.callback_query:
            await update.callback_query.edit_message_text(messages.TOPIC_LIST_HEADER, reply_markup=keyboard)
        else:
            await update.message.reply_text(messages.TOPIC_LIST_HEADER, reply_markup=keyboard)
        return TOPIC_SELECT
    except Exception as e:
        logger.error("Error showing topics for user %d: %s", update.effective_user.id, e, exc_info=True)
        if update.callback_query:
            await update.callback_query.answer(messages.ERROR_NETWORK)
        else:
            await update.message.reply_text(messages.ERROR_NETWORK)


async def handle_topic_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    if not query or not query.data:
        return TOPIC_SELECT

    if query.data == "ignore":
        return TOPIC_SELECT

    if query.data.startswith("topic:"):
        topic_id = query.data.split(":", 1)[1]
        context.user_data['current_topic_id'] = topic_id
        # Start test directly for selected topic!
        return await test_flow.start_test(update, context)


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    return await show_topics(update, context)
