"""Streamlit dashboard for the strategy monitor."""

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
from src.backtest.backtester import run_backtest
from src.datafeed.yfinance_client import YFinanceClient
from src.strategy.aberration import apply_aberration_strategy
from src.strategy.dual_thrust import apply_dual_thrust_strategy
from src.strategy.signals import classify_latest_signal_for_strategy


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
        "LONG_EXIT_ON_FLIP_TO_SHORT": "#ef6c00",
        "SHORT_EXIT_ON_FLIP_TO_LONG": "#00838f",
        "NO_SIGNAL": "#455a64",
    }
    return color_map.get(signal, "#455a64"), signal


def main() -> None:
    st.set_page_config(page_title="Strategy Monitor", layout="wide")
    st.title("Strategy Monitor")
    st.caption("Monitoring and alerting only. No execution layer in this repository.")

    settings = DEFAULT_SETTINGS

    st.sidebar.header("Controls")
    strategy_name = st.sidebar.selectbox(
        "Strategy",
        ["aberration", "dual_thrust"],
        index=0 if settings.strategy.strategy_name.lower() == "aberration" else 1,
    )
    ticker = st.sidebar.selectbox("Ticker", settings.monitor.tickers, index=0)
    period = st.sidebar.selectbox("History period", ["6mo", "1y", "2y", "5y"], index=1)
    show_backtest = st.sidebar.checkbox("Show backtest summary", value=True)

    client = YFinanceClient()
    df = client.get_ohlcv(ticker=ticker, interval=settings.monitor.timeframe, period=period)

    if df.empty:
        st.error("No data returned. Try another ticker or period.")
        return

    if strategy_name == "aberration":
        strategy_df = apply_aberration_strategy(
            df,
            length=settings.strategy.bollinger_length,
            multiplier=settings.strategy.bollinger_multiplier,
        )
    else:
        strategy_df = apply_dual_thrust_strategy(
            df,
            lookback=settings.strategy.dual_thrust_lookback,
            multiplier=settings.strategy.dual_thrust_multiplier,
        )

    latest_signal, latest_state = classify_latest_signal_for_strategy(
        strategy_df,
        strategy_name=strategy_name,
        current_state="flat",
    )
    color, label = signal_box(latest_signal)

    st.markdown(
        f"""
        <div style='background-color:{color};padding:12px;border-radius:8px;color:white;font-weight:600;'>
            Latest signal for {ticker} ({strategy_name}): {label} | state={latest_state}
        </div>
        """,
        unsafe_allow_html=True,
    )

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(strategy_df.index, strategy_df["Close"], label="Close", linewidth=1.5)

    if strategy_name == "aberration":
        ax.plot(strategy_df.index, strategy_df["middle_band"], label="Middle Band", linewidth=1.2)
        ax.plot(strategy_df.index, strategy_df["upper_band"], label="Upper Band", linewidth=1.0)
        ax.plot(strategy_df.index, strategy_df["lower_band"], label="Lower Band", linewidth=1.0)
    else:
        ax.plot(strategy_df.index, strategy_df["upper_trigger"], label="Upper Trigger", linewidth=1.0)
        ax.plot(strategy_df.index, strategy_df["lower_trigger"], label="Lower Trigger", linewidth=1.0)

    long_entries = strategy_df[strategy_df["long_entry"]]
    short_entries = strategy_df[strategy_df["short_entry"]]

    ax.scatter(long_entries.index, long_entries["Close"], marker="^", s=60, label="Long Entry")
    ax.scatter(short_entries.index, short_entries["Close"], marker="v", s=60, label="Short Entry")

    if strategy_name == "aberration":
        long_exits = strategy_df[strategy_df["long_exit"]]
        short_exits = strategy_df[strategy_df["short_exit"]]
        ax.scatter(long_exits.index, long_exits["Close"], marker="x", s=60, label="Long Exit")
        ax.scatter(short_exits.index, short_exits["Close"], marker="x", s=60, label="Short Exit")
    else:
        long_flip_exits = strategy_df[strategy_df["long_exit_on_flip"]]
        short_flip_exits = strategy_df[strategy_df["short_exit_on_flip"]]
        ax.scatter(long_flip_exits.index, long_flip_exits["Close"], marker="x", s=60, label="Long Exit on Flip")
        ax.scatter(short_flip_exits.index, short_flip_exits["Close"], marker="x", s=60, label="Short Exit on Flip")

    ax.set_title(f"{ticker} {strategy_name} view")
    ax.legend(loc="best")
    ax.grid(alpha=0.2)
    st.pyplot(fig)

    st.subheader("Latest Values")
    latest = strategy_df.iloc[-1]
    if strategy_name == "aberration":
        cols = st.columns(4)
        cols[0].metric("Close", f"{latest['Close']:.2f}")
        cols[1].metric("Middle", f"{latest['middle_band']:.2f}")
        cols[2].metric("Upper", f"{latest['upper_band']:.2f}")
        cols[3].metric("Lower", f"{latest['lower_band']:.2f}")
    else:
        cols = st.columns(4)
        cols[0].metric("Close", f"{latest['Close']:.2f}")
        cols[1].metric("Open", f"{latest['Open']:.2f}")
        cols[2].metric("Upper Trigger", f"{latest['upper_trigger']:.2f}")
        cols[3].metric("Lower Trigger", f"{latest['lower_trigger']:.2f}")

    st.subheader("Recent Signal Events")
    signal_log = load_signal_log(Path(settings.logging.csv_path))
    if signal_log.empty:
        st.info("No logged signals yet. Run terminal scanner to generate events.")
    else:
        if "strategy_name" in signal_log.columns:
            signal_log = signal_log[signal_log["strategy_name"] == strategy_name]
        st.dataframe(signal_log.sort_values("event_time", ascending=False).head(25), use_container_width=True)

    if show_backtest:
        st.subheader("Backtest Summary")
        result = run_backtest(
            strategy_name=strategy_name,
            data=df,
            bollinger_length=settings.strategy.bollinger_length,
            bollinger_multiplier=settings.strategy.bollinger_multiplier,
            dual_thrust_lookback=settings.strategy.dual_thrust_lookback,
            dual_thrust_multiplier=settings.strategy.dual_thrust_multiplier,
        )
        if result.summary:
            summary_df = pd.DataFrame([result.summary])
            st.dataframe(summary_df, use_container_width=True)

            chart_df = result.curve[["strategy_curve", "buy_hold_curve"]].copy()
            st.line_chart(chart_df)


if __name__ == "__main__":
    main()
