# -*- coding: utf-8 -*-
"""
eco-chat.uz — /start Command Handler
1. Registered user → show main menu
2. New user       → show welcome + branch selection keyboard
"""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.bot import messages
from app.bot.keyboards import get_main_menu_keyboard, get_branch_keyboard
from app.bot.api_client import bot_api

logger = logging.getLogger(__name__)

# Conversation states (must match registration.py and bot.py)
ASK_BRANCH   = 1
ASK_FULLNAME = 0
ASK_PHONE    = 2
MAIN_MENU    = 10


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    try:
        status = await bot_api.get_employee_status(user_id)

        if status.get("registration_state") == "REGISTERED":
            await update.message.reply_text(
                messages.WELCOME_BACK,
                reply_markup=get_main_menu_keyboard(),
            )
            return MAIN_MENU

    except Exception as e:
        logger.warning("Could not get employee status for user %d: %s", user_id, e)

    # New user — show welcome + branch keyboard
    try:
        resp = await bot_api.get_branches()
        branches = resp.get("branches", [])
    except Exception as e:
        logger.error("Could not fetch branches: %s", e)
        branches = []

    await update.message.reply_text(
        messages.WELCOME_NEW,
        reply_markup=get_branch_keyboard(branches) if branches else None,
    )
    return ASK_BRANCH


async def show_main_menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start_command(update, context)
