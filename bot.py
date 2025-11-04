import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from data_fetcher import get_funding_rates, get_all_pairs
from config import (
    TELEGRAM_BOT_TOKEN,
    ALERT_CHAT_ID,
    MONITORED_PAIRS,
    CRITICAL_FR_LONG,
    CRITICAL_FR_SHORT,
    UPDATE_INTERVAL,
    DEBUG
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG if DEBUG else logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальная переменная для доступа к приложению
application = None

# Клавиатура
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📈 Статус", "🔄 Обновить сейчас"],
        ["📋 Все пары", "🔔 Настройки"],
        ["❓ Помощь"]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

def format_funding_rate(pair: str, fr: float) -> str:
    """Добавляет эмодзи в зависимости от значения ставки"""
    if fr <= CRITICAL_FR_LONG:
        emoji = "🔻"  # Сильный LONG (отрицательная ставка)
    elif fr >= CRITICAL_FR_SHORT:
        emoji = "🔺"  # Сильный SHORT (положительная ставка)
    elif fr < 0:
        emoji = "⬇️"  # Слабый LONG
    elif fr > 0:
        emoji = "⬆️"  # Слабый SHORT
    else:
        emoji = "➖"  # Ноль
    return f"{pair}: {fr:.6f} {emoji}"

async def send_funding_alerts(context: ContextTypes.DEFAULT_TYPE):
    rates = get_funding_rates()
    for pair in MONITORED_PAIRS:
        if pair not in rates:
            logger.warning(f"Pair {pair} not found in funding rates")
            continue
        fr = rates[pair]
        alert = None
        if fr <= CRITICAL_FR_LONG:
            alert = f"⚠️ LONG funding alert!\n{pair}: {fr:.6f} ≤ {CRITICAL_FR_LONG}"
        elif fr >= CRITICAL_FR_SHORT:
            alert = f"⚠️ SHORT funding alert!\n{pair}: {fr:.6f} ≥ {CRITICAL_FR_SHORT}"
        if alert:
            try:
                await context.bot.send_message(chat_id=ALERT_CHAT_ID, text=alert)
                logger.info(f"Alert sent: {alert}")
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для мониторинга ставок финансирования Gate.io.\n"
        "Выберите действие в меню ниже:",
        reply_markup=MAIN_MENU
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📌 Доступные команды и кнопки:\n\n"
        "• 📈 Статус — ставки по отслеживаемым парам\n"
        "• 🔄 Обновить сейчас — мгновенное обновление данных\n"
        "• 📋 Все пары — список всех доступных пар\n"
        "• 🔔 Настройки — скоро будет!\n"
        "• ❓ Помощь — эта справка\n\n"
        "Автоматические алерты приходят в чат, указанный в настройках."
    )
    await update.message.reply_text(help_text, reply_markup=MAIN_MENU)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = get_funding_rates()
    lines = ["📊 Текущие ставки по отслеживаемым парам:"]
    for pair in MONITORED_PAIRS:
        fr = rates.get(pair)
        if fr is not None:
            lines.append(format_funding_rate(pair, fr))
        else:
            lines.append(f"{pair}: ❌ Недоступен")
    await update.message.reply_text("\n".join(lines), reply_markup=MAIN_MENU)

async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = get_all_pairs()
    if not rates:
        await update.message.reply_text("❌ Не удалось загрузить список пар.", reply_markup=MAIN_MENU)
        return

    lines = ["🌐 Все доступные пары на Gate.io (топ-30):"]
    # Сортируем по абсолютному значению ставки (самые "горячие" сверху)
    sorted_pairs = sorted(rates.items(), key=lambda x: abs(x[1]), reverse=True)
    for pair, fr in sorted_pairs[:30]:  # Только топ-30 для читаемости
        lines.append(format_funding_rate(pair, fr))
    await update.message.reply_text("\n".join(lines), reply_markup=MAIN_MENU)

async def handle_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки '🔄 Обновить сейчас'"""
    await update.message.reply_text("🔄 Запрашиваю свежие данные...")
    await cmd_status(update, context)

async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙️ Настройки пока в разработке. Следите за обновлениями!", reply_markup=MAIN_MENU)

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Используйте меню или /help.", reply_markup=MAIN_MENU)

async def post_init(application: Application):
    if application.job_queue is None:
        logger.error("Job queue is None!")
        return
    application.job_queue.run_repeating(
        send_funding_alerts,
        interval=UPDATE_INTERVAL,
        first=10
    )
    logger.info(f"✅ Monitoring scheduled every {UPDATE_INTERVAL} seconds.")

def main():
    global application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Команды
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("all", cmd_all))

    # Обработка кнопок
    application.add_handler(MessageHandler(filters.Regex("^📈 Статус$"), cmd_status))
    application.add_handler(MessageHandler(filters.Regex("^🔄 Обновить сейчас$"), handle_refresh))
    application.add_handler(MessageHandler(filters.Regex("^📋 Все пары$"), cmd_all))
    application.add_handler(MessageHandler(filters.Regex("^🔔 Настройки$"), handle_settings))
    application.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), cmd_help))

    # Обработка неизвестных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))

    logger.info("🚀 Bot is starting with enhanced UI...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()    # Создаём приложение и передаём post_init
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("status", cmd_status))

    logger.info("🚀 Bot is starting...")

    # Запускаем polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
