"""
eco-chat.uz — Telegram Bot Application
Sets up ConversationHandler, all message handlers, and bot lifecycle.
"""
from __future__ import annotations

import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from app.config import settings

logger = logging.getLogger(__name__)

# ── Conversation States ────────────────────────────────────────
# Registration
ASK_FULLNAME = 0
ASK_BRANCH   = 1
ASK_PHONE    = 2
# Navigation
MAIN_MENU    = 10
TOPIC_SELECT = 20
TEST_CONFIRM = 21
TEST_IN_PROGRESS = 22
SEMINAR_CONFIRM  = 23


async def create_application() -> Application:
    """Build and configure the Telegram bot application."""

    if not settings.bot_token_valid:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set or invalid. Check your .env file.")

    from app.bot.handlers import start, registration, menu, topic_nav, test_flow, results
    from app.bot.handlers.error import error_handler
    from app.bot import messages

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # ── Main Conversation Handler ──────────────────────────────
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start.start_command),
            CommandHandler("menu",  menu.show_main_menu_cmd),
        ],
        states={
            # ─ Registration ─────────────────────────────────
            ASK_BRANCH: [
                CallbackQueryHandler(registration.handle_branch, pattern=r"^branch:"),
            ],
            ASK_FULLNAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    registration.handle_fullname,
                ),
            ],

            # ─ Main Menu ────────────────────────────────────
            MAIN_MENU: [
                # Bottom menu buttons
                MessageHandler(
                    filters.Regex(f"^{messages.BTN_TESTS}$"),
                    topic_nav.show_topics,
                ),
                MessageHandler(
                    filters.Regex(f"^{messages.BTN_MY_RESULTS}$"),
                    results.show_all_results,
                ),
                MessageHandler(
                    filters.Regex(f"^{messages.BTN_MY_PROFILE}$"),
                    menu.show_my_profile,
                ),
                MessageHandler(
                    filters.Regex(f"^{messages.BTN_HELP}$"),
                    menu.show_help,
                ),
                # Inline button callbacks
                CallbackQueryHandler(topic_nav.handle_topic_select, pattern=r"^topic:"),
                CallbackQueryHandler(topic_nav.handle_back,         pattern=r"^back_to_topics$"),
                CallbackQueryHandler(test_flow.start_test,          pattern=r"^start_test:"),
                CallbackQueryHandler(test_flow.handle_answer,       pattern=r"^ans:"),
                CallbackQueryHandler(test_flow.handle_seminar_confirm, pattern=r"^seminar_"),
                # Ignore taps on non-interactive elements
                CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern=r"^ignore$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start.start_command),
            CommandHandler("menu",  menu.show_main_menu_cmd),
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
        name="main_conversation",
        persistent=False,
    )

    app.add_handler(conv_handler)

    # ── Global error handler ──────────────────────────────────
    app.add_error_handler(error_handler)

    # ── Bot Commands menu ─────────────────────────────────────
    await app.bot.set_my_commands([
        BotCommand("start",  "Botni boshlash / Menyu"),
        BotCommand("menu",   "Asosiy menyu"),
    ])

    logger.info("Telegram bot configured: @%s", (await app.bot.get_me()).username)
    return app


async def start_bot() -> None:
    """Initialize, start polling. Called from FastAPI lifespan."""
    app = await create_application()
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
