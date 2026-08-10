"""menu.py — Profile, Help handlers"""
from telegram import Update
from telegram.ext import ContextTypes
from ..api_client import bot_api
from ..keyboards import get_main_menu_keyboard
import logging

logger = logging.getLogger(__name__)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Асосий меню:",
        reply_markup=get_main_menu_keyboard()
    )


async def show_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        status = await bot_api.get_employee_status(user_id)

        if not status or not status.get("full_name"):
            await update.message.reply_text(
                "⚠️ Сиз рўйхатдан ўтмагансиз. /start буйруғини юборинг."
            )
            return

        full_name = status.get("full_name", "—")
        branch_name = status.get("branch_name", "—")
        phone = status.get("phone", "—")
        results = status.get("results", [])

        # Summary counts
        completed = sum(1 for r in results if r.get("attempt1_pct") is not None)
        passed = sum(1 for r in results if r.get("status") == "PASSED")
        total_topics = 4  # fixed for this system

        text = (
            f"👤 <b>Менинг профилим</b>\n\n"
            f"📛 <b>Ф.И.Ш.:</b> {full_name}\n"
            f"🏢 <b>Филиал:</b> {branch_name}\n"
            f"📞 <b>Телефон:</b> {phone}\n\n"
            f"📊 <b>Тест статистикаси:</b>\n"
            f"  • Жами мавзулар: {total_topics} та\n"
            f"  • Топширилган: {completed} та\n"
            f"  • Муваффақиятли: {passed} та\n"
        )

        # Best score
        best_scores = [r.get("attempt1_pct") or 0 for r in results if r.get("attempt1_pct")]
        if best_scores:
            best = max(best_scores)
            text += f"  • Энг юқори натижа: {best}%\n"

        await update.message.reply_text(text, parse_mode="HTML")

    except Exception as e:
        logger.error("show_my_profile error: %s", e, exc_info=True)
        await update.message.reply_text(
            "⚠️ Профилни юклашда хатолик. Илтимос, кейинроқ уриниб кўринг."
        )


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "❓ <b>Ёрдам</b>\n\n"
        "Ушбу бот Экологик назорат қўмитаси ходимлари учун мавзу бўйича билимларни тест қилиш учун мўлжалланган.\n\n"
        "<b>Қандай фойдаланиш:</b>\n"
        "1️⃣ <b>📝 Тестлар</b> — мавзу танланг ва тестни бошланг\n"
        "2️⃣ Ҳар бир савол учун <b>60 секунд</b> вақт берилади\n"
        "3️⃣ Жавобни А / Б / В / Г тугмалардан танланг\n"
        "4️⃣ 15 та савол — тест тугайди ва натижа кўрсатилади\n\n"
        "<b>📌 Эслатмалар:</b>\n"
        "• Ҳар бир мавзуда <b>2 та уриниш</b> мавжуд\n"
        "• 2-уринишга ўтиш учун <b>10 дақиқа</b> кутилади\n"
        "• 70% ва ундан юқори — ✅ Муваффақиятли\n\n"
        "<b>Буйруқлар:</b>\n"
        "/start — Менюни кўрсатиш\n"
        "/menu — Асосий менюга қайтиш\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def show_main_menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /menu command."""
    from app.bot.handlers.start import start_command
    return await start_command(update, context)
