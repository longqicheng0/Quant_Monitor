"""Offline signal replay utility for historical Aberration events.

This script is useful for demos and sanity checks without running the live monitor loop.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from config.settings import DEFAULT_SETTINGS
from src.datafeed.yfinance_client import YFinanceClient
from src.strategy.aberration import apply_aberration_strategy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay historical Aberration signals")
    parser.add_argument("--ticker", type=str, default="SPY", help="Ticker symbol")
    parser.add_argument("--interval", type=str, default="1d", help="Data interval (default: 1d)")
    parser.add_argument("--period", type=str, default="2y", help="History period (default: 2y)")
    parser.add_argument(
        "--max-events",
        type=int,
        default=25,
        help="How many latest events to print",
    )
    parser.add_argument(
        "--save-csv",
        type=str,
        default="",
        help="Optional path to save replay events CSV",
    )
    parser.add_argument(
        "--save-plot",
        type=str,
        default="",
        help="Optional path to save replay plot image (PNG)",
    )
    parser.add_argument(
        "--show-plot",
        action="store_true",
        help="Show interactive matplotlib window if available",
    )
    return parser.parse_args()


def build_event_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for ts, row in df.iterrows():
        if bool(row["long_entry"]):
            rows.append({"bar_time": ts, "signal": "LONG_ENTRY", "close": row["Close"]})
        if bool(row["short_entry"]):
            rows.append({"bar_time": ts, "signal": "SHORT_ENTRY", "close": row["Close"]})
        if bool(row["long_exit"]):
            rows.append({"bar_time": ts, "signal": "LONG_EXIT", "close": row["Close"]})
        if bool(row["short_exit"]):
            rows.append({"bar_time": ts, "signal": "SHORT_EXIT", "close": row["Close"]})

    if not rows:
        return pd.DataFrame(columns=["bar_time", "signal", "close"])

    out = pd.DataFrame(rows)
    out["bar_time"] = pd.to_datetime(out["bar_time"])
    out = out.sort_values("bar_time").reset_index(drop=True)
    return out


def build_trade_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build closed trade list from Aberration signals.

    Uses one-position-at-a-time logic.
    """
    trades = []
    state = "flat"
    open_trade = None

    for ts, row in df.iterrows():
        price = float(row["Close"])

        if state == "flat":
            if bool(row["long_entry"]):
                state = "long"
                open_trade = {"side": "LONG", "entry_time": ts, "entry_price": price}
            elif bool(row["short_entry"]):
                state = "short"
                open_trade = {"side": "SHORT", "entry_time": ts, "entry_price": price}

        elif state == "long" and bool(row["long_exit"]) and open_trade is not None:
            pnl_pct = (price - open_trade["entry_price"]) / open_trade["entry_price"] * 100.0
            trades.append(
                {
                    "side": open_trade["side"],
                    "entry_time": open_trade["entry_time"],
                    "exit_time": ts,
                    "entry_price": open_trade["entry_price"],
                    "exit_price": price,
                    "pnl_pct": pnl_pct,
                }
            )
            state = "flat"
            open_trade = None

        elif state == "short" and bool(row["short_exit"]) and open_trade is not None:
            pnl_pct = (open_trade["entry_price"] - price) / open_trade["entry_price"] * 100.0
            trades.append(
                {
                    "side": open_trade["side"],
                    "entry_time": open_trade["entry_time"],
                    "exit_time": ts,
                    "entry_price": open_trade["entry_price"],
                    "exit_price": price,
                    "pnl_pct": pnl_pct,
                }
            )
            state = "flat"
            open_trade = None

    if not trades:
        return pd.DataFrame(
            columns=["side", "entry_time", "exit_time", "entry_price", "exit_price", "pnl_pct"]
        )

    trade_df = pd.DataFrame(trades)
    trade_df["entry_time"] = pd.to_datetime(trade_df["entry_time"])
    trade_df["exit_time"] = pd.to_datetime(trade_df["exit_time"])
    return trade_df


def build_summary(events: pd.DataFrame, trades: pd.DataFrame, result: pd.DataFrame) -> dict[str, str]:
    """Create a compact summary dictionary for display."""
    total_events = len(events)
    total_trades = len(trades)

    if total_trades > 0:
        win_rate = float((trades["pnl_pct"] > 0).mean() * 100.0)
        avg_pnl = float(trades["pnl_pct"].mean())
        total_pnl = float(trades["pnl_pct"].sum())
    else:
        win_rate = 0.0
        avg_pnl = 0.0
        total_pnl = 0.0

    latest_close = float(result["Close"].iloc[-1])
    latest_date = pd.to_datetime(result.index[-1]).strftime("%Y-%m-%d")

    return {
        "Bars": str(len(result)),
        "Total events": str(total_events),
        "Closed trades": str(total_trades),
        "Win rate": f"{win_rate:.1f}%",
        "Avg trade PnL": f"{avg_pnl:.2f}%",
        "Total PnL (sum)": f"{total_pnl:.2f}%",
        "Latest close": f"{latest_close:.2f}",
        "Latest bar": latest_date,
    }


