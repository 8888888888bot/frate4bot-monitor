import os

# Heroku
APP_NAME = os.getenv("APP_NAME", "frate4bot-monitor")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8300632768:AAHo4A6wLly2LrxHysgdAAgTFIeGsNrm7CM")
ALERT_CHAT_ID = int(os.getenv("ALERT_CHAT_ID", "7295147132"))

# Gate.io
GATEIO_API_KEY = os.getenv("GATEIO_API_KEY", "625abba4fb6164fb87db1ae951e8120e")
GATEIO_SECRET_KEY = os.getenv("GATEIO_SECRET_KEY", "a1d4c5467d8f01a4c0cc19a7f906984b578cad01432459d75f76a8bc3dd5f7f8")

# Monitoring
MONITORED_PAIRS = os.getenv("MONITORED_PAIRS", "BTC_USDT,ETH_USDT,SOL_USDT").split(",")
CRITICAL_FR_LONG = float(os.getenv("CRITICAL_FR_LONG", "-0.001"))
CRITICAL_FR_SHORT = float(os.getenv("CRITICAL_FR_SHORT", "0.001"))
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "90"))

# Debug
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
