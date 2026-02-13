import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time

exchange = ccxt.binance({'enableRateLimit': True})
symbol = 'XAUUSD'

HOLIDAYS_2026 = [
    '2026-01-01', '2026-04-03', '2026-04-06', '2026-05-04', '2026-05-25',
    '2026-06-19', '2026-07-03', '2026-08-31', '2026-12-24', '2026-12-25',
    '2026-12-28', '2026-12-31'
]

HIGH_IMPACT_HOURS_UTC = [12, 13, 18]

def is_market_open():
    now = datetime.utcnow()
    if now.weekday() >= 5 or now.strftime('%Y-%m-%d') in HOLIDAYS_2026:
        return False
    return True

def fetch_news():
    try:
        time.sleep(1)  # polite delay
        url = 'https://www.investing.com/commodities/gold-news'
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all('article', class_='js-article-item', limit=3)
        return '\n'.join([f"- {a.find('a', class_='title').text.strip()}: {a.find('p').text.strip()}" for a in articles]) or "No news found."
    except Exception as e:
        return f"News fetch error: {str(e)}"

def fetch_ohlcv(timeframe, limit=200):
    time.sleep(1)  # avoid rate limits
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    return df

def generate_daily_outlook():
    if not is_market_open():
        return "Gold market is closed today (holiday or weekend). No analysis available."

    try:
        now = datetime.utcnow()
        df_h4 = fetch_ohlcv('4h')
        df_h1 = fetch_ohlcv('1h')
        df_daily = fetch_ohlcv('1d', 2)
        asian_start = now - timedelta(days=1, hours=now.hour - 18 if now.hour > 18 else now.hour + 6)
        df_asian = df_h1[df_h1['timestamp'] > asian_start]
        df_m15 = fetch_ohlcv('15m')
        df_m5 = fetch_ohlcv('5m')

        # Simple HTF
        adx = df_h4.ta.adx(append=True)['ADX_14'].iloc[-1] if 'ADX_14' in df_h4.columns else 20
        condition = "Trending" if adx > 25 else "Ranging"
        structure = "HH/HL" if df_h4['close'].iloc[-1] > df_h4['close'].iloc[-2] else "LH/LL"
        supply = df_h4['high'].max()
        demand = df_h4['low'].min()

        y_high = df_daily['high'].iloc[-1]
        y_low = df_daily['low'].iloc[-1]

        news = fetch_news()

        return f"""
DAILY MARKET OUTLOOK – XAUUSD
📅 Date: {now.strftime('%Y-%m-%d')}

Higher Timeframe: {condition} - {structure}
Supply at: {supply:.2f}
Demand at: {demand:.2f}

Yesterday High/Low: {y_high:.2f} / {y_low:.2f}

News:
{news}

Direction today: Look for {'bullish' if 'HH' in structure else 'bearish'} moves.
        """.strip()
    except Exception as e:
        return f"Outlook error: {str(e)}"

def generate_signal():
    if not is_market_open():
        return "Market closed. No signal."

    try:
        df_5m = fetch_ohlcv('5m', 80)
        df_1m = fetch_ohlcv('1m', 40)

        df_5m.ta.sma(length=9, append=True)
        df_5m.ta.sma(length=21, append=True)

        if df_5m['SMA_9'].iloc[-1] > df_5m['SMA_21'].iloc[-1] and df_5m['SMA_9'].iloc[-2] <= df_5m['SMA_21'].iloc[-2]:
            direction = "BUY"
            entry = df_1m['close'].iloc[-1]
            atr = df_1m.ta.atr(length=14).iloc[-1] if 'ATRr_14' in df_1m.columns else 5.0
            sl = entry - atr * 1.5
            tp1 = entry + atr * 2
            tp2 = entry + atr * 4
        elif df_5m['SMA_9'].iloc[-1] < df_5m['SMA_21'].iloc[-1] and df_5m['SMA_9'].iloc[-2] >= df_5m['SMA_21'].iloc[-2]:
            direction = "SELL"
            entry = df_1m['close'].iloc[-1]
            atr = df_1m.ta.atr(length=14).iloc[-1] if 'ATRr_14' in df_1m.columns else 5.0
            sl = entry + atr * 1.5
            tp1 = entry - atr * 2
            tp2 = entry - atr * 4
        else:
            return "No signal right now."

        return f"""
{direction} Signal on XAUUSD
Entry: {entry:.2f}
SL: {sl:.2f}
TP1: {tp1:.2f}
TP2: {tp2:.2f}
        """.strip()
    except Exception as e:
        return f"Signal error: {str(e)}"
