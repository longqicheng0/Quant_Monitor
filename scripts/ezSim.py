"""Single-file SNDK 1-year simulation from a fixed starting capital.

Usage:
    python3 scripts/ezSim.py
"""

from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from config.settings import DEFAULT_SETTINGS
from src.strategy.aberration import apply_aberration_strategy
from src.backtest.backtester import run_aberration_backtest
from src.datafeed.yfinance_client import YFinanceClient


# Simulation inputs: edit these values, then run this script again.
SIM_TICKER = "KRKNF"
SIM_INTERVAL = "1d"
SIM_PERIOD = "1y"
SIM_INITIAL_CAPITAL_CAD = 100_000.0
SIM_OUTPUT_PREFIX = "simulation_krknf_1y"


def parse_args() -> argparse.Namespace:
    """Optional overrides: ticker interval period."""
    parser = argparse.ArgumentParser(description="Run Aberration simulation for one ticker.")
    parser.add_argument("ticker", nargs="?", default=None, help="Ticker symbol override, e.g. HG.CN")
    parser.add_argument("interval", nargs="?", default=None, help="Interval override, e.g. 4h")
    parser.add_argument("period", nargs="?", default=None, help="Period override, e.g. 1y")
    return parser.parse_args()


def format_money(value: float) -> str:
    return f"CAD {value:,.2f}"


