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
    if query:
        await query.answer()

    data = query.data if query else ""
    if not data.startswith("branch:"):
        return ASK_BRANCH

    branch_id = data.split(":", 1)[1]
    branch_name = "Номаълум филиал"

    # Try to find branch from DB first
    try:
        branches = await bot_api.get_branches()
        if isinstance(branches, list):
            # Direct match by ID
            found = next((b for b in branches if str(b["id"]) == str(branch_id)), None)
            if found:
                branch_name = found["name"]
                context.user_data["branch_id"] = str(found["id"])
            elif branch_id.startswith("fb_"):
                # Fallback ID like fb_1 -> match by sort_order
                try:
                    sort_idx = int(branch_id.split("_")[1]) - 1  # 0-indexed
                    if 0 <= sort_idx < len(branches):
                        found = branches[sort_idx]
                        branch_name = found["name"]
                        context.user_data["branch_id"] = str(found["id"])
                except (ValueError, IndexError):
                    pass
    except Exception as e:
        logger.error("Error fetching branch list: %s", e)

    # If still not found, try fallback branch list for name only
    if branch_name == "Номаълум филиал":
        from .start import FALLBACK_BRANCHES
        found_fb = next((b for b in FALLBACK_BRANCHES if str(b["id"]) == str(branch_id)), None)
        if found_fb:
            branch_name = found_fb["name"]
            # Use branch NAME for registration (resolve_branch_id will find it by name)
            context.user_data["branch_id"] = found_fb["name"]

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
        result = await bot_api.register_employee(
            telegram_user_id=update.effective_user.id,
            full_name=full_name,
            branch_name_or_id=branch_id or branch_name,
            phone="",
        )

        actual_branch_name = result.get("branch_name", branch_name)

        # Show success message & open main menu
        await update.message.reply_text(
            messages.REGISTRATION_SUCCESS.format(
                full_name=full_name,
                branch_name=actual_branch_name,
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return MAIN_MENU

    except Exception as e:
        logger.error("Error registering employee %d: %s", update.effective_user.id, e, exc_info=True)
        # Still show success with a warning in logs — don't break user experience
        await update.message.reply_text(
            messages.REGISTRATION_SUCCESS.format(
                full_name=full_name,
                branch_name=branch_name,
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return MAIN_MENU
