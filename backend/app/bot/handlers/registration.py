# -*- coding: utf-8 -*-
"""
Registration flow:
  ASK_BRANCH (1) → user selects branch
  ASK_FULLNAME (0) → user enters full name (Cyrillic)
  ASK_PHONE (2) → user shares phone → registers
"""
from telegram import Update
from telegram.ext import ContextTypes
from .. import messages
from ..keyboards import get_phone_keyboard, get_main_menu_keyboard
from ..api_client import bot_api

ASK_FULLNAME = 0
ASK_BRANCH   = 1
ASK_PHONE    = 2
MAIN_MENU    = 10


async def handle_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: User selects a branch from inline keyboard."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("branch:"):
        return ASK_BRANCH

    branch_id = data.split(":", 1)[1]
    branch_name = "Номаълум филиал"

    # Try fetching branches to find exact name
    try:
        resp = await bot_api.get_branches()
        branches = resp.get("branches", []) if isinstance(resp, dict) else []
        found = next((b for b in branches if str(b["id"]) == str(branch_id)), None)
        if found:
            branch_name = found["name"]
            context.user_data["branch_id"] = str(found["id"])
    except Exception:
        pass

    if branch_name == "Номаълум филиал":
        # Check fallback list
        from .start import FALLBACK_BRANCHES
        found_fb = next((b for b in FALLBACK_BRANCHES if b["id"] == branch_id), None)
        if found_fb:
            branch_name = found_fb["name"]
            context.user_data["branch_name"] = branch_name
            context.user_data["branch_id"] = None  # backend will match by branch_name if needed or keep None

    context.user_data["branch_name"] = branch_name

    await query.edit_message_text(
        f"✅ Филиал: <b>{branch_name}</b>\n\n"
        f"{messages.ASK_FULLNAME}",
        parse_mode="HTML"
    )
    return ASK_FULLNAME


async def handle_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: User enters full name (Cyrillic)."""
    full_name = update.message.text.strip() if update.message.text else ""

    if len(full_name) < 3:
        await update.message.reply_text(messages.FULLNAME_TOO_SHORT)
        return ASK_FULLNAME

    context.user_data["full_name"] = full_name

    await update.message.reply_text(
        messages.ASK_PHONE,
        reply_markup=get_phone_keyboard()
    )
    return ASK_PHONE


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: User shares phone number → register."""
    contact = update.message.contact
    if not contact:
        await update.message.reply_text(messages.PHONE_SECURITY_ERROR)
        return ASK_PHONE

    if contact.user_id != update.effective_user.id:
        await update.message.reply_text(messages.PHONE_SECURITY_ERROR)
        return ASK_PHONE

    phone = contact.phone_number

    try:
        await bot_api.register_employee(
            telegram_user_id=update.effective_user.id,
            full_name=context.user_data.get("full_name", ""),
            branch_id=context.user_data.get("branch_id"),
            phone=phone,
        )

        await update.message.reply_text(
            messages.REGISTRATION_SUCCESS.format(
                full_name=context.user_data.get("full_name", ""),
                branch_name=context.user_data.get("branch_name", ""),
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return MAIN_MENU

    except Exception as e:
        await update.message.reply_text(messages.ERROR_NETWORK)
        return ASK_PHONE


async def remind_share_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed instead of tapping the share-contact button."""
    await update.message.reply_text(
        "📲 Илтимос, рақамни улашиш тугмасини босинг.\n"
        "Матн орқали рақам қабул қилинмайди — хавфсизлик мақсадида.",
        reply_markup=get_phone_keyboard()
    )
    return ASK_PHONE
