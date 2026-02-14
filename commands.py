from typing import Optional
from telebot import TeleBot
from telebot.types import BotCommand, Message

# Import analysis functions
from analysis import (
    generate_daily_outlook,
    generate_signal,
    fetch_news,
    get_live_gold_price,
    is_market_open,           # useful for better user feedback
)


def register_commands(bot: TeleBot) -> None:
    """
    Register slash commands that appear in Telegram's command menu
    when the user types "/"
    """
    commands = [
        BotCommand("start", "Start the bot & see welcome message"),
        BotCommand("help", "Show help and available commands"),
        BotCommand("outlook", "Get today's XAUUSD market outlook"),
        BotCommand("signal", "Check current buy/sell signal (if any)"),
        BotCommand("news", "Latest gold market news headlines"),
        BotCommand("price", "Current live XAUUSD price"),
    ]

    try:
        bot.set_my_commands(commands)
        print("✅ Bot commands successfully registered")
    except Exception as e:
        print(f"❌ Failed to register bot commands: {e}")


def safe_reply(message: Message, text: str, fallback: str = "Something went wrong. Try again later.") -> None:
    """
    Helper to send replies safely and handle potential send failures
    """
    try:
        bot.reply_to(message, text)
    except Exception as e:
        print(f"Error sending reply: {e}")
        try:
            bot.reply_to(message, fallback)
        except:
            pass


@bot.message_handler(commands=['start', 'help'])
def start_help_handler(message: Message) -> None:
    """Handle /start and /help commands"""
    text = (
        "👋 Hello Joseph! Welcome to your Gold (XAUUSD) Signals Bot\n\n"
        "Available commands:\n"
        "• /outlook   →  Daily market bias, structure & key levels\n"
        "• /signal    →  Current best buy or sell setup (if detected)\n"
        "• /news      →  Recent gold-related news headlines\n"
        "• /price     →  Live XAUUSD spot price\n\n"
        "Automatic features:\n"
        "• Daily outlook sent at 9:00 AM WAT (Mon–Thu)\n"
        "• Signal alerts checked every 5 minutes during active sessions\n\n"
        "⚠️ Disclaimer: This is not financial advice. Trade responsibly.\n"
        "Use /help anytime to see this message again."
    )
    safe_reply(message, text)


@bot.message_handler(commands=['outlook'])
def outlook_handler(message: Message) -> None:
    """Handle /outlook command"""
    if not is_market_open():
        reply = "Gold market is currently closed (weekend or holiday). No outlook available."
    else:
        try:
            outlook_text = generate_daily_outlook()
            reply = outlook_text or "Could not generate outlook right now."
        except Exception as e:
            print(f"Outlook error: {e}")
            reply = "Error generating outlook. Please try again later."

    safe_reply(message, reply)


@bot.message_handler(commands=['signal'])
def signal_handler(message: Message) -> None:
    """Handle /signal command"""
    if not is_market_open():
        reply = "Market is closed. No signals available."
    else:
        try:
            signal_text = generate_signal()
            if not signal_text or "No clear signal" in signal_text or "Market closed" in signal_text:
                reply = "No high-probability signal detected right now.\nTry again later or check /outlook first."
            else:
                reply = f"🔔 Current Signal:\n\n{signal_text}"
        except Exception as e:
            print(f"Signal error: {e}")
            reply = "Error checking signals. Please try again."

    safe_reply(message, reply)


@bot.message_handler(commands=['news'])
def news_handler(message: Message) -> None:
    """Handle /news command"""
    try:
        news_content = fetch_news()
        if not news_content or "error" in news_content.lower():
            reply = "Could not fetch news at the moment. Try again later."
        else:
            reply = f"📰 Recent Gold News:\n\n{news_content}"
    except Exception as e:
        print(f"News fetch error: {e}")
        reply = "Error loading news. Please try again."

    safe_reply(message, reply)


@bot.message_handler(commands=['price'])
def price_handler(message: Message) -> None:
    """Handle /price command"""
    try:
        price_text = get_live_gold_price()
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        reply = f"💰 Current XAUUSD Price\n\n{price_text}\n\n(Updated: {timestamp})"
    except Exception as e:
        print(f"Price fetch error: {e}")
        reply = "Could not fetch live price right now. Try again later."

    safe_reply(message, reply)
