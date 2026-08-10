"""
eco-chat.uz — Telegram Bot Application
Robust state-free event dispatching for 100% reliability.
"""
from __future__ import annotations

import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from app.config import settings

logger = logging.getLogger(__name__)


async def route_text_message(update: Update, context):
    """Route text messages cleanly based on text content or registration status."""
    if not update.message or not update.message.text:
        return

    txt = update.message.text.strip()
    from app.bot import messages
    from app.bot.handlers import start, menu, topic_nav, results, registration
    from app.bot.api_client import bot_api

    if txt in [messages.BTN_TESTS, "📝 Тестлар"]:
        return await topic_nav.show_topics(update, context)
    elif txt in [messages.BTN_MY_RESULTS, "📊 Менинг натижаларим"]:
        return await results.show_all_results(update, context)
    elif txt in [messages.BTN_MY_PROFILE, "👤 Менинг профилим"]:
        return await menu.show_my_profile(update, context)
    elif txt in [messages.BTN_HELP, "❓ Ёрдам"]:
        return await menu.show_help(update, context)
    else:
        # Only route to handle_fullname if the user is NOT already registered.
        # This prevents registered users from accidentally re-triggering registration.
        try:
            user_id = update.effective_user.id
            emp = await bot_api.get_employee_by_telegram_id(user_id)
            if emp and emp.get("full_name"):
                # Already registered — re-show main menu instead of registration
                from app.bot.keyboards import get_main_menu_keyboard
                full_name = emp["full_name"]
                await update.message.reply_text(
                    f"🌿 Хуш келибсиз! {full_name}\n\nАсосий меню:",
                    reply_markup=get_main_menu_keyboard(),
                )
                return
        except Exception:
            pass
        # New user typing their name during registration
        return await registration.handle_fullname(update, context)


async def create_application() -> Application:
    """Build and configure the Telegram bot application."""

    if not settings.bot_token_valid:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set or invalid. Check your .env file.")

    from app.bot.handlers import start, registration, menu, topic_nav, test_flow, results
    from app.bot.handlers.error import error_handler

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # ── Command Handlers ─────────────────────────────────────
    app.add_handler(CommandHandler("start", start.start_command))
    app.add_handler(CommandHandler("menu",  start.start_command))

    # ── Callback Query Handlers ──────────────────────────────
    app.add_handler(CallbackQueryHandler(registration.handle_branch, pattern=r"^branch:"))
    app.add_handler(CallbackQueryHandler(topic_nav.handle_topic_select, pattern=r"^topic:"))
    app.add_handler(CallbackQueryHandler(topic_nav.handle_back, pattern=r"^back_to_topics$"))
    app.add_handler(CallbackQueryHandler(test_flow.start_test, pattern=r"^start_test:"))
    app.add_handler(CallbackQueryHandler(test_flow.handle_answer, pattern=r"^ans:"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern=r"^ignore$"))

    # ── Text Message Handler ─────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text_message))

    # ── Global Error Handler ──────────────────────────────────
    app.add_error_handler(error_handler)

    # ── Bot Commands Menu ─────────────────────────────────────
    try:
        await app.bot.set_my_commands([
            BotCommand("start",  "Бошни бошлаш / Меню"),
            BotCommand("menu",   "Асосий меню"),
        ])
    except Exception as e:
        logger.warning("Could not set my commands: %s", e)

    logger.info("Telegram bot configured cleanly")
    return app


async def start_bot() -> None:
    """Initialize, start polling. Called from FastAPI lifespan."""
    app = await create_application()
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
