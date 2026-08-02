import io
import urllib.request
import sqlite3
import pandas as pd
import numpy as np
import yfinance as yf
import requests

# ---------------------------------------------------------
# TELEGRAM CREDENTIALS (REPLACE WITH YOUR OWN)
# ---------------------------------------------------------
TELEGRAM_BOT_TOKEN = "8859356411:AAGjyWzUI0kJlnmtON-iUNKRH0x8UKrpcMs" 
TELEGRAM_CHAT_ID = "6117972430"

def send_telegram_alert(df):
    """Sends top 5 setups to your Telegram channel."""
    if df.empty or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ℹ️ Telegram alert skipped (No token or empty data).")
        return

    message = "🚀 *NEW SWING TRADE SETUPS DETECTED* 🚀\n\n"
    for _, row in df.head(5).iterrows():
        emoji = "🟩" if row['1D_Change_%'] >= 0 else "🟥"
        message += (
            f"📌 *{row['Symbol']}* ({row['Category']})\n"
            f"• Entry: ₹{row['Entry']:.2f} | 1D: {emoji} {row['1D_Change_%']:+.2f}%\n"
            f"• Target: ₹{row['Target']:.2f} | SL: ₹{row['StopLoss']:.2f}\n"
            f"• RSI: {row['RSI']:.1f} | Trend: +{row['TrendStrength_%']:.2f}%\n\n"
        )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("📱 Telegram alert sent successfully!")
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")

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

def analyze_segment(tickers, category, target_pct, sl_pct):
    print(f"[{category}] Processing {len(tickers)} symbols...")
    
    # THREADS=FALSE PREVENTS THE DICTIONARY SIZE ITERATION BUG
    data = yf.download(tickers, period="6mo", interval="1d", progress=False, threads=False)
    trade_candidates = []

    for ticker in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if ticker in data['Close'].columns:
                    df = pd.DataFrame({'Close': data['Close'][ticker], 'Volume': data['Volume'][ticker]}).dropna()
                else:
                    continue
            else:
                df = pd.DataFrame({'Close': data['Close'], 'Volume': data['Volume']}).dropna()

            if len(df) < 50:
                continue

            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['Vol_Avg20'] = df['Volume'].rolling(window=20).mean()

            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            price = float(df['Close'].iloc[-1])
            prev_price = float(df['Close'].iloc[-2])
            day_change_pct = round(((price - prev_price) / prev_price) * 100, 2)

            sma50 = float(df['SMA50'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])
            vol = float(df['Volume'].iloc[-1])
            vol_avg = float(df['Vol_Avg20'].iloc[-1])

            trend_strength = round(((price - sma50) / sma50) * 100, 2)

            if price > sma50 and (55 <= rsi <= 75) and (vol >= 1.1 * vol_avg):
                trade_candidates.append({
                    "Symbol": ticker.replace(".NS", ""),
                    "Category": category,
                    "Entry": round(price, 2),
                    "Target": round(price * target_pct, 2),
                    "StopLoss": round(price * sl_pct, 2),
                    "RSI": round(rsi, 1),
                    "1D_Change_%": day_change_pct,
                    "TrendStrength_%": trend_strength,
                    "Status": "ACTIVE"
                })
        except Exception:
            continue

    df_res = pd.DataFrame(trade_candidates)
    if not df_res.empty and "TrendStrength_%" in df_res.columns:
        return df_res.sort_values(by="TrendStrength_%", ascending=False).head(10)
    return pd.DataFrame()

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
        print("✅ Pipeline executed successfully!")
        
        # Send Telegram notification
        send_telegram_alert(master_df)

if __name__ == "__main__":
    run_and_save_to_sql()