def plot_replay(
    ticker: str,
    ticker_name: str,
    interval: str,
    period: str,
    result: pd.DataFrame,
    trades: pd.DataFrame,
    summary: dict[str, str],
    save_plot_path: str,
    show_plot: bool,
) -> None:
    """Render left price plot and right summary/trades table."""
    fig, (ax_price, ax_table) = plt.subplots(
        ncols=2,
        figsize=(16, 7),
        gridspec_kw={"width_ratios": [3.4, 1.8]},
    )

    ax_price.plot(result.index, result["Close"], label="Close", linewidth=1.6)
    ax_price.plot(result.index, result["middle_band"], label="Middle Band", linewidth=1.1)
    ax_price.plot(result.index, result["upper_band"], label="Upper Band", linewidth=1.0)
    ax_price.plot(result.index, result["lower_band"], label="Lower Band", linewidth=1.0)

    long_entries = result[result["long_entry"]]
    short_entries = result[result["short_entry"]]
    long_exits = result[result["long_exit"]]
    short_exits = result[result["short_exit"]]

    ax_price.scatter(long_entries.index, long_entries["Close"], marker="^", s=45, label="Long Entry")
    ax_price.scatter(short_entries.index, short_entries["Close"], marker="v", s=45, label="Short Entry")
    ax_price.scatter(long_exits.index, long_exits["Close"], marker="x", s=45, label="Long Exit")
    ax_price.scatter(short_exits.index, short_exits["Close"], marker="x", s=45, label="Short Exit")

    ax_price.set_title(f"{ticker} - {ticker_name} | Aberration Replay ({interval}, {period})")
    ax_price.grid(alpha=0.25)
    ax_price.legend(loc="best", fontsize=8)

    ax_table.axis("off")
    summary_lines = [f"{k}: {v}" for k, v in summary.items()]
    ax_table.text(
        0.02,
        0.98,
        "Summary\n" + "\n".join(summary_lines),
        va="top",
        ha="left",
        fontsize=10,
        family="monospace",
    )

    recent = trades.tail(8).copy()
    if not recent.empty:
        recent["entry_time"] = recent["entry_time"].dt.strftime("%Y-%m-%d")
        recent["exit_time"] = recent["exit_time"].dt.strftime("%Y-%m-%d")
        recent["entry_price"] = recent["entry_price"].map(lambda x: f"{x:.2f}")
        recent["exit_price"] = recent["exit_price"].map(lambda x: f"{x:.2f}")
        recent["pnl_pct"] = recent["pnl_pct"].map(lambda x: f"{x:.2f}%")

        table = ax_table.table(
            cellText=recent.values,
            colLabels=["Side", "Entry", "Exit", "Entry Px", "Exit Px", "PnL"],
            cellLoc="center",
            loc="lower left",
            bbox=[0.0, 0.02, 1.0, 0.56],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)

    fig.tight_layout()

    out_path = Path(save_plot_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    print(f"Saved replay plot to: {out_path}")

    if show_plot:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    args = parse_args()
    settings = DEFAULT_SETTINGS

    client = YFinanceClient()
    ticker_name = client.get_ticker_name(args.ticker)
    raw = client.get_ohlcv(ticker=args.ticker, interval=args.interval, period=args.period)

    if raw.empty:
        print("No data returned. Try a different ticker/period.")
        return

    result = apply_aberration_strategy(
        raw,
        length=settings.strategy.bollinger_length,
        multiplier=settings.strategy.bollinger_multiplier,
    )
    events = build_event_table(result)
    trades = build_trade_table(result)
    summary = build_summary(events=events, trades=trades, result=result)

    print(f"\nReplay for {args.ticker} - {ticker_name} ({args.interval}, {args.period})")
    print(f"Bars: {len(result)}")
    print(f"Total detected events: {len(events)}")

    if events.empty:
        print("No crossover events detected in this period.")
    else:
        print("\nLatest events:")
        print(events.tail(args.max_events).to_string(index=False))

    if not trades.empty:
        print("\nLatest closed trades:")
        print(trades.tail(min(args.max_events, 10)).to_string(index=False))

    if args.save_csv:
        out_path = Path(args.save_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        events.to_csv(out_path, index=False)
        print(f"\nSaved replay events to: {out_path}")

    default_plot_path = f"data/processed/{args.ticker.lower()}_replay.png"
    plot_path = args.save_plot or default_plot_path
    plot_replay(
        ticker=args.ticker,
        ticker_name=ticker_name,
        interval=args.interval,
        period=args.period,
        result=result,
        trades=trades,
        summary=summary,
        save_plot_path=plot_path,
        show_plot=args.show_plot,
    )


if __name__ == "__main__":
    main()
