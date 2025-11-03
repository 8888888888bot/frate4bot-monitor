import asyncio
from telegram import Bot
from config import *
from data_fetcher import get_funding_rates

async def main():
    bot = Bot(TELEGRAM_BOT_TOKEN)
    while True:
        rates = get_funding_rates()
        for pair in [x.strip() for x in MONITORED_PAIRS.split(",")]:
            if pair in rates:
                rate = rates[pair]["rate"]
                if rate <= CRITICAL_FR_LONG:
                    await bot.send_message(ALERT_CHAT_ID, f"⚠️ *LONG ALERT* `{pair}`: {rate:.6f}", parse_mode="Markdown")
                elif rate >= CRITICAL_FR_SHORT:
                    await bot.send_message(ALERT_CHAT_ID, f"⚠️ *SHORT ALERT* `{pair}`: {rate:.6f}", parse_mode="Markdown")
        await asyncio.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
