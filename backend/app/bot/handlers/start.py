"""
eco-chat.uz — /start Command Handler
Checks registration status, resumes active attempts, or starts registration.
"""
from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.bot import messages
from app.bot.keyboards import get_main_menu_keyboard
from app.bot.api_client import bot_api

logger = logging.getLogger(__name__)

# ── State constants (shared across handlers via bot.py) ────────
ASK_FULLNAME = 0
ASK_BRANCH   = 1
ASK_PHONE    = 2
MAIN_MENU    = 10


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    /start — Entry point.
    1. Check if user is registered
    2. If registered: show main menu (with active attempt recovery)
    3. If not: begin registration flow
    """
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or ""

    try:
        status = await bot_api.get_employee_status(user_id)

        if status.get("registration_state") == "REGISTERED":
            # Bot restart recovery: check for active attempt
            active = status.get("active_attempt")
            if active:
                context.user_data["active_attempt_id"] = active.get("attempt_id")
                context.user_data["active_topic_id"] = active.get("topic_id")
                await update.message.reply_text(
                    f"🔄 Sizda davom etayotgan test bor!\n"
                    f"Mavzu: {active.get('topic_name', '')}\n"
                    f"Savol: {active.get('current_question_index', 1)}/15\n\n"
                    f"Davom etish uchun quyidagi menyu orqali tanlang.",
                    reply_markup=get_main_menu_keyboard(),
                )
            else:
                await update.message.reply_text(
                    messages.WELCOME_BACK,
                    reply_markup=get_main_menu_keyboard(),
                )
            return MAIN_MENU

    except Exception as e:
        logger.warning("Could not get employee status for user %d: %s", user_id, e)
        # API not reachable — still start registration if first time
        # or show welcome back if we know they're registered
        pass

    # New user — start registration
    await update.message.reply_text(messages.WELCOME_NEW)
    await update.message.reply_text(messages.ASK_FULLNAME)
    return ASK_FULLNAME


async def show_main_menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Alias for /menu command — shows main menu if registered."""
    return await start_command(update, context)
