# bot.py
import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError

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

async def send_alert(message: str):
    """Отправка оповещения в Telegram"""
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=ALERT_CHAT_ID, text=message, parse_mode="Markdown")
        logger.info(f"Alert sent: {message}")
    except TelegramError as e:
        logger.error(f"Failed to send Telegram alert: {e}")

async def monitor_funding_rates():
    """Основной цикл мониторинга ставок финансирования"""
    logger.info("Starting funding rate monitor...")
    while True:
        try:
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
                    await send_alert(alert_msg)

            logger.info(f"Completed monitoring cycle. Sleeping for {UPDATE_INTERVAL} seconds...")

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)

        await asyncio.sleep(UPDATE_INTERVAL)

def main():
    """Точка входа для Heroku worker"""
    logger.info("Bot worker starting...")
    try:
        asyncio.run(monitor_funding_rates())
    except KeyboardInterrupt:
        logger.info("Bot worker stopped by user.")
    except Exception as e:
        logger.critical(f"Bot worker crashed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()        asyncio.run(monitor_funding_rates())
    except KeyboardInterrupt:
        logger.info("Bot worker stopped by user.")
    except Exception as e:
        logger.critical(f"Bot worker crashed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
