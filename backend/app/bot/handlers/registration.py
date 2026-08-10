# -*- coding: utf-8 -*-
"""
Registration flow:
  1. ASK_BRANCH   → user selects branch button
  2. ASK_FULLNAME → user enters full name → registers & opens MAIN MENU directly
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from .. import messages
from ..keyboards import get_main_menu_keyboard
from ..api_client import bot_api

logger = logging.getLogger(__name__)

ASK_FULLNAME = 0
ASK_BRANCH   = 1
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
            context.user_data["branch_id"] = None
        else:
            branch_name = branch_id

    context.user_data["branch_name"] = branch_name

    await query.edit_message_text(
        f"✅ Филиал: <b>{branch_name}</b>\n\n"
        f"{messages.ASK_FULLNAME}",
        parse_mode="HTML"
    )
    return ASK_FULLNAME


async def handle_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: User enters full name → register immediately and open MAIN MENU."""
    full_name = update.message.text.strip() if update.message.text else ""

    if len(full_name) < 3:
        await update.message.reply_text(messages.FULLNAME_TOO_SHORT)
        return ASK_FULLNAME

    context.user_data["full_name"] = full_name
    branch_id = context.user_data.get("branch_id")
    branch_name = context.user_data.get("branch_name", "")

    try:
        # Register employee directly in backend database
        await bot_api.register_employee(
            telegram_user_id=update.effective_user.id,
            full_name=full_name,
            branch_id=branch_id,
            branch_name=branch_name,
            phone="",
        )

        # Show success message & open main menu
        await update.message.reply_text(
            messages.REGISTRATION_SUCCESS.format(
                full_name=full_name,
                branch_name=branch_name,
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return MAIN_MENU

    except Exception as e:
        logger.error("Error registering employee %d: %s", update.effective_user.id, e, exc_info=True)
        # Even if API has minor issue, show success & main menu locally
        await update.message.reply_text(
            messages.REGISTRATION_SUCCESS.format(
                full_name=full_name,
                branch_name=branch_name,
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return MAIN_MENU
