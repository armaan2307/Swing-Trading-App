import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(
    page_title="Positional Swing Screener",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Positional Swing Trade Dashboard")
st.caption("Automated momentum setups with RSI & Volume spikes across Nifty 50, Midcap 150, and Smallcap 250.")

# Clear cache to ensure immediate updates from trades.db
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
                # Soft green background, dark green text
                return ['background-color: #d4edda; color: #155724; font-weight: bold'] * len(row)
            elif val < 0:
                # Soft red background, dark red text
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
    st.dataframe(
        style_dataframe(display_df),
        use_container_width=True,
        hide_index=True
    )

else:
    st.error("No trades database found or database is empty! Run your screener script first.")