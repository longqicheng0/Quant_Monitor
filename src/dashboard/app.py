"""Streamlit dashboard for the Aberration strategy monitor."""

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
from src.research.decision_engine import evaluate_aberration_decision
from src.research.experiment_runner import run_strategy_experiments
from src.strategy.aberration import apply_aberration_strategy
from src.strategy.signals import classify_latest_signal


def load_signal_log(path: Path, max_rows: int = 200) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).tail(max_rows)


def load_latest_report() -> pd.DataFrame:
    report_dir = Path("data/processed")
    files = sorted(report_dir.glob("daily_report_*.csv"))
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[-1])


def decision_box(decision: str) -> str:
    color_map = {
        "TRADE_TOMORROW": "#1b5e20",
        "WATCH_TOMORROW": "#ef6c00",
        "NO_TRADE": "#37474f",
        "NO_DATA": "#6d4c41",
    }
    return color_map.get(decision, "#37474f")


def main() -> None:
    st.set_page_config(page_title="Aberration Strategy Monitor", layout="wide")
    st.title("Aberration Strategy Monitor")
    st.caption("Daily after-close decision support built around one breakout model.")

    settings = DEFAULT_SETTINGS
    st.sidebar.header("Controls")
    ticker = st.sidebar.selectbox("Ticker", settings.monitor.tickers, index=0)
    period = st.sidebar.selectbox("History period", ["6mo", "1y", "2y", "5y"], index=1)
    apply_filters = st.sidebar.checkbox("Show filtered backtest", value=True)
    show_experiments = st.sidebar.checkbox("Show experiments panel", value=False)

    client = YFinanceClient()
    df = client.get_ohlcv(ticker=ticker, interval=settings.monitor.interval, period=period)
    if df.empty:
        st.error("No data returned. Try another ticker or period.")
        return

    strategy_df = apply_aberration_strategy(
        df,
        length=settings.strategy.bollinger_length,
        multiplier=settings.strategy.bollinger_multiplier,
    )
    decision = evaluate_aberration_decision(ticker=ticker, strategy_df=strategy_df, filter_settings=settings.filters)
    latest_signal, latest_state = classify_latest_signal(strategy_df, current_state="flat")

    st.markdown(
        f"""
        <div style='background-color:{decision_box(decision.decision)};padding:12px;border-radius:8px;color:white;font-weight:600;'>
            {ticker}: {decision.decision} | bias={decision.bias} | latest_signal={latest_signal} | state={latest_state}
            <br>{decision.notes}
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
    ax.set_title(f"{ticker} aberration view")
    ax.legend(loc="best")
    ax.grid(alpha=0.2)
    st.pyplot(fig)

    st.subheader("Latest Values")
    latest = strategy_df.iloc[-1]
    cols = st.columns(5)
    cols[0].metric("Close", f"{latest['Close']:.2f}")
    cols[1].metric("Middle", f"{latest['middle_band']:.2f}")
    cols[2].metric("Upper", f"{latest['upper_band']:.2f}")
    cols[3].metric("Lower", f"{latest['lower_band']:.2f}")
    cols[4].metric("Upper Distance", f"{decision.distance_to_upper_pct:.2%}")

    st.subheader("Latest Saved Daily Report")
    latest_report = load_latest_report()
    if latest_report.empty:
        st.info("No saved daily report found yet. Run make report to generate one.")
    else:
        st.dataframe(latest_report, width="stretch")

    st.subheader("Recent Signal Events")
    signal_log = load_signal_log(Path(settings.logging.csv_path))
    if signal_log.empty:
        st.info("No logged signals yet. Run terminal scanner to generate events.")
    else:
        st.dataframe(signal_log.sort_values("event_time", ascending=False).head(25), width="stretch")

    st.subheader("Backtest Summary")
    result = run_backtest(
        data=df,
        bollinger_length=settings.strategy.bollinger_length,
        bollinger_multiplier=settings.strategy.bollinger_multiplier,
        atr_length=settings.filters.atr_length,
        atr_stop_enabled=settings.experiment.atr_stop_enabled and apply_filters,
        atr_stop_multiple=settings.experiment.atr_stop_multiple,
        atr_trailing_enabled=settings.experiment.atr_trailing_enabled and apply_filters,
        atr_trailing_multiple=settings.experiment.atr_trailing_multiple,
        apply_filters=apply_filters,
        filter_settings=settings.filters,
    )
    if result.summary:
        st.dataframe(pd.DataFrame([result.summary]), width="stretch")
        st.line_chart(result.curve[["strategy_curve", "buy_hold_curve"]].copy())

    if show_experiments:
        st.subheader("Aberration Experiments")
        st.caption("Compare baseline vs filtered Aberration across the configured basket.")
        if st.button("Run Experiment Comparison"):
            with st.spinner("Running experiments. This may take a minute..."):
                artifacts = run_strategy_experiments(
                    app_settings=settings,
                    strategy_family="aberration",
                    output_prefix="dashboard_experiment",
                )

            st.success("Experiment run finished.")
            if artifacts.aggregate_df.empty:
                st.warning("No experiment rows returned. Try checking ticker data availability.")
            else:
                st.write("Aggregate Metrics")
                st.dataframe(artifacts.aggregate_df, width="stretch")

            if not artifacts.family_df.empty:
                st.write("Baseline vs Filtered Comparison")
                st.dataframe(artifacts.family_df, width="stretch")

            for line in artifacts.summary_lines:
                st.write(f"- {line}")


if __name__ == "__main__":
    main()
