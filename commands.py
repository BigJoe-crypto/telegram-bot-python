from telebot import TeleBot
from telebot.types import BotCommand

def register_commands(bot: TeleBot):
    """
    Register bot commands with Telegram.

    Args:
        bot (TeleBot): The TeleBot instance.
    """
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("hello", "Hello"),
    ]
    
    bot.set_my_commands(commands)
# ... (your existing code: imports, bot init, scheduler, etc.)

# Command handlers from commands.py
from analysis import generate_daily_outlook, generate_signal, fetch_news

@bot.message_handler(commands=['outlook'])
def outlook(message):
    bot.reply_to(message, generate_daily_outlook())

@bot.message_handler(commands=['signal'])
def signal_cmd(message):
    sig = generate_signal()
    bot.reply_to(message, sig or "No signal right now.")

@bot.message_handler(commands=['news'])
def news_cmd(message):
    bot.reply_to(message, fetch_news())

# Optional: welcome message
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Hello Joseph! Bot is alive.\nCommands: /outlook /signal /news")

print("Handlers registered - starting polling")
bot.polling(none_stop=True)
