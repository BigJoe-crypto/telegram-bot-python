import telebot
from dotenv import load_dotenv
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime
import logging
import time

# Import analysis functions
from analysis import (
    generate_daily_outlook,
    generate_signal,
    is_market_open,
    fetch_news,
    get_live_gold_price
)

# ────────────────────────────────────────────────
# Setup
# ────────────────────────────────────────────────

load_dotenv()

# Logging setup – very important for Railway debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This goes to Railway logs
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
USER_CHAT_ID = os.getenv('USER_CHAT_ID')

if not BOT_TOKEN:
    logger.critical("BOT_TOKEN not found in .env file. Exiting.")
    exit(1)

if not USER_CHAT_ID:
    logger.warning("USER_CHAT_ID not set in .env – scheduled messages will be disabled")

bot = telebot.TeleBot(BOT_TOKEN)

logger.info("Telegram Bot initialized successfully")

# ────────────────────────────────────────────────
# Bot Commands Menu
# ────────────────────────────────────────────────

def register_bot_commands():
    commands = [
        telebot.types.BotCommand("start", "Start the bot"),
        telebot.types.BotCommand("help", "Show help"),
        telebot.types.BotCommand("outlook", "Get today's XAUUSD outlook"),
        telebot.types.BotCommand("signal", "Check current buy/sell signal"),
        telebot.types.BotCommand("news", "See recent gold news"),
        telebot.types.BotCommand("price", "Get live gold price & chart links"),
    ]
    try:
        bot.set_my_commands(commands)
        logger.info("Bot commands menu registered successfully")
    except Exception as e:
        logger.error(f"Failed to register bot commands: {e}")

register_bot_commands()

# ────────────────────────────────────────────────
# Scheduler Setup
# ────────────────────────────────────────────────

scheduler = BackgroundScheduler(timezone=pytz.timezone('Africa/Lagos'))

# Daily outlook: Mon–Thu at 9:00 AM WAT
scheduler.add_job(
    lambda: send_daily_outlook(),
    trigger=CronTrigger(day_of_week='mon-thu', hour=9, minute=0),
    id='daily_outlook',
    replace_existing=True
)

def send_daily_outlook():
    if not USER_CHAT_ID:
        return
    try:
        outlook = generate_daily_outlook()
        msg = f"Good morning, Joseph! 🌅\nHere's today's XAUUSD outlook:\n\n{outlook}"
        bot.send_message(USER_CHAT_ID, msg)
        logger.info("Daily outlook sent successfully")
    except Exception as e:
        logger.error(f"Failed to send daily outlook: {e}")

# Signal check every 5 minutes during active sessions
def monitor_signals():
    if not USER_CHAT_ID:
        return
    now_utc = datetime.utcnow()
    hour_utc = now_utc.hour
    active_hours = (7 <= hour_utc <= 17) or (12 <= hour_utc <= 21)
    if not active_hours or not is_market_open():
        return
    try:
        signal_text = generate_signal()
        if signal_text and "No clear signal" not in signal_text and "Market closed" not in signal_text:
            bot.send_message(
                USER_CHAT_ID,
                f"🔔 New XAUUSD Signal Detected!\n\n{signal_text}"
            )
            logger.info("Signal notification sent")
    except Exception as e:
        logger.error(f"Signal monitoring error: {e}")

scheduler.add_job(
    monitor_signals,
    'interval',
    minutes=5,
    id='signal_monitor',
    replace_existing=True
)

# Morning market status check
scheduler.add_job(
    lambda: send_market_status(),
    trigger=CronTrigger(hour=8, minute=0),
    id='morning_market_check',
    replace_existing=True
)

def send_market_status():
    if not USER_CHAT_ID:
        return
    if not is_market_open():
        try:
            bot.send_message(USER_CHAT_ID, "ℹ️ Gold market is closed today (weekend or holiday).")
            logger.info("Market closed notification sent")
        except Exception as e:
            logger.error(f"Failed to send market closed message: {e}")

scheduler.start()
logger.info("Scheduler started successfully")

# Give scheduler a moment to initialize
time.sleep(1.5)

# ────────────────────────────────────────────────
# Command Handlers
# ────────────────────────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def start_help(message):
    text = (
        "Hello Joseph! 👋 Welcome to your Gold (XAUUSD) Signals Bot.\n\n"
        "Available commands:\n"
        "• /outlook  →  Today's market outlook & bias\n"
        "• /signal   →  Current buy/sell signal (if available)\n"
        "• /news     →  Recent gold news headlines\n"
        "• /price    →  Live gold price + chart links\n\n"
        "Automatic features:\n"
        "• Daily outlook at 9:00 AM WAT (Mon–Thu)\n"
        "• Signal checks every 5 min during active hours\n\n"
        "Trade responsibly — this is not financial advice."
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['outlook'])
def outlook_handler(message):
    try:
        bot.reply_to(message, generate_daily_outlook())
    except Exception as e:
        logger.error(f"Outlook handler error: {e}")
        bot.reply_to(message, "Sorry, error generating outlook. Try again later.")

@bot.message_handler(commands=['signal'])
def signal_handler(message):
    try:
        sig = generate_signal()
        reply = sig if sig else "No clear/high-probability signal right now."
        bot.reply_to(message, reply)
    except Exception as e:
        logger.error(f"Signal handler error: {e}")
        bot.reply_to(message, "Error checking signals. Try again later.")

@bot.message_handler(commands=['news'])
def news_handler(message):
    try:
        news_text = fetch_news()
        bot.reply_to(message, news_text if news_text else "Could not load news right now.")
    except Exception as e:
        logger.error(f"News handler error: {e}")
        bot.reply_to(message, "Error fetching news. Try again.")

@bot.message_handler(commands=['price'])
def price_handler(message):
    try:
        price_text = get_live_gold_price()
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        full_text = f"{price_text}\n\n(Last checked: {timestamp})"
        bot.reply_to(message, full_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Price handler error: {e}")
        bot.reply_to(message, "Could not load price info right now. Try again later.")

@bot.message_handler(func=lambda m: True)
def unknown_message(message):
    bot.reply_to(
        message,
        "Sorry, I don't understand that command.\nUse /start or /help for available options."
    )

# ────────────────────────────────────────────────
# Start the bot
# ────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting Gold Signals Telegram Bot...")
    print("Bot is running... Press Ctrl+C to stop")

    try:
        bot.infinity_polling(
            timeout=30,
            long_polling_timeout=30,
            skip_pending=True,
            allowed_updates=['message', 'callback_query']
        )
    except Exception as e:
        logger.critical(f"Bot polling crashed: {e}", exc_info=True)
    finally:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        logger.info("Bot shutdown complete.")
