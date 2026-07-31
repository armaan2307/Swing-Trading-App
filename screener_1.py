#!/usr/bin/env python
# coding: utf-8

# In[1]:


import io
import urllib.request
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf

# ---------------------------------------------------------
# 1. TICKER FETCHING FUNCTIONS
# ---------------------------------------------------------
def get_nse_tickers(url, fallback_list):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            csv_data = response.read().decode('utf-8')
        df_nse = pd.read_csv(io.StringIO(csv_data))
        symbols = df_nse['Symbol'].dropna().tolist()
        return [f"{str(sym).strip()}.NS" for sym in symbols]
    except Exception:
        return fallback_list

def get_nifty50_tickers():
    return get_nse_tickers("https://archives.nseindia.com/content/indices/ind_nifty50list.csv", ["RELIANCE.NS", "TCS.NS"])

def get_midcap150_tickers():
    return get_nse_tickers("https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv", ["PERSISTENT.NS", "POLYCAB.NS"])

def get_smallcap250_tickers():
    return get_nse_tickers("https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv", ["SUZLON.NS", "CDSL.NS"])

# ---------------------------------------------------------
# 2. ADVANCED ANALYSIS ENGINE (SMA + RSI + Volume)
# ---------------------------------------------------------
def analyze_segment(tickers, category, target_pct, sl_pct):
    print(f"[{category}] Processing {len(tickers)} symbols...")
    data = yf.download(tickers, period="6mo", interval="1d", progress=False)
    trade_candidates = []

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = pd.DataFrame({'Close': data['Close'], 'Volume': data['Volume']}).dropna()
            else:
                df = pd.DataFrame({'Close': data['Close'][ticker], 'Volume': data['Volume'][ticker]}).dropna()

            if len(df) < 50:
                continue

            # Indicators
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['Vol_Avg20'] = df['Volume'].rolling(window=20).mean()

            # RSI Calculation
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # Latest Values
            price = float(df['Close'].iloc[-1])
            sma50 = float(df['SMA50'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])
            vol = float(df['Volume'].iloc[-1])
            vol_avg = float(df['Vol_Avg20'].iloc[-1])

            trend_strength = round(((price - sma50) / sma50) * 100, 2)

            # STRATEGY RULES:
            # 1. Price > 50 SMA (Uptrend)
            # 2. RSI between 55 and 70 (Strong momentum, not yet overbought)
            # 3. Volume > 1.2x Average 20-day volume (Institutional interest)
            if price > sma50 and (55 <= rsi <= 75) and (vol >= 1.1 * vol_avg):
                trade_candidates.append({
                    "Symbol": ticker.replace(".NS", ""),
                    "Category": category,
                    "Entry": round(price, 2),
                    "Target": round(price * target_pct, 2),
                    "StopLoss": round(price * sl_pct, 2),
                    "RSI": round(rsi, 1),
                    "TrendStrength_%": trend_strength,
                    "Status": "ACTIVE"
                })
        except Exception:
            continue

    df_res = pd.DataFrame(trade_candidates)
    if not df_res.empty and "TrendStrength_%" in df_res.columns:
        return df_res.sort_values(by="TrendStrength_%", ascending=False).head(10)
    return pd.DataFrame()

# ---------------------------------------------------------
# 3. RUNNER & DATABASE SAVER
# ---------------------------------------------------------
def run_and_save_to_sql():
    df_large = analyze_segment(get_nifty50_tickers(), "LargeCap", 1.06, 0.97)
    df_mid = analyze_segment(get_midcap150_tickers(), "MidCap", 1.08, 0.95)
    df_small = analyze_segment(get_smallcap250_tickers(), "SmallCap", 1.10, 0.94)

    all_dfs = [df for df in [df_large, df_mid, df_small] if not df.empty]
    if all_dfs:
        master_df = pd.concat(all_dfs, ignore_index=True)
        conn = sqlite3.connect("trades.db")
        master_df.to_sql("positional_trades", conn, if_exists="replace", index=False)
        conn.close()
        print("✅ Upgraded Engine finished and saved setups to trades.db!")

if __name__ == "__main__":
    run_and_save_to_sql()


# In[ ]:




