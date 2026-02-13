from telebot import TeleBot
from telebot.types import BotCommand

def register_commands(bot: TeleBot):
    """
    Register bot commands with Telegram.

    Args:
        bot (TeleBot): The TeleBot instance.
    """
    commands = [
        BotCommand("start", "Start the bot and see welcome message"),
        BotCommand("outlook", "Get today's XAUUSD market outlook"),
        BotCommand("signal", "Check for current buy/sell signal"),
        BotCommand("news", "See recent gold news headlines"),
        BotCommand("help", "Show available commands"),
    ]
    
    bot.set_my_commands(commands)
    print("Bot commands registered successfully")

# Message handlers (these make the bot actually reply when commands are sent)

@bot.message_handler(commands=['start', 'help'])
def start_help(message):
    welcome_text = (
        "Hello Joseph! I'm your XAUUSD trading bot.\n\n"
        "Available commands:\n"
        "/outlook - Today's market outlook\n"
        "/signal - Check current signal\n"
        "/news - Recent gold news\n"
        "\nBot runs automatically for daily messages at 9 AM (Mon–Thu)."
    )
    bot.reply_to(message, welcome_text)


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


# Optional: echo any non-command text (for debugging)
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Unknown command. Try /start or /help.")
