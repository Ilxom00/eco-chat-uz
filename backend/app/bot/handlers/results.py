"""results.py — "Менинг натижаларим" handler"""
from telegram import Update
from telegram.ext import ContextTypes
from ..api_client import bot_api
import logging

logger = logging.getLogger(__name__)


async def show_all_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        status = await bot_api.get_employee_status(user_id)

        if not status or not status.get("full_name"):
            await update.message.reply_text(
                "⚠️ Сиз рўйхатдан ўтмагансиз. /start буйруғини юборинг."
            )
            return

        results = status.get("results", [])

        if not results:
            text = (
                "📊 <b>Менинг натижаларим</b>\n\n"
                "Ҳали ҳеч қандай тест топширилмаган.\n\n"
                "📝 Тестлар мавзусини танланг!"
            )
        else:
            text = "📊 <b>Менинг натижаларим</b>\n\n"
            for r in results:
                topic_name = r.get("topic_name", "Мавзу")
                a1_pct = r.get("attempt1_pct")
                a2_pct = r.get("attempt2_pct")
                a1_score = r.get("attempt1_score")
                a2_score = r.get("attempt2_score")
                status_str = r.get("status", "")

                # Status icon
                if status_str == "PASSED":
                    icon = "✅"
                elif status_str == "FAILED":
                    icon = "❌"
                elif status_str == "IN_PROGRESS":
                    icon = "⏳"
                else:
                    icon = "📝"

                text += f"{icon} <b>{topic_name}</b>\n"

                if a1_pct is not None:
                    bar = "🟩" * (a1_pct // 10) + "⬜" * (10 - a1_pct // 10)
                    text += f"  1-уриниш: {a1_score}/15 ({a1_pct}%) {bar}\n"
                else:
                    text += f"  1-уриниш: топширилмаган\n"

                if a2_pct is not None:
                    bar2 = "🟩" * (a2_pct // 10) + "⬜" * (10 - a2_pct // 10)
                    delta = (a2_pct - a1_pct) if a1_pct is not None else 0
                    delta_str = f"+{delta}" if delta >= 0 else str(delta)
                    text += f"  2-уриниш: {a2_score}/15 ({a2_pct}%) {bar2} ({delta_str} б.п.)\n"
                elif a1_pct is not None:
                    text += f"  2-уриниш: ҳали топширилмаган\n"

                text += "\n"

        await update.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        logger.error("show_all_results error: %s", e, exc_info=True)
        await update.message.reply_text(
            "⚠️ Натижаларни юклашда хатолик. Илтимос, кейинроқ уриниб кўринг."
        )
