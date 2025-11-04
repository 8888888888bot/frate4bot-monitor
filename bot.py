import asyncio
import logging
import json
import requests
import os
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from data_fetcher import get_funding_rates
from config import (
    TELEGRAM_BOT_TOKEN,
    ALERT_CHAT_ID,
    MONITORED_PAIRS as DEFAULT_MONITORED_PAIRS,
    CRITICAL_FR_LONG as DEFAULT_LONG,
    CRITICAL_FR_SHORT as DEFAULT_SHORT,
    UPDATE_INTERVAL,
    DEBUG
)

# ======================
# GITHUB GIST CONFIG
# ======================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_GIST_ID = os.getenv("GITHUB_GIST_ID")
GIST_URL = f"https://api.github.com/gists/{GITHUB_GIST_ID}"

DEFAULT_DATA = {
    "settings": {
        "alerts_enabled": True,
        "critical_fr_long": DEFAULT_LONG,
        "critical_fr_short": DEFAULT_SHORT,
        "monitored_pairs": list(DEFAULT_MONITORED_PAIRS)
    },
    "history": {},
    "daily_stats": {
        "alerts_count": 0,
        "max_long": [0, ""],
        "max_short": [0, ""]
    }
}

def load_data_from_gist():
    if not GITHUB_TOKEN or not GITHUB_GIST_ID:
        logging.warning("GITHUB_TOKEN or GITHUB_GIST_ID not set. Using defaults.")
        return DEFAULT_DATA.copy()
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(GIST_URL, headers=headers, timeout=10)
        response.raise_for_status()
        gist = response.json()
        content = gist["files"]["frate4bot-data.json"]["content"]
        data = json.loads(content)
        logging.info("✅ Data loaded from Gist")
        return data
    except Exception as e:
        logging.error(f"❌ Failed to load from Gist: {e}. Using defaults.")
        return DEFAULT_DATA.copy()

def save_data_to_gist(data):
    if not GITHUB_TOKEN or not GITHUB_GIST_ID:
        logging.warning("GITHUB_TOKEN or GITHUB_GIST_ID not set. Skip saving.")
        return False
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        payload = {
            "files": {
                "frate4bot-data.json": {
                    "content": json.dumps(data, indent=2, ensure_ascii=False)
                }
            }
        }
        response = requests.patch(GIST_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logging.info("✅ Data saved to Gist")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to save to Gist: {e}")
        return False

# ======================
# INIT DATA
# ======================
data = load_data_from_gist()
user_settings = data["settings"]
history = data["history"]
daily_stats = data["daily_stats"]

# Convert list → set for pairs
if "monitored_pairs" in user_settings:
    user_settings["monitored_pairs"] = set(user_settings["monitored_pairs"])

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG if DEBUG else logging.INFO
)
logger = logging.getLogger(__name__)

application = None

# ======================
# UTILS
# ======================

def get_trend(pair: str) -> str:
    if pair not in history or len(history[pair]) < 3:
        return "⏺️"
    rates = [r for _, r in history[pair][-3:]]
    if rates[-1] > rates[-2] > rates[-3]:
        return "🔼 Растёт"
    elif rates[-1] < rates[-2] < rates[-3]:
        return "🔽 Падает"
    else:
        return "⏹️ Стабильно"

def add_to_history(pair: str, rate: float):
    now = datetime.utcnow().strftime("%H:%M")
    if pair not in history:
        history[pair] = []
    history[pair].append([now, rate])
    if len(history[pair]) > 12:
        history[pair].pop(0)

    if rate <= daily_stats["max_long"][0]:
        daily_stats["max_long"] = [rate, pair]
    if rate >= daily_stats["max_short"][0]:
        daily_stats["max_short"] = [rate, pair]

    if len(history[pair]) % 5 == 0:
        save_to_gist()

