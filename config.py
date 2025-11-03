import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALERT_CHAT_ID = os.getenv("ALERT_CHAT_ID")
GATEIO_API_KEY = os.getenv("GATEIO_API_KEY")
GATEIO_SECRET_KEY = os.getenv("GATEIO_SECRET_KEY")

MONITORED_PAIRS = os.getenv("MONITORED_PAIRS", "BTC_USDT,ETH_USDT,SOL_USDT")
CRITICAL_FR_LONG = float(os.getenv("CRITICAL_FR_LONG", "-0.001"))
CRITICAL_FR_SHORT = float(os.getenv("CRITICAL_FR_SHORT", "0.001"))
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "90"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
