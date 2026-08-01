import streamlit as st
import sqlite3
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page Configuration
st.set_page_config(
    page_title="Positional Swing Screener",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Positional Swing Trade Dashboard")
st.caption("Automated momentum setups with RSI & Volume spikes across Nifty 50, Midcap 150, and Smallcap 250.")

# Force clear cache for fresh database reads
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

    # Styling function for positive (green) and negative (red) daily returns
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

    st.subheader("📋 Active Screener Opportunities")
    st.dataframe(
        style_dataframe(display_df),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # Technical Chart Section
    st.subheader("📊 Deep-Dive Technical Chart Analysis")
    
    symbol_list = display_df["Symbol"].tolist()
    selected_stock = st.selectbox("Select a Stock to View Technical Chart & Key Levels:", symbol_list)

    if selected_stock:
        stock_info = display_df[display_df["Symbol"] == selected_stock].iloc[0]
        
        target_gain = round((stock_info['Target'] - stock_info['Entry']) / stock_info['Entry'] * 100, 1)
        sl_loss = round((stock_info['Entry'] - stock_info['StopLoss']) / stock_info['Entry'] * 100, 1)
        day_change = stock_info['1D_Change_%']
        day_color = "#155724" if day_change >= 0 else "#721c24"

        # CUSTOM FULL-WIDTH HTML METRIC CARDS (NO TRUNCATION / NO DOTS)
        st.markdown(f"""
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 25px;">
            <div style="flex: 1; min-width: 150px; background-color: #1e222d; padding: 15px; border-radius: 8px; border-left: 4px solid #2962ff;">
                <p style="color: #8f96a3; margin: 0; font-size: 13px; font-weight: 600;">ENTRY PRICE</p>
                <h3 style="color: #ffffff; margin: 5px 0 0 0; font-size: 22px; font-weight: 700;">₹{stock_info['Entry']:.2f}</h3>
            </div>
            <div style="flex: 1; min-width: 150px; background-color: #1e222d; padding: 15px; border-radius: 8px; border-left: 4px solid #00c853;">
                <p style="color: #8f96a3; margin: 0; font-size: 13px; font-weight: 600;">TARGET PRICE</p>
                <h3 style="color: #00e676; margin: 5px 0 0 0; font-size: 22px; font-weight: 700;">₹{stock_info['Target']:.2f}</h3>
                <span style="color: #00e676; font-size: 12px; font-weight: 600;">▲ +{target_gain}%</span>
            </div>
            <div style="flex: 1; min-width: 150px; background-color: #1e222d; padding: 15px; border-radius: 8px; border-left: 4px solid #ff1744;">
                <p style="color: #8f96a3; margin: 0; font-size: 13px; font-weight: 600;">STOP LOSS</p>
                <h3 style="color: #ff5252; margin: 5px 0 0 0; font-size: 22px; font-weight: 700;">₹{stock_info['StopLoss']:.2f}</h3>
                <span style="color: #ff5252; font-size: 12px; font-weight: 600;">▼ -{sl_loss}%</span>
            </div>
            <div style="flex: 1; min-width: 130px; background-color: #1e222d; padding: 15px; border-radius: 8px; border-left: 4px solid #ab47bc;">
                <p style="color: #8f96a3; margin: 0; font-size: 13px; font-weight: 600;">RSI (14)</p>
                <h3 style="color: #e1bee7; margin: 5px 0 0 0; font-size: 22px; font-weight: 700;">{stock_info['RSI']:.1f}</h3>
            </div>
            <div style="flex: 1; min-width: 130px; background-color: #1e222d; padding: 15px; border-radius: 8px; border-left: 4px solid #00bcd4;">
                <p style="color: #8f96a3; margin: 0; font-size: 13px; font-weight: 600;">1D CHANGE</p>
                <h3 style="color: {day_color}; margin: 5px 0 0 0; font-size: 22px; font-weight: 700;">{day_change:+.2f}%</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)

        ticker_symbol = f"{selected_stock}.NS"
        
        try:
            df_chart = yf.download(ticker_symbol, period="1y", interval="1d", progress=False)

            if isinstance(df_chart.columns, pd.MultiIndex):
                df_chart = df_chart.xs(ticker_symbol, level='Ticker', axis=1) if 'Ticker' in df_chart.columns.names else df_chart.droplevel(1, axis=1)

            if not df_chart.empty:
                df_chart = df_chart.dropna()
                df_chart['SMA50'] = df_chart['Close'].rolling(window=50).mean()

                delta = df_chart['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df_chart['RSI'] = 100 - (100 / (1 + rs))

                fig = make_subplots(
                    rows=3, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.04,
                    subplot_titles=(f"{selected_stock} - Price Action & Key Levels", "Volume Profile", "RSI (14) Momentum"),
                    row_width=[0.2, 0.2, 0.6]
                )

                fig.add_trace(go.Candlestick(
                    x=df_chart.index,
                    open=df_chart['Open'],
                    high=df_chart['High'],
                    low=df_chart['Low'],
                    close=df_chart['Close'],
                    name="Price"
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=df_chart.index,
                    y=df_chart['SMA50'],
                    mode='lines',
                    name='50 SMA',
                    line=dict(color='orange', width=2)
                ), row=1, col=1)

                fig.add_hline(y=stock_info['Target'], line_dash="dash", line_color="green", annotation_text=f"Target: ₹{stock_info['Target']:.2f}", row=1, col=1)
                fig.add_hline(y=stock_info['StopLoss'], line_dash="dash", line_color="red", annotation_text=f"StopLoss: ₹{stock_info['StopLoss']:.2f}", row=1, col=1)

                colors = ['green' if c >= o else 'red' for c, o in zip(df_chart['Close'], df_chart['Open'])]
                fig.add_trace(go.Bar(
                    x=df_chart.index,
                    y=df_chart['Volume'],
                    name='Volume',
                    marker_color=colors
                ), row=2, col=1)

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
                st.warning(f"Could not retrieve chart data for {ticker_symbol}.")
        except Exception as err:
            st.error(f"Error fetching technical chart for {ticker_symbol}: {err}")

else:
    st.error("No trades database found or database is empty!")