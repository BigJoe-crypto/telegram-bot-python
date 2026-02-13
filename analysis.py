# analysis.py (combined: daily outlook + new pipeline for signals)

import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import pytz
import requests
from bs4 import BeautifulSoup
import xgboost as xgb
import joblib
import os

exchange = ccxt.binance({'enableRateLimit': True})
symbol = 'XAUUSD'

HOLIDAYS_2026 = [  
    '2026-01-01', '2026-04-03', '2026-04-06', '2026-05-04', '2026-05-25',
    '2026-06-19', '2026-07-03', '2026-08-31', '2026-12-24', '2026-12-25',
    '2026-12-28', '2026-12-31'
]

MODEL_PATH = 'xgboost_gold_confirm.pkl'  
if os.path.exists(MODEL_PATH):
    ml_model = joblib.load(MODEL_PATH)
else:
    ml_model = None

HIGH_IMPACT_HOURS_UTC = [12, 13, 18]

def is_market_open():
    now = datetime.utcnow()
    if now.weekday() >= 5:
        return False
    if now.strftime('%Y-%m-%d') in HOLIDAYS_2026:
        return False
    return True

def fetch_news():
    try:
        url = 'https://www.investing.com/commodities/gold-news'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('article', class_='js-article-item', limit=3)
        news_str = ''
        for art in articles:
            title = art.find('a', class_='title').text.strip()
            summary = art.find('p').text.strip()
            news_str += f"- {title}: {summary}\n"
        return news_str or "No recent news found."
    except Exception as e:
        return f"Error fetching news: {str(e)}"

