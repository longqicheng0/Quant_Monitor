"""Streamlit dashboard for the Aberration Strategy Monitor."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from config.settings import DEFAULT_SETTINGS
from src.backtest.backtester import run_aberration_backtest
from src.datafeed.yfinance_client import YFinanceClient
from src.strategy.aberration import apply_aberration_strategy
from src.strategy.signals import classify_latest_signal


def load_signal_log(path: Path, max_rows: int = 200) -> pd.DataFrame:
    """Load recent signal history from CSV if available."""
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df.tail(max_rows)


def signal_box(signal: str) -> tuple[str, str]:
    """Map signal name to dashboard color and label."""
    color_map = {
        "LONG_ENTRY": "#2e7d32",
        "SHORT_ENTRY": "#c62828",
        "LONG_EXIT": "#1565c0",
        "SHORT_EXIT": "#6a1b9a",
        "NO_SIGNAL": "#455a64",
    }
    return color_map.get(signal, "#455a64"), signal


def main() -> None:
    st.set_page_config(page_title="Aberration Monitor", layout="wide")
    st.title("Aberration Strategy Monitor")
    st.caption("Monitoring and alerting only. No execution layer in this repository.")

    settings = DEFAULT_SETTINGS

    st.sidebar.header("Controls")
    ticker = st.sidebar.selectbox("Ticker", settings.monitor.tickers, index=0)
    period = st.sidebar.selectbox("History period", ["6mo", "1y", "2y", "5y"], index=1)
    show_backtest = st.sidebar.checkbox("Show backtest summary", value=True)

    client = YFinanceClient()
    df = client.get_ohlcv(ticker=ticker, interval=settings.monitor.timeframe, period=period)

    if df.empty:
        st.error("No data returned. Try another ticker or period.")
        return

    strategy_df = apply_aberration_strategy(
        df,
        length=settings.strategy.bollinger_length,
        multiplier=settings.strategy.bollinger_multiplier,
    )

    latest_signal, _ = classify_latest_signal(strategy_df, current_state="flat")
    color, label = signal_box(latest_signal)

    st.markdown(
        f"""
        <div style='background-color:{color};padding:12px;border-radius:8px;color:white;font-weight:600;'>
            Latest signal for {ticker}: {label}
        </div>
        """,
        unsafe_allow_html=True,
    )

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(strategy_df.index, strategy_df["Close"], label="Close", linewidth=1.5)
    ax.plot(strategy_df.index, strategy_df["middle_band"], label="Middle Band", linewidth=1.2)
    ax.plot(strategy_df.index, strategy_df["upper_band"], label="Upper Band", linewidth=1.0)
    ax.plot(strategy_df.index, strategy_df["lower_band"], label="Lower Band", linewidth=1.0)

    long_entries = strategy_df[strategy_df["long_entry"]]
    short_entries = strategy_df[strategy_df["short_entry"]]
    long_exits = strategy_df[strategy_df["long_exit"]]
    short_exits = strategy_df[strategy_df["short_exit"]]

    ax.scatter(long_entries.index, long_entries["Close"], marker="^", s=60, label="Long Entry")
    ax.scatter(short_entries.index, short_entries["Close"], marker="v", s=60, label="Short Entry")
    ax.scatter(long_exits.index, long_exits["Close"], marker="x", s=60, label="Long Exit")
    ax.scatter(short_exits.index, short_exits["Close"], marker="x", s=60, label="Short Exit")

    ax.set_title(f"{ticker} Close and Bollinger Bands")
    ax.legend(loc="best")
    ax.grid(alpha=0.2)
    st.pyplot(fig)

    st.subheader("Latest Values")
    latest = strategy_df.iloc[-1]
    cols = st.columns(4)
    cols[0].metric("Close", f"{latest['Close']:.2f}")
    cols[1].metric("Middle", f"{latest['middle_band']:.2f}")
    cols[2].metric("Upper", f"{latest['upper_band']:.2f}")
    cols[3].metric("Lower", f"{latest['lower_band']:.2f}")

    st.subheader("Recent Signal Events")
    signal_log = load_signal_log(Path(settings.logging.csv_path))
    if signal_log.empty:
        st.info("No logged signals yet. Run terminal scanner to generate events.")
    else:
        st.dataframe(signal_log.sort_values("event_time", ascending=False).head(25), use_container_width=True)

    if show_backtest:
        st.subheader("Backtest Summary")
        result = run_aberration_backtest(
            strategy_df,
            length=settings.strategy.bollinger_length,
            multiplier=settings.strategy.bollinger_multiplier,
        )
        if result.summary:
            summary_df = pd.DataFrame([result.summary])
            st.dataframe(summary_df, use_container_width=True)

            chart_df = result.curve[["strategy_curve", "buy_hold_curve"]].copy()
            st.line_chart(chart_df)


if __name__ == "__main__":
    main()
