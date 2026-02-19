import time
import os
import MetaTrader5 as mt5
import analysis
import command

def init_mt5():
    """Initialize MT5 with credentials from environment variables"""
    login = int(os.environ.get("MT5_LOGIN", 0))
    password = os.environ.get("MT5_PASSWORD", "")
    server = os.environ.get("MT5_SERVER", "")

    if not mt5.initialize(login=login, password=password, server=server):
        print("MT5 initialization failed")
        mt5.shutdown()
        exit()
    else:
        print(f"MT5 initialized successfully on server {server}")

def run_bot():
    # Initialize Telegram bot
    command.init_telegram()
    
    # Initialize MT5 connection
    init_mt5()

    # Send daily news summary
    command.send_daily_news()

    print("Bot is running...")

    # Real-time polling loop for trade alerts
    while True:
        trade = analysis.check_trade()
        if trade:
            command.send_alert(trade)
        time.sleep(1)  # Poll every 1 second for 1-min chart entries

if _name_ == "_main_":
    run_bot()