def save_to_gist():
    serializable_data = {
        "settings": {
            "alerts_enabled": user_settings["alerts_enabled"],
            "critical_fr_long": user_settings["critical_fr_long"],
            "critical_fr_short": user_settings["critical_fr_short"],
            "monitored_pairs": list(user_settings["monitored_pairs"])
        },
        "history": history,
        "daily_stats": daily_stats
    }
    save_data_to_gist(serializable_data)

def format_funding_rate(pair: str, fr: float) -> str:
    alert_long = fr <= user_settings["critical_fr_long"]
    alert_short = fr >= user_settings["critical_fr_short"]
    emoji = "🔻" if alert_long else "🔺" if alert_short else "⬇️" if fr < 0 else "⬆️" if fr > 0 else "➖"
    trend = get_trend(pair)
    return f"{pair}: {fr:.6f} {emoji} {trend}"

# ======================
# MAIN MENU
# ======================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📈 Статус"],
        ["📋 Все пары", "🔔 Настройки"],
        ["❓ Помощь"]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# ======================
# HANDLERS
# ======================

async def send_funding_alerts(context: ContextTypes.DEFAULT_TYPE):
    if not user_settings["alerts_enabled"]:
        return

    rates = get_funding_rates()
    for pair in user_settings["monitored_pairs"]:
        if pair not in rates:
            continue
        fr = rates[pair]
        add_to_history(pair, fr)

        alert = None
        if fr <= user_settings["critical_fr_long"]:
            alert = f"⚠️ LONG funding alert!\n{pair}: {fr:.6f} ≤ {user_settings['critical_fr_long']:.6f}"
            daily_stats["alerts_count"] += 1
        elif fr >= user_settings["critical_fr_short"]:
            alert = f"⚠️ SHORT funding alert!\n{pair}: {fr:.6f} ≥ {user_settings['critical_fr_short']:.6f}"
            daily_stats["alerts_count"] += 1

        if alert:
            try:
                await context.bot.send_message(chat_id=ALERT_CHAT_ID, text=alert)
                logger.info(f"Alert sent: {alert}")
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
    save_to_gist()

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    global daily_stats
    report = (
        f"📆 Ежедневный отчёт ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC):\n"
        f"• Всего алертов: {daily_stats['alerts_count']}\n"
        f"• Макс. LONG: {daily_stats['max_long'][0]:.6f} ({daily_stats['max_long'][1]})\n"
        f"• Макс. SHORT: {daily_stats['max_short'][0]:.6f} ({daily_stats['max_short'][1]})\n"
    )
    if daily_stats["alerts_count"] == 0:
        report += "• Рекомендация: спокойный день — можно искать новые пары."
    elif daily_stats["max_short"][0] > 0.002:
        report += "• Рекомендация: высокие SHORT ставки — возможен шорт-сквиз!"
    else:
        report += "• Рекомендация: следите за трендами."

    try:
        await context.bot.send_message(chat_id=ALERT_CHAT_ID, text=report)
        logger.info("Daily report sent.")
    except Exception as e:
        logger.error(f"Failed to send daily report: {e}")

    daily_stats.update({"alerts_count": 0, "max_long": [0, ""], "max_short": [0, ""]})
    save_to_gist()

# --- Commands ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я FRate Bot с расширенными настройками.\nВыберите действие:",
        reply_markup=MAIN_MENU
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Возможности:\n"
        "• Настройки порогов и пар\n"
        "• История ставок (/history BTC_USDT)\n"
        "• Ежедневный отчёт (09:00 UTC)\n"
        "• Умные тренды и алерты",
        reply_markup=MAIN_MENU
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = get_funding_rates()
    lines = ["📊 Текущие ставки:"]
    for pair in sorted(user_settings["monitored_pairs"]):
        fr = rates.get(pair)
        if fr is not None:
            lines.append(format_funding_rate(pair, fr))
        else:
            lines.append(f"{pair}: ❌ Недоступен")
    await update.message.reply_text("\n".join(lines), reply_markup=MAIN_MENU)

