import streamlit as st
import sqlite3
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Positional Swing Screener",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Positional Swing Trade Dashboard")
st.caption("Automated momentum setups with RSI & Volume spikes across Nifty 50, Midcap 150, and Smallcap 250.")

# Load trades from SQLite Database
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
    # Sidebar Filters
    st.sidebar.header("Filter Options")
    category = st.sidebar.radio(
        "Select Market Cap Category:",
        ["All", "LargeCap", "MidCap", "SmallCap"]
    )

    # Filter data based on selection
    if category != "All":
        display_df = df_trades[df_trades["Category"] == category]
    else:
        display_df = df_trades

    # Top KPI Cards
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Opportunities", len(display_df))
    col2.metric("Market Segment", category)
    col3.metric("Status", "Live / SQL Synced")

    st.markdown("---")

    # Format Dataframe Display
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Entry": st.column_config.NumberColumn("Entry (₹)", format="₹%.2f"),
            "Target": st.column_config.NumberColumn("Target (₹)", format="₹%.2f"),
            "StopLoss": st.column_config.NumberColumn("Stop Loss (₹)", format="₹%.2f"),
            "RSI": st.column_config.NumberColumn("RSI (14)", format="%.1f"),
            "TrendStrength_%": st.column_config.NumberColumn("Trend Strength %", format="%.2f%%"),
        }
    )

else:
    st.error("No trades database found or database is empty! Make sure 'trades.db' exists and is populated.")
