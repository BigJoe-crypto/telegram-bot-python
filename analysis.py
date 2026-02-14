import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup
import time
import logging
from scipy.signal import argrelextrema

# Setup logging (visible in Railway logs)
logger = logging.getLogger(__name__)

exchange = ccxt.binance({'enableRateLimit': True})
symbol = 'XAUUSD'

HOLIDAYS_2026 = [
    '2026-01-01', '2026-04-03', '2026-04-06', '2026-05-04', '2026-05-25',
    '2026-06-19', '2026-07-03', '2026-08-31', '2026-12-24', '2026-12-25',
    '2026-12-28', '2026-12-31'
]

HIGH_IMPACT_HOURS_UTC = [12, 13, 18]  # Example high-impact news hours

def is_market_open():
    now = datetime.utcnow()
    if now.weekday() >= 5 or now.strftime('%Y-%m-%d') in HOLIDAYS_2026:
        return False
    return True

def fetch_news():
    news_text = "Daily Gold News:\n\n"
    try:
        url = 'https://www.investing.com/commodities/gold-news'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all('article', class_='js-article-item', limit=3)
        news_text += "From Investing.com:\n"
        for a in articles:
            title_tag = a.find('a', class_='title')
            if title_tag:
                news_text += f"- {title_tag.text.strip()}\n"
    except Exception as e:
        logger.warning(f"Investing.com news failed: {e}")
        news_text += "Investing.com unavailable\n"

    try:
        rss_url = 'https://news.google.com/rss/search?q=gold+price+news+when:1d&hl=en-US&gl=US&ceid=US:en'
        feed = feedparser.parse(rss_url)
        if feed.entries:
            news_text += "\nFrom Google News:\n"
            for entry in feed.entries[:3]:
                news_text += f"- {entry.title}\n"
        else:
            news_text += "\nNo recent Google News\n"
    except Exception as e:
        logger.warning(f"Google News failed: {e}")
        news_text += "Google News unavailable\n"

    return news_text.strip() or "No recent gold news found today."

def fetch_ohlcv(timeframe, limit=200):
    time.sleep(1.8)  # Slightly longer delay to avoid Binance rate limits
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        return df
    except Exception as e:
        logger.error(f"CCXT fetch error ({timeframe}): {str(e)}")
        return pd.DataFrame()

def find_swing_highs_lows(df, order=5):
    high_idx = argrelextrema(df['high'].values, np.greater_equal, order=order)[0]
    low_idx = argrelextrema(df['low'].values, np.less_equal, order=order)[0]
    
    swings = []
    for idx in high_idx:
        swings.append(('H', df['timestamp'].iloc[idx], df['high'].iloc[idx]))
    for idx in low_idx:
        swings.append(('L', df['timestamp'].iloc[idx], df['low'].iloc[idx]))
    
    swings.sort(key=lambda x: x[1])
    return swings

def generate_daily_outlook():
    if not is_market_open():
        return "Gold market is closed today (holiday or weekend). No analysis available."
    try:
        now = datetime.utcnow()
        df_h4 = fetch_ohlcv('4h', 100)
        df_h1 = fetch_ohlcv('1h', 200)
        df_daily = fetch_ohlcv('1d', 5)  # more context
        asian_start = now - timedelta(days=1, hours=now.hour - 18 if now.hour > 18 else now.hour + 6)
        df_asian = df_h1[df_h1['timestamp'] > asian_start]
        # HTF analysis
        adx_series = df_h4.ta.adx(append=False)
        adx = adx_series['ADX_14'].iloc[-1] if not adx_series.empty else 20
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
        logger.error(f"Outlook error: {str(e)}")
        return f"Outlook generation error: {str(e)}"

def get_live_gold_price():
    """
    Try to fetch live price. If all APIs fail, return useful chart websites.
    """
    try:
        # 1. BullionVault – very reliable free API
        url = "https://www.bullionvault.com/gold-price.json"
        r = requests.get(url, timeout=8)
        data = r.json()
        price = data.get('spotPrice')
        if price:
            return f"Live XAUUSD Price: **${price:,.2f}** (BullionVault)\nUpdated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    except Exception as e:
        pass

    try:
        # 2. Metals-API (free tier sometimes works)
        url = "https://metals-api.com/api/latest?access_key=free&base=XAU&symbols=USD"
        r = requests.get(url, timeout=8)
        data = r.json()
        if 'rates' in data and 'USD' in data['rates']:
            price = 1 / data['rates']['USD']
            return f"Live XAUUSD Price: **${price:,.2f}** (Metals-API)\nUpdated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    except Exception:
        pass

    # Final fallback: websites with live charts
    websites = [
        {"name": "TradingView — XAUUSD", "url": "https://www.tradingview.com/chart/?symbol=XAUUSD", "desc": "Best interactive live chart + indicators"},
        {"name": "Investing.com Gold Chart", "url": "https://www.investing.com/commodities/gold-chart", "desc": "Real-time chart + news + analysis"},
        {"name": "Kitco Live Gold", "url": "https://www.kitco.com/charts/livegold.html", "desc": "Clean, reliable live gold price chart"},
        {"name": "BullionVault Gold Price", "url": "https://www.bullionvault.com/gold-price-chart.do", "desc": "Accurate spot price and chart"},
        {"name": "FXStreet Gold Rates", "url": "https://www.fxstreet.com/rates-charts/gold", "desc": "Live chart + economic calendar"}
    ]

    msg = "⚠️ Live price APIs are temporarily unavailable.\n\n"
    msg += "Here are the best free websites with **live XAUUSD charts**:\n\n"
    for site in websites:
        msg += f"📊 **{site['name']}**\n{site['desc']}\n👉 {site['url']}\n\n"
    msg += f"(Checked: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})"

    return msg

# The rest of your signal generation code remains unchanged...
# (generate_signal, find_swing_highs_lows, etc.)
