# bot.py
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import (
    TELEGRAM_BOT_TOKEN,
    ALERT_CHAT_ID,
    MONITORED_PAIRS,
    CRITICAL_FR_LONG,
    CRITICAL_FR_SHORT,
    UPDATE_INTERVAL,
    DEBUG,
)
from data_fetcher import get_funding_rates

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG if DEBUG else logging.INFO
)
logger = logging.getLogger(__name__)

PAIRS = [p.strip() for p in MONITORED_PAIRS.split(",")]

# ===== Команды бота =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот мониторинга ставок финансирования.\nИспользуй /status для просмотра текущих ставок.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Начать работу\n/status - Текущие ставки\n/help - Помощь")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = get_funding_rates()
    if not rates:
        await update.message.reply_text("Не удалось получить данные.")
        return

    message = "📊 Текущие ставки финансирования:\n\n"
    for pair in PAIRS:
        if pair in rates:
            rate = rates[pair]["rate"]
            message += f"{pair}: {rate:.6f}\n"
        else:
            message += f"{pair}: N/A\n"
    await update.message.reply_text(f"```\n{message}\n```", parse_mode="Markdown")

# ===== Мониторинг в фоне =====

async def monitor_funding_rates(context: ContextTypes.DEFAULT_TYPE):
    """Фоновый мониторинг ставок"""
    rates = get_funding_rates()
    logger.debug(f"Funding rates fetched: {rates}")

    for pair in PAIRS:
        if pair not in rates:
            logger.warning(f"Pair {pair} not found in funding rates data")
            continue

        rate = float(rates[pair].get("rate", 0))
        alert_msg = None

        if rate <= CRITICAL_FR_LONG:
            alert_msg = (
                f"🚨 *LONG CRITICAL ALERT*\n"
                f"Pair: `{pair}`\n"
                f"Funding Rate: `{rate:.6f}`\n"
                f"Threshold: `{CRITICAL_FR_LONG}`"
            )
        elif rate >= CRITICAL_FR_SHORT:
            alert_msg = (
                f"🚨 *SHORT CRITICAL ALERT*\n"
                f"Pair: `{pair}`\n"
                f"Funding Rate: `{rate:.6f}`\n"
                f"Threshold: `{CRITICAL_FR_SHORT}`"
            )

        if alert_msg:
            try:
                await context.bot.send_message(chat_id=ALERT_CHAT_ID, text=alert_msg, parse_mode="Markdown")
                logger.info(f"Alert sent: {alert_msg}")
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

# ===== Основная функция =====

def main():
    """Запуск бота с обработчиками и фоновым мониторингом"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))

    # Фоновый мониторинг каждые UPDATE_INTERVAL секунд
    application.job_queue.run_repeating(monitor_funding_rates, interval=UPDATE_INTERVAL)

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
