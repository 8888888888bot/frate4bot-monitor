import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from data_fetcher import get_funding_rates
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

# Global bot app reference for job access
application = None

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
        "Отправляю алерты при превышении критических значений.\n"
        "Используй /help для помощи."
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start — приветствие\n"
        "/help — список команд\n"
        "/status — текущие ставки по отслеживаемым парам"
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = get_funding_rates()
    lines = ["📊 Текущие ставки финансирования:"]
    for pair in MONITORED_PAIRS:
        fr = rates.get(pair, "N/A")
        lines.append(f"{pair}: {fr:.6f}" if isinstance(fr, float) else f"{pair}: {fr}")
    await update.message.reply_text("\n".join(lines))

async def post_init(application: Application):
    # Schedule recurring job using job_queue
    application.job_queue.run_repeating(
        send_funding_alerts,
        interval=UPDATE_INTERVAL,
        first=10  # First check after 10 seconds
    )
    logger.info("Monitoring job scheduled.")

def main():
    global application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Command handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("status", cmd_status))

    logger.info("Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
