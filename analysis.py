import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import feedparser  # For RSS feeds
import requests
from bs4 import BeautifulSoup
import time
from scipy.signal import argrelextrema

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
    news_text = "Daily Gold News:\n\n"
    # 1. From Investing.com (your current source)
    try:
        url = 'https://www.investing.com/commodities/gold-news'
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all('article', class_='js-article-item', limit=2)
        news_text += "From Investing.com:\n"
        for a in articles:
            title = a.find('a', class_='title').text.strip()
            news_text += f"- {title}\n"
    except:
        news_text += "Investing.com error\n"
    # 2. From Google News (using RSS feed for "gold price news")
    try:
        rss_url = 'https://news.google.com/rss/search?q=gold+price+news+when:1d&hl=en-US&gl=US&ceid=US:en'
        feed = feedparser.parse(rss_url)
        news_text += "\nFrom Google News:\n"
        for entry in feed.entries[:2]:
            news_text += f"- {entry.title}\n"
    except:
        news_text += "Google News error (add feedparser to dependencies)\n"
    return news_text or "No news found today."

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

def find_swing_highs_lows(df, order=5):
    # Use argrelextrema to find local maxima and minima
    high_idx = argrelextrema(df['high'].values, np.greater_equal, order=order)[0]
    low_idx = argrelextrema(df['low'].values, np.less_equal, order=order)[0]
    
    swings = []
    for idx in high_idx:
        swings.append(('H', df['timestamp'].iloc[idx], df['high'].iloc[idx]))
    for idx in low_idx:
        swings.append(('L', df['timestamp'].iloc[idx], df['low'].iloc[idx]))
    
    swings.sort(key=lambda x: x[1])  # Sort by timestamp
    return swings

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

def get_live_gold_price():
    try:
        # Try GoldAPI directly (more reliable for XAU/USD)
        url = "https://www.goldapi.io/api/XAU/USD"
        r = requests.get(url, timeout=10)
        data = r.json()
        price = data.get('price')
        if price:
            return f"Live XAUUSD Price (GoldAPI): ${price:.2f}"
    except Exception as e:
        pass
   
    # Fallback to another source
    try:
        url = "https://api.metals.live/v1/spot/gold"
        r = requests.get(url, timeout=10)
        data = r.json()
        price = data.get('gold')
        if price:
            return f"Live XAUUSD Price (Metals.live): ${price:.2f}"
    except Exception as fallback_error:
        return f"Price fetch error: {str(e)} | Fallback error: {str(fallback_error)}"

