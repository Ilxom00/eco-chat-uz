"""
eco-chat.uz — Global Telegram Error Handler
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import (
    TelegramError,
    Forbidden,
    NetworkError,
    RetryAfter,
    TimedOut,
)

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for all uncaught exceptions."""
    error = context.error

    if isinstance(error, Forbidden):
        # User blocked the bot — log and ignore
        logger.warning("Bot was blocked by user: %s", update)
        return

    if isinstance(error, RetryAfter):
        logger.warning("Telegram rate limit hit. Retry after %d seconds.", error.retry_after)
        return

    if isinstance(error, TimedOut):
        logger.warning("Request timed out: %s", error)
        return

    if isinstance(error, NetworkError):
        logger.error("Network error: %s", error)
        return

    # Log unexpected errors
    logger.error("Unhandled exception while processing update:", exc_info=error)

    # Try to notify user if possible
    if update and hasattr(update, "effective_message") and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Tizimda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.\n"
                "Muammo davom etsa, /start buyrug'ini bosing."
            )
        except TelegramError:
            pass  # Can't send message — ignore
