# live_tracker7day_fixed.py
import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="BTC & ETH 7-Day Tracker (Fixed Scale)", layout="wide")
st.title("BTC & ETH 7-Day Live Tracker — Fixed scales & EMAs")

# -------------------------
# Settings
# -------------------------
refresh_interval = 60  # seconds
days_to_track = 7
tickers = ["BTC-USD", "ETH-USD"]
ema_period = 7  # 7-period EMA

# -------------------------
# Auto-refresh logic
# -------------------------
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = datetime.now()

elapsed = (datetime.now() - st.session_state["last_refresh"]).seconds
remaining = max(refresh_interval - elapsed, 0)
st.markdown(f"⏳ **Next update in:** {remaining} s")

if elapsed >= refresh_interval:
    st.session_state["last_refresh"] = datetime.now()
    st.rerun()

# -------------------------
# Fetch 1-hour Close price data for last 7 days
# -------------------------
end = datetime.now()
start = end - timedelta(days=days_to_track)

raw = yf.download(tickers, start=start, end=end, interval="1h")
# Use Close only (no Adj Close)
if "Close" in raw.columns.levels[0] if isinstance(raw.columns, pd.MultiIndex) else "Close" in raw.columns:
    # yf returns single-level columns when multiple tickers -> raw['Close'] may or may not exist as top-level
    pass

# Normalize access to Close columns robustly
if isinstance(raw.columns, pd.MultiIndex):
    # multiindex returned: ('Close','BTC-USD'), ('Close','ETH-USD')
    data = raw["Close"].copy()
else:
    # single-level columns already 'BTC-USD','ETH-USD' (Close provided directly)
    # Some yfinance versions return DataFrame with Close directly for crypto
    if "BTC-USD" in raw.columns and "ETH-USD" in raw.columns:
        data = raw[["BTC-USD", "ETH-USD"]].copy()
    else:
        # Fallback: try to get 'Close' key (rare), else raise
        try:
            data = raw["Close"].copy()
        except Exception as e:
            st.error("Could not parse data from yfinance. Raw columns: " + ", ".join(map(str, raw.columns)))
            st.stop()

# Fill gaps
data = data.ffill().bfill()

# Ensure we have enough rows
if data.empty or len(data) < 2:
    st.error("No data returned from yfinance for the selected range.")
    st.stop()

# -------------------------
# Compute portfolios (normalized to 1.0 at start)
# -------------------------
btc = data["BTC-USD"] / data["BTC-USD"].iloc[0]
eth = data["ETH-USD"] / data["ETH-USD"].iloc[0]
mix = 0.5 * btc + 0.5 * eth  # 50/50 average

portfolios = pd.DataFrame({
    "100% BTC": btc,
    "100% ETH": eth,
    "50% BTC + 50% ETH (Average)": mix
}, index=data.index)

# Compute fixed y-axis domain for portfolios (so changing zoom/refresh won't re-scale)
y_min = portfolios.min().min() * 0.995
y_max = portfolios.max().max() * 1.005

# -------------------------
# Portfolio chart (fixed y-axis)
# -------------------------
fig_port = go.Figure()
fig_port.add_trace(go.Scatter(x=portfolios.index, y=portfolios["100% BTC"],
                              name="100% BTC", line=dict(width=3, color="#FF9900")))
fig_port.add_trace(go.Scatter(x=portfolios.index, y=portfolios["100% ETH"],
                              name="100% ETH", line=dict(width=3, color="#6A5ACD")))
fig_port.add_trace(go.Scatter(x=portfolios.index, y=portfolios["50% BTC + 50% ETH (Average)"],
                              name="50/50 (Average)", line=dict(width=4, dash="dash", color="black")))

fig_port.update_layout(
    title=f"Portfolio Performance (Last {days_to_track} days, normalized)",
    xaxis_title="Datetime (UTC)",
    yaxis_title="Normalized value (Base = 1.0)",
    template="plotly_white",
    hovermode="x unified",
    height=700,
    font=dict(size=14)
)
# enforce fixed y-axis range
fig_port.update_yaxes(range=[y_min, y_max])

st.plotly_chart(fig_port, use_container_width=True)
st.caption(f"📅 Portfolio chart last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S (UTC)')}")

# -------------------------
# BTC price + EMA (its own chart and scale)
# -------------------------
btc_price = data["BTC-USD"].copy()
btc_ema = btc_price.ewm(span=ema_period, adjust=False).mean()

fig_btc = go.Figure()
fig_btc.add_trace(go.Scatter(x=btc_price.index, y=btc_price, name="BTC-USD Price", line=dict(width=3, color="orange")))
fig_btc.add_trace(go.Scatter(x=btc_ema.index, y=btc_ema, name=f"{ema_period}-period EMA",
                             line=dict(width=3, color="black", dash="dot")))

fig_btc.update_layout(
    title=f"Bitcoin (BTC-USD) Price (Last {days_to_track} days) & {ema_period}-period EMA",
    xaxis_title="Datetime (UTC)",
    yaxis_title="Price (USD)",
    template="plotly_white",
    hovermode="x unified",
    height=600,
    font=dict(size=14)
)
st.plotly_chart(fig_btc, use_container_width=True)
st.caption(f"📅 BTC price last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S (UTC)')}")

# -------------------------
# ETH price + EMA (its own chart and scale)
# -------------------------
eth_price = data["ETH-USD"].copy()
eth_ema = eth_price.ewm(span=ema_period, adjust=False).mean()

fig_eth = go.Figure()
fig_eth.add_trace(go.Scatter(x=eth_price.index, y=eth_price, name="ETH-USD Price", line=dict(width=3, color="purple")))
fig_eth.add_trace(go.Scatter(x=eth_ema.index, y=eth_ema, name=f"{ema_period}-period EMA",
                             line=dict(width=3, color="green", dash="dot")))

fig_eth.update_layout(
    title=f"Ethereum (ETH-USD) Price (Last {days_to_track} days) & {ema_period}-period EMA",
    xaxis_title="Datetime (UTC)",
    yaxis_title="Price (USD)",
    template="plotly_white",
    hovermode="x unified",
    height=600,
    font=dict(size=14)
)
st.plotly_chart(fig_eth, use_container_width=True)
st.caption(f"📅 ETH price last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S (UTC)')}")

# -------------------------
# Signals & metrics
# -------------------------
eth_last = portfolios["100% ETH"].iloc[-1]
btc_last = portfolios["100% BTC"].iloc[-1]
eth_btc_ratio = eth_last / btc_last
eth_return_pct = (eth_last - 1) * 100
btc_return_pct = (btc_last - 1) * 100
diff_pct = eth_return_pct - btc_return_pct

col1, col2, col3 = st.columns(3)
col1.metric("BTC normalized", f"{btc_last:.4f}", f"{btc_return_pct:.2f}%")
col2.metric("ETH normalized", f"{eth_last:.4f}", f"{eth_return_pct:.2f}%")
col3.metric("ETH/BTC ratio", f"{eth_btc_ratio:.4f}", f"{diff_pct:.2f}%")

# Recovery signal
if eth_last > btc_last:
    st.success(f"🟢 ETH Recovery Detected — ETH > BTC (ETH/BTC ratio {eth_btc_ratio:.4f})")
else:
    st.warning(f"🔴 BTC Leading — BTC > ETH (ETH/BTC ratio {eth_btc_ratio:.4f})")

st.markdown("---")
st.caption("Notes: portfolio chart is normalized (start = 1.0). Price charts use absolute USD prices and their own scales.")