async def cmd_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = get_funding_rates()
    if not rates:
        await update.message.reply_text("❌ Не удалось загрузить пары.", reply_markup=MAIN_MENU)
        return
    lines = ["🌐 Все пары (топ-20 по |ставка|):"]
    sorted_pairs = sorted(rates.items(), key=lambda x: abs(x[1]), reverse=True)
    for pair, fr in sorted_pairs[:20]:
        lines.append(format_funding_rate(pair, fr))
    await update.message.reply_text("\n".join(lines), reply_markup=MAIN_MENU)

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("UsageId: /history BTC_USDT")
        return
    pair = context.args[0].upper()
    if pair not in history or not history[pair]:
        await update.message.reply_text(f"Нет истории для {pair}.")
        return
    lines = [f"📈 История {pair} (последние {len(history[pair])} записей):"]
    for ts, rate in history[pair]:
        marker = " ⚠️" if (rate <= user_settings["critical_fr_long"] or rate >= user_settings["critical_fr_short"]) else ""
        lines.append(f"{ts} → {rate:.6f}{marker}")
    await update.message.reply_text("\n".join(lines), reply_markup=MAIN_MENU)

# --- Settings ---
async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем список всех доступных пар (можно кэшировать)
    rates = get_funding_rates()
    all_pairs = sorted(rates.keys()) if rates else []

    # Формируем текст настроек
    settings_text = (
        "🔔 Настройки:\n"
        f"Алерты: {'✅ ВКЛ' if user_settings['alerts_enabled'] else '❌ ВЫКЛ'}\n"
        f"Пары: {', '.join(sorted(user_settings['monitored_pairs'])) or '—'}\n\n"
        "Нажмите на кнопки для изменения:"
    )

    # Кнопки для LONG/SHORT
    long_buttons = [
        InlineKeyboardButton("➖", callback_data="long_dec"),
        InlineKeyboardButton(f"{user_settings['critical_fr_long']:.4f}", callback_data="long_val"),
        InlineKeyboardButton("➕", callback_data="long_inc")
    ]
    short_buttons = [
        InlineKeyboardButton("➖", callback_data="short_dec"),
        InlineKeyboardButton(f"{user_settings['critical_fr_short']:.4f}", callback_data="short_val"),
        InlineKeyboardButton("➕", callback_data="short_inc")
    ]

    # Кнопки для пар
    add_button = InlineKeyboardButton("➕ Добавить пару", callback_data="add_pair_menu")
    remove_button = InlineKeyboardButton("➖ Удалить пару", callback_data="remove_pair_menu")
    reset_button = InlineKeyboardButton("🔄 Сбросить настройки", callback_data="reset_settings")

    # Создаём клавиатуру
    keyboard = [
        [InlineKeyboardButton("⚙️ Алерты", callback_data="toggle_alerts")],
        long_buttons,
        short_buttons,
        [add_button],
        [remove_button],
        [reset_button]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(update, Update):
        await update.message.reply_text(settings_text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(settings_text, reply_markup=reply_markup)

# --- INLINE MENU FOR ADDING PAIR ---
async def show_add_pair_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = get_funding_rates()
    if not rates:
        await update.callback_query.answer("Не удалось загрузить пары.", show_alert=True)
        return

    # Берём топ-20 пар по абсолютной ставке
    sorted_pairs = sorted(rates.items(), key=lambda x: abs(x[1]), reverse=True)
    top_pairs = [p for p, _ in sorted_pairs[:20]]

    # Создаём кнопки для выбора пары
    buttons = []
    for pair in top_pairs:
        buttons.append([InlineKeyboardButton(pair, callback_data=f"add_{pair}")])

    # Добавляем кнопку "Назад"
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings")])

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.callback_query.edit_message_text("Выберите пару для добавления:", reply_markup=reply_markup)

# --- INLINE MENU FOR REMOVING PAIR ---
async def show_remove_pair_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_settings["monitored_pairs"]:
        await update.callback_query.answer("Нет отслеживаемых пар.", show_alert=True)
        return

    buttons = []
    for pair in sorted(user_settings["monitored_pairs"]):
        buttons.append([InlineKeyboardButton(pair, callback_data=f"remove_{pair}")])

    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings")])

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.callback_query.edit_message_text("Выберите пару для удаления:", reply_markup=reply_markup)

# --- Button Handler ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "toggle_alerts":
        user_settings["alerts_enabled"] = not user_settings["alerts_enabled"]
        save_to_gist()
    elif data == "long_val":
        pass  # Это просто отображение значения
    elif data == "short_val":
        pass  # Это просто отображение значения
    elif data == "long_dec":
        user_settings["critical_fr_long"] -= 0.0001
        save_to_gist()
    elif data == "long_inc":
        user_settings["critical_fr_long"] += 0.0001
        save_to_gist()
    elif data == "short_dec":
        user_settings["critical_fr_short"] -= 0.0001
        save_to_gist()
    elif data == "short_inc":
        user_settings["critical_fr_short"] += 0.0001
        save_to_gist()
    elif data == "add_pair_menu":
        await show_add_pair_menu(query, context)
        return
    elif data == "remove_pair_menu":
        await show_remove_pair_menu(query, context)
        return
    elif data.startswith("add_"):
        pair = data[4:]  # Убираем "add_"
        user_settings["monitored_pairs"].add(pair)
        save_to_gist()
        await query.answer(f"✅ {pair} добавлена", show_alert=True)
        await show_settings(query, context)
        return
    elif data.startswith("remove_"):
        pair = data[7:]  # Убираем "remove_"
        if pair in user_settings["monitored_pairs"]:
            user_settings["monitored_pairs"].discard(pair)
            save_to_gist()
            await query.answer(f"✅ {pair} удалена", show_alert=True)
        else:
            await query.answer(f"❌ {pair} не в списке", show_alert=True)
        await show_settings(query, context)
        return
    elif data == "reset_settings":
        user_settings.update({
            "alerts_enabled": True,
            "critical_fr_long": DEFAULT_LONG,
            "critical_fr_short": DEFAULT_SHORT,
            "monitored_pairs": set(DEFAULT_MONITORED_PAIRS)
        })
        history.clear()
        daily_stats.update({"alerts_count": 0, "max_long": [0, ""], "max_short": [0, ""]})
        save_to_gist()
        await query.answer("Настройки сброшены к значениям по умолчанию.", show_alert=True)
        await show_settings(query, context)
        return
    elif data == "back_to_settings":
        await show_settings(query, context)
        return

    await show_settings(query, context)

# --- Misc ---
async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "awaiting_pair" in context.user_data:
        await handle_text_input(update, context)
    else:
        await update.message.reply_text("Неизвестная команда. Используйте меню.", reply_markup=MAIN_MENU)

# --- Init ---
async def post_init(application: Application):
    if application.job_queue is None:
        logger.error("Job queue is None!")
        return
    application.job_queue.run_repeating(send_funding_alerts, interval=UPDATE_INTERVAL, first=10)
    application.job_queue.run_daily(send_daily_report, time=timedelta(hours=9))  # 09:00 UTC
    logger.info("✅ Мониторинг и ежедневный отчёт запущены.")

def main():
    global application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Commands
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("all", cmd_all))
    application.add_handler(CommandHandler("history", cmd_history))

    # Menu buttons
    application.add_handler(MessageHandler(filters.Regex("^🔔 Настройки$"), show_settings))
    application.add_handler(MessageHandler(filters.Regex("^📈 Статус$"), cmd_status))
    application.add_handler(MessageHandler(filters.Regex("^📋 Все пары$"), cmd_all))
    application.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), cmd_help))

    # Callbacks
    application.add_handler(CallbackQueryHandler(button_handler))

    # Fallback
    application.add_handler(MessageHandler(filters.ALL, handle_unknown))

    logger.info("🚀 Бот запущен с улучшенным интерфейсом настроек!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