def generate_signal():
    if not is_market_open():
        return "Market closed. No signal available."
    
    try:
        # Fetch data for different analyzers
        df_1h = fetch_ohlcv('1h', 200)
        df_5m = fetch_ohlcv('5m', 200)
        df_1m = fetch_ohlcv('1m', 100)
        
        if df_1h.empty or df_5m.empty or df_1m.empty:
            return "Data fetch failed. Try again later."
        
        # 1H Analyzer: Determine Daily Bias using structure
        swings_1h = find_swing_highs_lows(df_1h, order=5)
        highs_1h = [s for s in swings_1h if s[0] == 'H'][-4:]  # Last 4 highs
        lows_1h = [s for s in swings_1h if s[0] == 'L'][-4:]  # Last 4 lows
        
        if len(highs_1h) < 2 or len(lows_1h) < 2:
            return "Insufficient data for structure analysis on 1H."
        
        bias = "Range"
        structure_desc = "Equal highs/lows (range)"
        choch = False
        
        if highs_1h[-1][2] > highs_1h[-2][2] and lows_1h[-1][2] > lows_1h[-2][2]:
            bias = "Bullish"
            structure_desc = "Higher Highs / Higher Lows (bullish)"
        elif highs_1h[-1][2] < highs_1h[-2][2] and lows_1h[-1][2] < lows_1h[-2][2]:
            bias = "Bearish"
            structure_desc = "Lower Highs / Lower Lows (bearish)"
        
        if bias == "Range":
            return "Market in range, no clear trend. No signal."
        
        # Check for CHoCH
        if bias == "Bullish" and lows_1h[-1][2] < lows_1h[-2][2]:
            choch = True
        elif bias == "Bearish" and highs_1h[-1][2] > highs_1h[-2][2]:
            choch = True
        
        if choch:
            return f"CHoCH detected in {bias.lower()} trend. Possible reversal. No signal."
        
        # Check key levels from 1H (support/resistance)
        resistance = highs_1h[-1][2]
        support = lows_1h[-1][2]
        
        # News AI: Filter volatility risk
        now = datetime.utcnow()
        if now.hour in HIGH_IMPACT_HOURS_UTC:
            return "High impact news period. Avoid trading."
        
        # 5M Analyzer: Confirm Setup (momentum, impulse vs correction, BOS confirmation)
        df_5m.ta.adx(append=True)
        adx_5m = df_5m['ADX_14'].iloc[-1]
        if adx_5m < 25:
            return "Low momentum on 5M. No strong impulse. No signal."
        
        # Use SMA crossover for setup confirmation, but only in bias direction
        df_5m.ta.sma(length=9, append=True)
        df_5m.ta.sma(length=21, append=True)
        last_5m = df_5m.iloc[-1]
        prev_5m = df_5m.iloc[-2]
        
        direction = None
        pattern = "No pattern"
        
        if bias == "Bullish" and last_5m['SMA_9'] > last_5m['SMA_21'] and prev_5m['SMA_9'] <= prev_5m['SMA_21']:
            # Check for BOS: if close breaks previous high
            prev_high_5m = df_5m['high'].iloc[-2]
            if last_5m['close'] > prev_high_5m:
                direction = "BUY"
                pattern = "Bullish BOS after SMA crossover"
            else:
                return "Bullish setup but no confirmed BOS (wick only?). No signal."
        elif bias == "Bearish" and last_5m['SMA_9'] < last_5m['SMA_21'] and prev_5m['SMA_9'] >= prev_5m['SMA_21']:
            # Check for BOS: if close breaks previous low
            prev_low_5m = df_5m['low'].iloc[-2]
            if last_5m['close'] < prev_low_5m:
                direction = "SELL"
                pattern = "Bearish BOS after SMA crossover"
            else:
                return "Bearish setup but no confirmed BOS (wick only?). No signal."
        
        if direction is None:
            return "No confirmed setup on 5M in the direction of bias."
        
        # Check liquidity hunt: Look for equal highs/lows on 5M (simple check)
        recent_highs = df_5m['high'].iloc[-10:]
        if len(np.unique(recent_highs[recent_highs > last_5m['close']])) < 3 and direction == "BUY":
            return "Potential liquidity hunt at equal highs. Avoid buy."
        recent_lows = df_5m['low'].iloc[-10:]
        if len(np.unique(recent_lows[recent_lows < last_5m['close']])) < 3 and direction == "SELL":
            return "Potential liquidity hunt at equal lows. Avoid sell."
        
        # 1M Analyzer: Precision Entry
        entry = df_1m['close'].iloc[-1]
        df_1m.ta.atr(length=14, append=True)
        atr = df_1m['ATRr_14'].iloc[-1] if 'ATRr_14' in df_1m.columns else 5.0
        
        # ML Model: Simple rule-based "ML" decision (score conditions)
        score = 0
        if adx_5m > 30: score += 1  # Strong trend
        if not choch: score += 1
        if abs(entry - resistance if direction == "SELL" else entry - support) < atr * 3: score += 1  # Near key level
        if bias != "Range": score += 1
        if score < 3:
            return f"ML decision score too low ({score}/4). No signal."
        
        # Set SL and TP based on structure and ATR
        swings_5m = find_swing_highs_lows(df_5m, order=3)
        highs_5m = [s for s in swings_5m if s[0] == 'H'][-2:]
        lows_5m = [s for s in swings_5m if s[0] == 'L'][-2:]
        
        if direction == "BUY":
            sl = lows_5m[-1][2] - atr * 0.5 if len(lows_5m) > 0 else entry - atr * 1.5
            tp1 = entry + atr * 2
            tp2 = entry + atr * 4
        else:  # SELL
            sl = highs_5m[-1][2] + atr * 0.5 if len(highs_5m) > 0 else entry + atr * 1.5
            tp1 = entry - atr * 2
            tp2 = entry - atr * 4
        
        # Final signal format
        return f"""
XAUUSD {direction} SETUP 🔔
* Structure: {structure_desc}
* Pattern: {pattern}
* Entry: {entry:.2f}
* SL: {sl:.2f}
* TP1: {tp1:.2f}
* TP2: {tp2:.2f}
        """.strip()
    
    except Exception as e:
        return f"Signal generation error: {str(e)}"
