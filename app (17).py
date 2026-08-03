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

st.title("📈 Positional Swing Trade Workstation")

# ---------------------------------------------------------
# ---------------------------------------------------------
# ---------------------------------------------------------
# TOP BENCHMARK INDICES BAR (NO TRUNCATION / STYLED BOXES)
# ---------------------------------------------------------
# CSS to auto-scale st.metric font size so big numbers never truncate
st.markdown("""
<style>
div[data-testid="stMetricValue"] {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache index prices for 5 minutes
def fetch_index_data():
    indices = {
        "NIFTY 50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "NIFTY MIDCAP": "^NSEMDCP50"
    }
    
    index_results = {}
    for name, ticker in indices.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            if len(data) >= 2:
                last_price = data['Close'].iloc[-1]
                prev_price = data['Close'].iloc[-2]
                change_pct = ((last_price - prev_price) / prev_price) * 100
                index_results[name] = (last_price, change_pct)
        except Exception:
            continue
    return index_results

indices_data = fetch_index_data()

if indices_data:
    cols = st.columns(len(indices_data))
    for i, (name, (price, change)) in enumerate(indices_data.items()):
        with cols[i].container(border=True):
            st.metric(
                label=name,
                value=f"{price:,.2f}",
                delta=f"{change:+.2f}%"
            )

st.markdown("---")

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
    category = st.sidebar.radio("Select Market Cap:", ["All", "LargeCap", "MidCap", "SmallCap"])

    display_df = df_trades if category == "All" else df_trades[df_trades["Category"] == category]

    # Metrics Row
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Opportunities", len(display_df))
    col2.metric("Market Segment", category)
    col3.metric("Status", "Live")

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

    # Technical Chart & Deep Analysis Section
    st.subheader("📊 Technical Chart Analysis")
    
    symbol_list = display_df["Symbol"].tolist()
    selected_stock = st.selectbox("Select a Stock to View Technical Chart & Key Levels:", symbol_list)

    if selected_stock:
        stock_info = display_df[display_df["Symbol"] == selected_stock].iloc[0]
        
        target_gain = round((stock_info['Target'] - stock_info['Entry']) / stock_info['Entry'] * 100, 1)
        sl_loss = round((stock_info['Entry'] - stock_info['StopLoss']) / stock_info['Entry'] * 100, 1)
        day_change = stock_info['1D_Change_%']
        day_color = "#00e676" if day_change >= 0 else "#ff5252"

        # CUSTOM HTML METRIC CARDS
        st.markdown(f"""
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
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

        # ---------------------------------------------------------
        # POSITION SIZING & RISK CALCULATOR WIDGET
        # ---------------------------------------------------------
        with st.expander("🧮 **Position Sizing & Risk Management Calculator**", expanded=True):
            r_col1, r_col2 = st.columns(2)
            
            with r_col1:
                total_capital = st.number_input("Total Trading Capital (₹)", value=500000, step=25000)
                risk_pct = st.slider("Max Risk Per Trade (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.25)
            
            risk_per_share = stock_info['Entry'] - stock_info['StopLoss']
            reward_per_share = stock_info['Target'] - stock_info['Entry']
            
            if risk_per_share > 0:
                max_allowed_loss = total_capital * (risk_pct / 100.0)
                quantity = int(max_allowed_loss // risk_per_share)
                total_investment = quantity * stock_info['Entry']
                rr_ratio = reward_per_share / risk_per_share
                
                with r_col2:
                    st.markdown("#### **Execution Parameters**")
                    st.markdown(f"• **Recommended Position Size:** `{quantity:,} shares`")
                    st.markdown(f"• **Total Capital Deployed:** `₹{total_investment:,.2f}` ({round((total_investment/total_capital)*100, 1)}% of portfolio)")
                    st.markdown(f"• **Max Dollar Risk:** `₹{max_allowed_loss:,.2f}` (Strict Limit)")
                    st.markdown(f"• **Risk-to-Reward Ratio:** `1 : {rr_ratio:.2f}`")

        st.markdown("<br>", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # PLOTLY CHART RENDERING
        # ---------------------------------------------------------
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