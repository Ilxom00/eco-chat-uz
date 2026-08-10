from telegram import Update
from telegram.ext import ContextTypes
from .. import messages
from ..api_client import bot_api

async def show_all_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        status = await bot_api.get_employee_status(update.effective_user.id)
        # Assuming status returns list of completed topics and their scores
        results_text = f"{messages.MY_RESULTS_HEADER}\n\n"
        
        topics_results = status.get('results', [])
        if not topics_results:
            results_text += messages.NO_RESULTS_YET
        else:
            for res in topics_results:
                results_text += f"Мавзу {res['topic_id']}: {res['attempt1_pct']}% → {res['attempt2_pct']}% (+{res['delta_pct']} п.п.)\n"
                
        await update.message.reply_text(results_text)
    except Exception:
        await update.message.reply_text(messages.ERROR_NETWORK)
