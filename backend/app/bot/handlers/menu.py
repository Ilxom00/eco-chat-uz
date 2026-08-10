from telegram import Update
from telegram.ext import ContextTypes
from .. import messages
from ..api_client import bot_api

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(messages.MAIN_MENU_TEXT)

async def show_my_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        status = await bot_api.get_employee_status(update.effective_user.id)
        # Formulate results message
        # For simplicity in this mock, we just show a placeholder or basic formatting
        await update.message.reply_text(f"{messages.MY_RESULTS_HEADER}\n\nКўрсаткич: {status.get('score', 0)}")
    except Exception:
        await update.message.reply_text(messages.ERROR_NETWORK)

async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        status = await bot_api.get_employee_status(update.effective_user.id)
        profile_text = f"👤 Профиль:\n\nИсм: {status.get('full_name', 'N/A')}\nФилиал: {status.get('branch_name', 'N/A')}"
        await update.message.reply_text(profile_text)
    except Exception:
        await update.message.reply_text(messages.ERROR_NETWORK)

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(messages.HELP_TEXT)


async def show_main_menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /menu command."""
    from app.bot.handlers.start import start_command
    return await start_command(update, context)
