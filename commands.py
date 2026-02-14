from telebot import TeleBot
from telebot.types import BotCommand

# Import analysis functions
from analysis import generate_daily_outlook, generate_signal, fetch_news

def register_commands(bot: TeleBot):
    """
    Register bot commands so they appear when typing /
    """
    commands = [
        BotCommand("start", "Start the bot and see welcome message"),
        BotCommand("outlook", "Get today's XAUUSD daily outlook"),
        BotCommand("price", "Live gold price"),
        BotCommand("signal", "Check current buy/sell signal"),
        BotCommand("news", "See recent gold news headlines"),
        BotCommand("help", "Show all available commands"),
    ]
    
    bot.set_my_commands(commands)
    print("Commands registered: /start, /outlook, /signal, /news, /help")


# Handlers - these make the bot reply when commands are sent

@bot.message_handler(commands=['start', 'help'])
def start_help(message):
    text = (
        "Hello Joseph! Welcome to Tradesignal bot.\n\n"
        "Commands:\n"
        "/outlook → Today's market outlook\n"
        "/signal → Current buy/sell signal\n"
        "/news → Recent gold news\n"
        "\nBot sends daily outlook automatically at 9 AM Mon–Thu."
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['outlook'])
def outlook(message):
    bot.reply_to(message, generate_daily_outlook())

@bot.message_handler(commands=['price', 'chart'])
def price(message):
    bot.reply_to(message, get_live_gold_price())
    
@bot.message_handler(commands=['signal'])
def signal_cmd(message):
    sig = generate_signal()
    bot.reply_to(message, sig or "No clear signal right now.")

@bot.message_handler(commands=['news'])
def news_cmd(message):
    bot.reply_to(message, fetch_news())
