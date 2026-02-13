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

HIGH_IMPACT_HOURS_UTC = [12, 13, 18]  # Example high-impact times

def is_market_open():
    now = datetime.utcnow()
    if now.weekday() >= 5 or now.strftime('%Y-%m-%d') in HOLIDAYS_2026:
        return False
    return True

def fetch_news():
    try:
        time.sleep(1)  # polite delay
        url = 'https://www.investing.com/commodities/gold-news'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all('article', class_='js-article-item', limit=3)
        if not articles:
            return "No recent news articles found."
        return '\n'.join([f"- {a.find('a', class_='title').text.strip()}: {a.find('p').text.strip()}" for a in articles])
    except Exception as e:
        return f"News fetch error: {str(e)}"

def fetch_ohlcv(timeframe, limit=200):
    time.sleep(1.5)  # avoid rate limits on Binance public API
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        return df
    except Exception as e:
        print(f"CCXT fetch error ({timeframe}): {str(e)}")
        return pd.DataFrame()

def generate_daily_outlook():
    if not is_market_open():
        return "Gold market is closed today (holiday or weekend). No analysis available."

    try:
        now = datetime.utcnow()
        df_h4 = fetch_ohlcv('4h')
        df_h1 = fetch_ohlcv('1h')
        df_daily = fetch_ohlcv('1d', 3)  # last 3 days for better context
        asian_start = now - timedelta(days=1, hours=now.hour - 18 if now.hour > 18 else now.hour + 6)
        df_asian = df_h1[df_h1['timestamp'] > asian_start]
        df_m15 = fetch_ohlcv('15m')
        df_m5 = fetch_ohlcv('5m')

        # HTF analysis
        adx = df_h4.ta.adx(append=True)['ADX_14'].iloc[-1] if 'ADX_14' in df_h4.columns else 20
        condition = "Trending" if adx > 25 else "Ranging" if adx < 20 else "Volatile/Post-news"
        structure = "HH/HL (bullish)" if df_h4['close'].iloc[-1] > df_h4['close'].iloc[-2] else "LH/LL (bearish)"
        supply = df_h4['high'].max()
        demand = df_h4['low'].min()

        y_high = df_daily['high'].iloc[-1]
        y_low = df_daily['low'].iloc[-1]

        news = fetch_news()

        return f"""
DAILY MARKET OUTLOOK – XAUUSD
📅 Date: {now.strftime('%Y-%m-%d')}

Higher Timeframe (H4/H1): {condition} - {structure}
Supply zone: {supply:.2f}
Demand zone: {demand:.2f}

Yesterday High/Low: {y_high:.2f} / {y_low:.2f}

Recent News:
{news}

Direction today: Look for {'bullish breaks above supply' if 'HH' in structure else 'bearish breaks below demand'}.
        """.strip()
    except Exception as e:
        return f"Outlook generation error: {str(e)}"

def generate_signal():
    if not is_market_open():
        return "Market closed. No signal available."

    try:
        df_5m = fetch_ohlcv('5m', 100)
        df_1m = fetch_ohlcv('1m', 50)

        if df_5m.empty or df_1m.empty:
            return "Data fetch failed. Try again later."

        df_5m.ta.sma(length=9, append=True)
        df_5m.ta.sma(length=21, append=True)

        last_5m = df_5m.iloc[-1]
        prev_5m = df_5m.iloc[-2]

        if last_5m['SMA_9'] > last_5m['SMA_21'] and prev_5m['SMA_9'] <= prev_5m['SMA_21']:
            direction = "BUY"
            entry = df_1m['close'].iloc[-1]
            atr = df_1m.ta.atr(length=14).iloc[-1] if 'ATRr_14' in df_1m.columns else 5.0
            sl = entry - atr * 1.5
            tp1 = entry + atr * 2
            tp2 = entry + atr * 4
        elif last_5m['SMA_9'] < last_5m['SMA_21'] and prev_5m['SMA_9'] >= prev_5m['SMA_21']:
            direction = "SELL"
            entry = df_1m['close'].iloc[-1]
            atr = df_1m.ta.atr(length=14).iloc[-1] if 'ATRr_14' in df_1m.columns else 5.0
            sl = entry + atr * 1.5
            tp1 = entry - atr * 2
            tp2 = entry - atr * 4
        else:
            return "No clear signal right now (SMA crossover not triggered)."

        return f"""
{direction} Signal on XAUUSD (5m SMA crossover)
Entry: {entry:.2f}
SL: {sl:.2f}
TP1: {tp1:.2f}
TP2: {tp2:.2f}

Note: Use with caution - this is basic SMA logic.
        """.strip()
    except Exception as e:
        return f"Signal generation error: {str(e)}"
