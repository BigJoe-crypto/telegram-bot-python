import telebot
from dotenv import load_dotenv
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime
from analysis import generate_daily_outlook, generate_signal, is_market_open

# Load environment variables
load_dotenv()

# Bot initialization - use BOT_TOKEN (the name you set in Railway Variables)
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))

# Your Telegram chat ID
USER_CHAT_ID = '1684090709'

# Scheduler (Lagos time = Africa/Lagos)
scheduler = BackgroundScheduler(timezone=pytz.timezone('Africa/Lagos'))

# Daily outlook Monday–Thursday at 9:00 AM WAT
scheduler.add_job(
    lambda: bot.send_message(
        USER_CHAT_ID,
        f"Good morning, Joseph! Here's today's XAUUSD outlook:\n\n{generate_daily_outlook()}"
    ),
    CronTrigger(day_of_week='mon-thu', hour=9, minute=0)
)

# Check for trading signals every 5 minutes during London/NY sessions
def monitor_signals():
    now = datetime.utcnow()
    hour_utc = now.hour
    # London session ~08:00–16:00 UTC, NY ~13:00–21:00 UTC
    if (8 <= hour_utc <= 16) or (13 <= hour_utc <= 21):
        if is_market_open():
            signal = generate_signal()
            if signal:
                bot.send_message(USER_CHAT_ID, signal)

scheduler.add_job(monitor_signals, 'interval', minutes=5)

# Daily holiday/weekend check at 8:00 AM UTC
scheduler.add_job(
    lambda: bot.send_message(USER_CHAT_ID, "Gold market is closed today (holiday or weekend). No signals will be generated.")
    if not is_market_open() else None,
    CronTrigger(hour=8, minute=0)
)

# Start scheduler
scheduler.start()

print("Bot started - polling and scheduling active")
bot.polling(none_stop=True)