def fetch_ohlcv(timeframe, limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    return df

def analyze_htf_context(df_h4, df_h1):
    df_h4.ta.adx(append=True)
    adx = df_h4['ADX_14'].iloc[-1]
    condition = "Trending" if adx > 25 else "Ranging" if adx < 20 else "Post-news / Volatile"

    highs = "HH" if df_h4['high'].iloc[-1] > df_h4['high'].iloc[-2] else "LH"
    lows = "HL" if df_h4['low'].iloc[-1] > df_h4['low'].iloc[-2] else "LL"
    structure = f"Highs: {highs} Lows: {lows}"

    supply = df_h4['high'].max()
    demand = df_h4['low'].min()

    conclusion = f"Market is currently {condition.lower()}, so I will be {'directional' if 'Trending' in condition else 'reactive'}."

    return condition, structure, supply, demand, conclusion

def analyze_yesterday_story(df_daily, df_asian):
    y_high = df_daily['high'].iloc[-1]
    y_low = df_daily['low'].iloc[-1]
    a_high = df_asian['high'].max()
    a_low = df_asian['low'].min()

    df_daily['body'] = abs(df_daily['close'] - df_daily['open'])
    df_daily['range'] = df_daily['high'] - df_daily['low']
    event = "Strong impulse" if df_daily['range'].iloc[-1] > df_daily['range'].mean() * 1.5 else "Sideways"

    clue = f"Because price {event.lower()}, today I expect continuation or patience."

    return y_high, y_low, a_high, a_low, event, clue

def analyze_intraday_keys(df_m15, df_m5):
    df_m15.ta.pivot(append=True)  

    levels = [df_m15['high'].iloc[-1], df_m15['low'].iloc[-1]]  

    return levels

def generate_daily_outlook():
    if not is_market_open():
        return "Gold market is closed today (holiday/weekend). No analysis available."

    df_h4 = fetch_ohlcv('4h')
    df_h1 = fetch_ohlcv('1h')
    df_daily = fetch_ohlcv('1d', 2)  
    now = datetime.utcnow()
    asian_start = now - timedelta(days=1, hours=now.hour - 18 if now.hour > 18 else now.hour + 6)
    df_asian = df_h1[df_h1['timestamp'] > asian_start]  
    df_m15 = fetch_ohlcv('15m')
    df_m5 = fetch_ohlcv('5m')

    condition, structure, supply, demand, conclusion = analyze_htf_context(df_h4, df_h1)
    y_high, y_low, a_high, a_low, event, clue = analyze_yesterday_story(df_daily, df_asian)
    levels = analyze_intraday_keys(df_m15, df_m5)

    news = fetch_news()

    outlook = f"""
DAILY MARKET OUTLOOK – XAUUSD
📅 Date: {now.strftime('%Y-%m-%d')}
📊 Session Focus: ☐ London ☐ New York

1️⃣ Higher Timeframe Context (H4 / H1)
Market condition: {condition}
Overall structure: {structure}
Nearest HTF zones:
Supply at: {supply}
Demand at: {demand}
HTF Conclusion: “{conclusion}”

2️⃣ Yesterday’s Story
Yesterday High: {y_high}
Yesterday Low: {y_low}
Asian High / Low: {a_high} / {a_low}
What happened yesterday? {event}
Yesterday’s Clue: “{clue}”

3️⃣ Intraday Key Areas (M15 / M5)
Key levels to watch today:
Level 1: {levels[0]}
Level 2: {levels[1]}

News Concerning Gold:
{news}

Direction for today: Look out for { 'bullish breaks above supply' if 'HH' in structure else 'bearish below demand' }.
"""
    return outlook

def is_high_volatility_risk():
    now_utc = datetime.utcnow()
    if now_utc.hour in HIGH_IMPACT_HOURS_UTC:
        return True
    df = fetch_ohlcv('5m', 20)
    df.ta.atr(length=14, append=True)
    if df['ATRr_14'].iloc[-1] > df['close'].mean() * 0.008:
        return True
    return False

def analyze_1h_bias():
    df = fetch_ohlcv('1h', 100)
    df.ta.sma(length=50, append=True)
    df.ta.sma(length=200, append=True)
    df.ta.adx(append=True)

    adx = df['ADX_14'].iloc[-1]
    bias = "Trending" if adx > 25 else "Ranging" if adx < 20 else "Volatile / Post-news"

    direction = "Bullish" if df['SMA_50'].iloc[-1] > df['SMA_200'].iloc[-1] else "Bearish"

    recent_high = df['high'].rolling(20).max().iloc[-1]
    recent_low = df['low'].rolling(20).min().iloc[-1]
    current = df['close'].iloc[-1]
    structure = "Breakout Bullish (HH)" if current > recent_high else "Breakdown Bearish (LL)" if current < recent_low else "Inside Range"

    return {
        'bias': bias,
        'direction': direction,
        'structure': structure,
        'htf_score': 1 if direction == "Bullish" else -1 if direction == "Bearish" else 0
    }

def analyze_5m_setup(bias_info):
    df = fetch_ohlcv('5m', 80)
    df.ta.fvg(append=True)  # Assume available; custom impl if not: FVG if high[t-2] < low[t-1]
    df.ta.obv(append=True)

    swing_high = df['high'].rolling(10).max().shift(1).iloc[-1]
    swing_low = df['low'].rolling(10).min().shift(1).iloc[-1]

    current = df['close'].iloc[-1]
    setup_score = 0

    if bias_info['direction'] == "Bullish":
        if current > swing_high and (df['FVG'].iloc[-1] != 0 if 'FVG' in df.columns else (df['low'].iloc[-1] > df['high'].iloc[-2])):
            setup_score += 1
        if df['OBV'].iloc[-1] > df['OBV'].iloc[-5]:
            setup_score += 1
    elif bias_info['direction'] == "Bearish":
        if current < swing_low and (df['FVG'].iloc[-1] != 0 if 'FVG' in df.columns else (df['high'].iloc[-1] < df['low'].iloc[-2])):
            setup_score -= 1
        if df['OBV'].iloc[-1] < df['OBV'].iloc[-5]:
            setup_score -= 1

    return setup_score

def analyze_1m_entry(setup_score):
    df = fetch_ohlcv('1m', 40)
    df.ta.cdl_pattern(name="engulfing", append=True)
    df.ta.rsi(length=14, append=True)

    entry_score = 0
    if setup_score > 0 and df['CDL_ENGULFING'].iloc[-1] > 0 and df['RSI_14'].iloc[-1] < 70:
        entry_score = 1
    elif setup_score < 0 and df['CDL_ENGULFING'].iloc[-1] < 0 and df['RSI_14'].iloc[-1] > 30:
        entry_score = -1

    return entry_score

def ml_confirmation(features):
    if ml_model is None:
        return 0
    # Assume model predicts [hold, buy, sell] probs
    prob = ml_model.predict_proba([list(features.values())])[0]
    return 1 if prob[1] > 0.65 else -1 if prob[2] > 0.65 else 0

def generate_signal():
    if not is_market_open():
        return "Market closed. No signal."

    if is_high_volatility_risk():
        return "High volatility risk detected (news/event window). No signal issued."

    bias = analyze_1h_bias()
    setup = analyze_5m_setup(bias)
    entry = analyze_1m_entry(setup)

    total_score = bias['htf_score'] + (setup / 2 if setup else 0) + entry

    features = {
        'htf_score': bias['htf_score'],
        'setup_score': setup,
        'entry_score': entry,
        'rsi_5m': fetch_ohlcv('5m', 20).ta.rsi(length=14).iloc[-1],
        # Expand as needed
    }
    ml_vote = ml_confirmation(features)

    final_score = total_score + ml_vote * 1.5

    if final_score >= 2.5:
        direction = "BUY"
        entry_price = fetch_ohlcv('1m', 1)['close'].iloc[-1]
        atr = fetch_ohlcv('1m', 20).ta.atr(length=14).iloc[-1]
        sl = entry_price - atr * 1.5
        tp1 = entry_price + atr * 2
        tp2 = entry_price + atr * 4
    elif final_score <= -2.5:
        direction = "SELL"
        entry_price = fetch_ohlcv('1m', 1)['close'].iloc[-1]
        atr = fetch_ohlcv('1m', 20).ta.atr(length=14).iloc[-1]
        sl = entry_price + atr * 1.5
        tp1 = entry_price - atr * 2
        tp2 = entry_price - atr * 4
    else:
        return None

    return f"""
{direction} Signal on XAUUSD
Entry: {entry_price:.2f}
SL: {sl:.2f}
TP1: {tp1:.2f}
TP2: {tp2:.2f}

1H Bias: {bias['direction']} ({bias['structure']})
5M Setup: {'Confirmed' if abs(setup) > 0 else 'Weak'}
1M Entry: {'Precision timing OK' if abs(entry) > 0 else 'No micro confirmation'}
News Risk: Low
ML Vote: {'Strong Buy' if ml_vote > 0 else 'Strong Sell' if ml_vote < 0 else 'Neutral'}
"""
