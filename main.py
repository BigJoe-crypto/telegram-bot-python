import time
import analysis
import command

def run_bot():
    # Initialize Telegram bot
    command.init_telegram()
    
    # Initialize MT5 connection
    analysis.init_mt5()

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