def safe_slug(text: str) -> str:
    """Convert a label into a filesystem-safe lowercase slug."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()


def build_trade_markers(curve: pd.DataFrame) -> tuple[pd.Index, pd.Index]:
    """Return index locations where position flips into long or short."""
    position = curve["position"].fillna(0)
    previous = position.shift(1).fillna(0)
    long_entries = curve.index[(position == 1) & (previous != 1)]
    short_entries = curve.index[(position == -1) & (previous != -1)]
    return long_entries, short_entries


def save_simulation_plot(
    data: pd.DataFrame,
    strategy_df: pd.DataFrame,
    curve: pd.DataFrame,
    summary: dict[str, float | int | str],
    out_path: Path,
) -> None:
    """Save a chart with Bollinger bands, trade markers, and summary text."""
    long_entries, short_entries = build_trade_markers(curve)
    long_exits = strategy_df.index[strategy_df["long_exit"].fillna(False)]
    short_exits = strategy_df.index[strategy_df["short_exit"].fillna(False)]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    axes[0].plot(data.index, data["Close"], label="Close", linewidth=1.4)
    axes[0].plot(strategy_df.index, strategy_df["middle_band"], label="Middle Band", linewidth=1.1)
    axes[0].plot(strategy_df.index, strategy_df["upper_band"], label="Upper Band", linewidth=1.0)
    axes[0].plot(strategy_df.index, strategy_df["lower_band"], label="Lower Band", linewidth=1.0)
    if len(long_entries) > 0:
        axes[0].scatter(long_entries, data.loc[long_entries, "Close"], marker="^", s=70, label="Long Entry")
    if len(short_entries) > 0:
        axes[0].scatter(short_entries, data.loc[short_entries, "Close"], marker="v", s=70, label="Short Entry")
    if len(long_exits) > 0:
        axes[0].scatter(long_exits, data.loc[long_exits, "Close"], marker="x", s=65, label="Long Exit")
    if len(short_exits) > 0:
        axes[0].scatter(short_exits, data.loc[short_exits, "Close"], marker="x", s=65, label="Short Exit")

    summary_text = (
        f"Start: {summary['start_capital_cad']:,.0f} CAD\n"
        f"End: {summary['strategy_end_value_cad']:,.0f} CAD\n"
        f"Return: {summary['strategy_return']:.2%}\n"
        f"PnL: {summary['strategy_pnl_cad']:,.0f} CAD\n"
        f"Trades: {summary['num_trades']}\n"
        f"Win Rate: {summary['win_rate']:.2%}\n"
        f"MDD: {summary['max_drawdown']:.2%}"
    )
    axes[0].text(
        0.99,
        0.99,
        summary_text,
        transform=axes[0].transAxes,
        va="top",
        ha="right",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
    )

    axes[0].set_title("SNDK Price, Bollinger Bands, and Trade Markers")
    axes[0].set_ylabel("Price")
    axes[0].grid(alpha=0.2)
    axes[0].legend(loc="best")

    axes[1].plot(curve.index, curve["strategy_portfolio_cad"], label="Aberration Portfolio")
    axes[1].plot(curve.index, curve["buy_hold_portfolio_cad"], label="Buy & Hold Portfolio")
    axes[1].set_title("Portfolio Value (CAD)")
    axes[1].set_ylabel("CAD")
    axes[1].grid(alpha=0.2)
    axes[1].legend(loc="best")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    args = parse_args()

    initial_capital_cad = float(SIM_INITIAL_CAPITAL_CAD)
    ticker = str(args.ticker or SIM_TICKER).upper()
    interval = str(args.interval or SIM_INTERVAL)
    period = str(args.period or SIM_PERIOD)
    output_prefix = f"simulation_{safe_slug(ticker)}_{safe_slug(interval)}_{safe_slug(period)}"

    settings = DEFAULT_SETTINGS
    client = YFinanceClient()

    data = client.get_ohlcv(ticker=ticker, interval=interval, period=period)
    if data.empty:
        print(f"No market data returned for {ticker} ({interval}, {period}).")
        return 1

    result = run_aberration_backtest(
        data=data,
        length=settings.strategy.bollinger_length,
        multiplier=settings.strategy.bollinger_multiplier,
        atr_length=settings.filters.atr_length,
        atr_stop_enabled=False,
        atr_stop_multiple=settings.experiment.atr_stop_multiple,
        atr_trailing_enabled=False,
        atr_trailing_multiple=settings.experiment.atr_trailing_multiple,
        apply_filters=False,
    )

    strategy_df = apply_aberration_strategy(
        data,
        length=settings.strategy.bollinger_length,
        multiplier=settings.strategy.bollinger_multiplier,
    )

    if not result.summary:
        print("Backtest did not produce summary metrics.")
        return 1

    strategy_return = float(result.summary.get("total_return", 0.0))
    buy_hold_return = float(result.summary.get("buy_and_hold_return", 0.0))

    final_strategy_value = initial_capital_cad * (1.0 + strategy_return)
    final_buy_hold_value = initial_capital_cad * (1.0 + buy_hold_return)
    pnl_strategy = final_strategy_value - initial_capital_cad
    pnl_buy_hold = final_buy_hold_value - initial_capital_cad

    curve = result.curve.copy()
    curve["strategy_portfolio_cad"] = initial_capital_cad * curve["strategy_curve"]
    curve["buy_hold_portfolio_cad"] = initial_capital_cad * curve["buy_hold_curve"]

    out_dir = Path("data/processed/historical data")
    out_dir.mkdir(parents=True, exist_ok=True)
    curve_out_path = out_dir / f"{output_prefix}_curve.csv"
    summary_out_path = out_dir / f"{output_prefix}_summary.csv"
    plot_out_path = out_dir / f"{output_prefix}_chart.png"
    curve.to_csv(curve_out_path)

    summary = {
        "ticker": ticker,
        "interval": interval,
        "period": period,
        "start_capital_cad": initial_capital_cad,
        "bars_used": len(data),
        "strategy_return": strategy_return,
        "buy_hold_return": buy_hold_return,
        "strategy_end_value_cad": final_strategy_value,
        "buy_hold_end_value_cad": final_buy_hold_value,
        "strategy_pnl_cad": pnl_strategy,
        "buy_hold_pnl_cad": pnl_buy_hold,
        "max_drawdown": float(result.summary.get("max_drawdown", 0.0)),
        "sharpe_ratio": float(result.summary.get("sharpe_ratio", 0.0)),
        "num_trades": int(result.summary.get("num_trades", 0.0)),
        "win_rate": float(result.summary.get("win_rate", 0.0)),
    }
    pd.DataFrame([summary]).to_csv(summary_out_path, index=False)
    save_simulation_plot(data=data, strategy_df=strategy_df, curve=curve, summary=summary, out_path=plot_out_path)

    print(f"{ticker} Simulation ({period}, {interval})")
    print("---------------------------------")
    print(f"Start Capital        : {format_money(initial_capital_cad)}")
    print(f"Ticker               : {ticker}")
    print(f"Bars Used            : {len(data)}")
    print(f"Strategy Return      : {strategy_return:.2%}")
    print(f"Buy & Hold Return    : {buy_hold_return:.2%}")
    print(f"Strategy End Value   : {format_money(final_strategy_value)}")
    print(f"Buy & Hold End Value : {format_money(final_buy_hold_value)}")
    print(f"Strategy PnL         : {format_money(pnl_strategy)}")
    print(f"Buy & Hold PnL       : {format_money(pnl_buy_hold)}")
    print(f"Max Drawdown         : {float(result.summary.get('max_drawdown', 0.0)):.2%}")
    print(f"Sharpe Ratio         : {float(result.summary.get('sharpe_ratio', 0.0)):.3f}")
    print(f"Trades               : {int(result.summary.get('num_trades', 0.0))}")
    print(f"Win Rate             : {float(result.summary.get('win_rate', 0.0)):.2%}")
    print(f"Saved Curve CSV      : {curve_out_path}")
    print(f"Saved Summary CSV    : {summary_out_path}")
    print(f"Saved Chart PNG      : {plot_out_path}")
    print("\nNote: Market prices are not FX-converted; this script labels portfolio in CAD.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
