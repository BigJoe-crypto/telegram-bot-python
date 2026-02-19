from telegram import Bot
import os

# Use environment variables for security
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8532436746:AAFO_lgbLMB39txheVxts3SCHTMAas0TSYg")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1684090709")

bot = Bot(token=TELEGRAM_TOKEN)
chat_id = TELEGRAM_CHAT_ID

def init_telegram():
    """Initialize Telegram bot (already initialized above, placeholder for structure)"""
    global bot, chat_id
    # Already initialized using environment variables
    print("Telegram bot initialized")

def send_alert(trade):
    """Send trade alert to Telegram"""
    msg = (
        f"💹 Trade Alert 💹\n"
        f"Trend: {trade['trend']}\n"
        f"Entry: {trade['entry']}\n"
        f"SL: {trade['sl']}\n"
        f"TP: {trade['tp']}\n"
    )
    bot.send_message(chat_id=chat_id, text=msg)
    print(f"Alert sent: {msg}")

def send_daily_news():
    """Send daily market news (placeholder)"""
    # Example news - replace with API or scraping logic
    headlines = [
        "Gold rises amid USD weakness",
        "US CPI data due today",
        "Geopolitical tensions impact oil & gold"
    ]
    msg = "📰 Daily Market News:\n" + "\n".join(headlines)
    bot.send_message(chat_id=chat_id, text=msg)
    print("Daily news sent")
