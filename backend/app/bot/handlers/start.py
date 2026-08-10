# -*- coding: utf-8 -*-
"""
eco-chat.uz — /start Command Handler
1. Registered user → show welcome back & main menu directly
2. New user       → show welcome text + 15 inline branch selection buttons
"""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.bot import messages
from app.bot.keyboards import get_main_menu_keyboard, get_branch_keyboard
from app.bot.api_client import bot_api

logger = logging.getLogger(__name__)

ASK_BRANCH   = 1
ASK_FULLNAME = 0
MAIN_MENU    = 10

FALLBACK_BRANCHES = [
    {"id": "fb_1",  "name": "Давлат Экологик экспертизаси маркази (Марказий аппарат)"},
    {"id": "fb_2",  "name": "Қорақалпоғистон Республикаси филиали"},
    {"id": "fb_3",  "name": "Андижон вилояти филиали"},
    {"id": "fb_4",  "name": "Бухоро вилояти филиали"},
    {"id": "fb_5",  "name": "Жиззах вилояти филиали"},
    {"id": "fb_6",  "name": "Қашқадарё вилояти филиали"},
    {"id": "fb_7",  "name": "Навоий вилояти филиали"},
    {"id": "fb_8",  "name": "Наманган вилояти филиали"},
    {"id": "fb_9",  "name": "Самарқанд вилояти филиали"},
    {"id": "fb_10", "name": "Сурхондарё вилояти филиали"},
    {"id": "fb_11", "name": "Сирдарё вилояти филиали"},
    {"id": "fb_12", "name": "Фарғона вилояти филиали"},
    {"id": "fb_13", "name": "Тошкент вилояти филиали"},
    {"id": "fb_14", "name": "Хоразм вилояти филиали"},
    {"id": "fb_15", "name": "Тошкент шаҳар филиали"},
]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.effective_user.id
        msg = update.effective_message

        try:
            emp = await bot_api.get_employee_by_telegram_id(user_id)
            if emp and emp.get("full_name"):
                if msg:
                    await msg.reply_text(
                        messages.WELCOME_BACK,
                        reply_markup=get_main_menu_keyboard(),
                    )
                return MAIN_MENU
        except Exception as e:
            logger.warning("Error fetching employee for %d: %s", user_id, e)

        # New user — fetch 15 branches
        branches = []
        try:
            resp = await bot_api.get_branches()
            if isinstance(resp, list) and len(resp) > 0:
                branches = resp
            elif isinstance(resp, dict):
                branches = resp.get("branches", [])
        except Exception as e:
            logger.error("Error fetching branches: %s", e)

        if not branches:
            branches = FALLBACK_BRANCHES

        if msg:
            await msg.reply_text(
                messages.WELCOME_NEW,
                reply_markup=get_branch_keyboard(branches),
            )
        return ASK_BRANCH

    except Exception as e:
        logger.error("Critical error in start_command: %s", e, exc_info=True)
        msg = update.effective_message
        if msg:
            try:
                await msg.reply_text(
                    messages.WELCOME_NEW,
                    reply_markup=get_branch_keyboard(FALLBACK_BRANCHES),
                )
            except Exception:
                pass
        return ASK_BRANCH


async def show_main_menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start_command(update, context)
