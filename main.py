import telebot
from dotenv import load_dotenv
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime
from analysis import generate_daily_outlook, generate_signal, is_market_open, fetch_news

# Load environment variables
load_dotenv()

# Bot initialization
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))

# Your Telegram chat ID
USER_CHAT_ID = '1684090709'

# Scheduler (Lagos time)
scheduler = BackgroundScheduler(timezone=pytz.timezone('Africa/Lagos'))

# Daily outlook Mon–Thu at 9 AM WAT
scheduler.add_job(
    lambda: bot.send_message(
        USER_CHAT_ID,
        f"Good morning, Joseph! Here's today's XAUUSD outlook:\n\n{generate_daily_outlook()}"
    ),
    CronTrigger(day_of_week='mon-thu', hour=9, minute=0)
)

# Signal check every 5 min during sessions
def monitor_signals():
    now = datetime.utcnow()
    hour_utc = now.hour
    if (8 <= hour_utc <= 16) or (13 <= hour_utc <= 21):
        if is_market_open():
            signal = generate_signal()
            if signal:
                bot.send_message(USER_CHAT_ID, signal)

scheduler.add_job(monitor_signals, 'interval', minutes=5)

# Holiday check
scheduler.add_job(
    lambda: bot.send_message(USER_CHAT_ID, "Gold market closed today.") if not is_market_open() else None,
    CronTrigger(hour=8, minute=0)
)

scheduler.start()

# --- Command Handlers (moved here so 'bot' is already defined) ---

@bot.message_handler(commands=['start', 'help'])
def start_help(message):
    text = (
        "Hello Joseph! I'm your XAUUSD trading bot.\n\n"
        "Commands:\n"
        "/outlook → Today's market outlook\n"
        "/signal → Current buy/sell signal\n"
        "/news → Recent gold news\n"
        "\nBot sends automatic outlook at 9 AM Mon–Thu."
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['outlook'])
def outlook(message):
    bot.reply_to(message, generate_daily_outlook())

@bot.message_handler(commands=['signal'])
def signal_cmd(message):
    sig = generate_signal()
    bot.reply_to(message, sig or "No clear signal right now.")

@bot.message_handler(commands=['news'])
def news_cmd(message):
    bot.reply_to(message, fetch_news())

# Optional: reply to any non-command text
@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, "Unknown command. Try /start or /help.")

print("Handlers registered - starting polling")
bot.polling(none_stop=True)
