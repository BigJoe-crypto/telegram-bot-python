import telebot
from dotenv import load_dotenv
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from analysis import generate_daily_outlook, generate_signal, is_market_open

# Load environment variables (BOT_TOKEN from Railway Variables)
load_dotenv()
bot = telebot.TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))

# Your personal Telegram chat ID
USER_CHAT_ID = '1684090709'

# Scheduler for automated messages (Lagos time = WAT = Africa/Lagos)
scheduler = BackgroundScheduler(timezone=pytz.timezone('Africa/Lagos'))

# 1. Send daily outlook Monday–Thursday at 9:00 AM WAT
scheduler.add_job(
    lambda: bot.send_message(
        USER_CHAT_ID,
        f"Good morning, Joseph! Here's today's XAUUSD outlook:\n\n{generate_daily_outlook()}"
    ),
    CronTrigger(day_of_week='mon-thu', hour=9, minute=0)
)

# 2. Check for trading signals every 5 minutes during London/NY sessions
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

# 3. Daily holiday/weekend check at 8:00 AM UTC
def holiday_check():
    if not is_market_open():
        bot.send_message(USER_CHAT_ID, "Gold market is closed today (holiday or weekend). No signals will be generated.")

scheduler.add_job(holiday_check, CronTrigger(hour=8, minute=0))

# Start the scheduler
scheduler.start()

# Start the bot (polling mode – Railway keeps it alive)
print("Bot is running...")
bot.polling(none_stop=True)
