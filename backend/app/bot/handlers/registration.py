from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from .. import messages
from ..keyboards import get_branch_keyboard, get_phone_keyboard, get_main_menu_keyboard
from ..api_client import bot_api

ASK_FULLNAME = 0
ASK_BRANCH = 1
ASK_PHONE = 2
MAIN_MENU = 10

async def handle_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = update.message.text.strip()
    if len(full_name) < 3:
        await update.message.reply_text(messages.FULLNAME_TOO_SHORT)
        return ASK_FULLNAME
        
    context.user_data['full_name'] = full_name
    
    try:
        branches = await bot_api.get_branches()
        await update.message.reply_text(
            messages.ASK_BRANCH, 
            reply_markup=get_branch_keyboard(branches)
        )
        return ASK_BRANCH
    except Exception as e:
        await update.message.reply_text(messages.ERROR_NETWORK)
        return ASK_FULLNAME

async def handle_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("branch:"):
        branch_id = int(data.split(":")[1])
        context.user_data['branch_id'] = branch_id
        
        # Get branch name for display
        branches = await bot_api.get_branches()
        branch_name = next((b['name'] for b in branches if b['id'] == branch_id), "Unknown")
        context.user_data['branch_name'] = branch_name
        
        await query.edit_message_text(messages.BRANCH_SELECTED.format(branch_name=branch_name))
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages.ASK_PHONE,
            reply_markup=get_phone_keyboard()
        )
        return ASK_PHONE
        
    return ASK_BRANCH

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            full_name=context.user_data['full_name'],
            branch_id=context.user_data['branch_id'],
            phone=phone
        )
        
        await update.message.reply_text(
            messages.REGISTRATION_SUCCESS.format(
                full_name=context.user_data['full_name'],
                branch_name=context.user_data['branch_name']
            ),
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU
    except Exception as e:
        await update.message.reply_text(messages.ERROR_NETWORK)
        return ASK_PHONE


async def remind_share_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed instead of sharing contact button — remind them."""
    await update.message.reply_text(
        "📱 Iltimos, telefon raqamingizni ulashish tugmasini bosing.\n"
        "Matn orqali raqam qabul qilinmaydi — xavfsizlik maqsadida.",
        reply_markup=get_phone_keyboard()
    )
    return ASK_PHONE
