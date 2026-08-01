import streamlit as st
import sqlite3
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Positional Swing Screener",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Positional Swing Trade Dashboard")
st.caption("Automated momentum setups with RSI & Volume spikes across Nifty 50, Midcap 150, and Smallcap 250.")

# Force clear cache for fresh reads from trades.db
st.cache_data.clear()

def load_trades():
    try:
        conn = sqlite3.connect("trades.db")
        df = pd.read_sql("SELECT * FROM positional_trades", conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

df_trades = load_trades()

if not df_trades.empty:
    # Sidebar Filter
    st.sidebar.header("Filter Options")
    category = st.sidebar.radio("Select Market Cap Category:", ["All", "LargeCap", "MidCap", "SmallCap"])

    display_df = df_trades if category == "All" else df_trades[df_trades["Category"] == category]

    # Metrics Row
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Opportunities", len(display_df))
    col2.metric("Market Segment", category)
    col3.metric("Status", "Live / SQL Synced")

    st.markdown("---")

    # Function to apply green/red styling based on 1D_Change_%
    def style_dataframe(df):
        def color_row(row):
            val = row.get("1D_Change_%", 0)
            if val > 0:
                return ['background-color: #d4edda; color: #155724; font-weight: bold'] * len(row)
            elif val < 0:
                return ['background-color: #f8d7da; color: #721c24; font-weight: bold'] * len(row)
            return [''] * len(row)

        return df.style.apply(color_row, axis=1).format({
            "Entry": "₹{:.2f}",
            "Target": "₹{:.2f}",
            "StopLoss": "₹{:.2f}",
            "RSI": "{:.1f}",
            "1D_Change_%": "{:+.2f}%",
            "TrendStrength_%": "{:.2f}%"
        })

    # Render styled table
    st.subheader("📋 Active Screener Opportunities")
    st.dataframe(
        style_dataframe(display_df),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # INTERACTIVE TECHNICAL CHART SECTION
    # ---------------------------------------------------------
    st.subheader("📊 Deep-Dive Technical Chart Analysis")
    
    # Fetch historical price data from Yahoo Finance
        ticker_symbol = f"{selected_stock}.NS"
        
        try:
            # Use Ticker.history for reliable single-stock downloads
            stock_obj = yf.Ticker(ticker_symbol)
            df_chart = stock_obj.history(period="6m", interval="1d")

            # Fallback to yf.download if history returns empty
            if df_chart.empty:
                df_chart = yf.download(ticker_symbol, period="6m", interval="1d", progress=False)

            # Flatten MultiIndex columns if present
            if isinstance(df_chart.columns, pd.MultiIndex):
                df_chart.columns = df_chart.columns.get_level_values(0)

            if not df_chart.empty and len(df_chart) > 14:
                df_chart['SMA50'] = df_chart['Close'].rolling(window=50).mean()

                # Calculate RSI
                delta = df_chart['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df_chart['RSI'] = 100 - (100 / (1 + rs))

                # Create Subplots
                fig = make_subplots(
                    rows=3, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.04,
                    subplot_titles=(f"{selected_stock} - Daily Price Action & Key Levels", "Volume Profile", "RSI (14) Indicator"),
                    row_width=[0.2, 0.2, 0.6]
                )

                # Panel 1: Candlesticks
                fig.add_trace(go.Candlestick(
                    x=df_chart.index,
                    open=df_chart['Open'],
                    high=df_chart['High'],
                    low=df_chart['Low'],
                    close=df_chart['Close'],
                    name="Price"
                ), row=1, col=1)

                # Panel 1: 50 SMA
                fig.add_trace(go.Scatter(
                    x=df_chart.index,
                    y=df_chart['SMA50'],
                    mode='lines',
                    name='50 SMA',
                    line=dict(color='orange', width=2)
                ), row=1, col=1)

                # Horizontal Target & Stop Loss Lines
                fig.add_hline(y=stock_info['Target'], line_dash="dash", line_color="green", annotation_text=f"Target: ₹{stock_info['Target']:.2f}", row=1, col=1)
                fig.add_hline(y=stock_info['StopLoss'], line_dash="dash", line_color="red", annotation_text=f"StopLoss: ₹{stock_info['StopLoss']:.2f}", row=1, col=1)

                # Panel 2: Volume
                colors = ['green' if c >= o else 'red' for c, o in zip(df_chart['Close'], df_chart['Open'])]
                fig.add_trace(go.Bar(
                    x=df_chart.index,
                    y=df_chart['Volume'],
                    name='Volume',
                    marker_color=colors
                ), row=2, col=1)

                # Panel 3: RSI
                fig.add_trace(go.Scatter(
                    x=df_chart.index,
                    y=df_chart['RSI'],
                    mode='lines',
                    name='RSI',
                    line=dict(color='purple', width=2)
                ), row=3, col=1)

                fig.add_hline(y=70, line_dash="dot", line_color="grey", row=3, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="grey", row=3, col=1)

                fig.update_layout(
                    height=800,
                    xaxis_rangeslider_visible=False,
                    template="plotly_white",
                    margin=dict(l=20, r=20, t=40, b=20)
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"Insufficient historical price data found for {ticker_symbol}.")
        except Exception as err:
            st.error(f"Error fetching chart data for {ticker_symbol}: {err}")