"""Simple backtester for Aberration strategy research."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.research.filters import apply_entry_filters, compute_atr
from src.strategy.aberration import apply_aberration_strategy


@dataclass
class BacktestResult:
    """Container for backtest summary and curves."""

    summary: dict[str, float]
    curve: pd.DataFrame


def _max_drawdown(equity_curve: pd.Series) -> float:
    peak = equity_curve.cummax()
    drawdown = (equity_curve / peak) - 1.0
    return float(drawdown.min()) if not drawdown.empty else 0.0


def _build_summary(df: pd.DataFrame, trades: list[float]) -> dict[str, float]:
    total_return = float(df["strategy_curve"].iloc[-1] - 1.0)
    buy_hold_return = float(df["buy_hold_curve"].iloc[-1] - 1.0)

    periods = len(df)
    annualized_return = float((1.0 + total_return) ** (252 / periods) - 1.0) if periods > 0 else 0.0

    ret_mean = float(df["strategy_ret"].mean())
    ret_std = float(df["strategy_ret"].std())
    sharpe = float(np.sqrt(252) * ret_mean / ret_std) if ret_std > 0 else 0.0

    num_trades = len(trades)
    win_rate = float(sum(1 for t in trades if t > 0) / num_trades) if num_trades > 0 else 0.0
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    profit_factor = float(sum(wins) / abs(sum(losses))) if losses and abs(sum(losses)) > 0 else 0.0

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "buy_and_hold_return": buy_hold_return,
        "max_drawdown": _max_drawdown(df["strategy_curve"]),
        "sharpe_ratio": sharpe,
        "num_trades": float(num_trades),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
    }


def run_signal_backtest(
    data: pd.DataFrame,
    strategy_df: pd.DataFrame,
    strategy_family: str,
    long_entry_col: str = "long_entry",
    short_entry_col: str = "short_entry",
    atr_length: int = 14,
    atr_stop_enabled: bool = False,
    atr_stop_multiple: float = 2.0,
    atr_trailing_enabled: bool = False,
    atr_trailing_multiple: float = 2.5,
) -> BacktestResult:
    """Backtest using strategy signal columns and optional ATR stop logic."""
    if data.empty or strategy_df.empty:
        return BacktestResult(summary={}, curve=pd.DataFrame())

    df = strategy_df.copy()
    df["ret"] = data["Close"].pct_change().fillna(0.0)
    df["atr"] = compute_atr(data, length=atr_length)

    positions = np.zeros(len(df), dtype=float)
    strategy_rets = np.zeros(len(df), dtype=float)

    position = 0
    trades: list[float] = []
    open_trade: dict[str, float] | None = None
    trailing_stop: float | None = None

    for i in range(1, len(df)):
        sig_row = df.iloc[i - 1]
        sig_close = float(sig_row["Close"])
        sig_atr = float(sig_row.get("atr", float("nan")))

        long_signal = bool(sig_row.get(long_entry_col, False))
        short_signal = bool(sig_row.get(short_entry_col, False))

        if open_trade is not None and (atr_stop_enabled or atr_trailing_enabled) and not np.isnan(sig_atr):
            if position == 1:
                if trailing_stop is None:
                    trailing_stop = open_trade["entry_price"] - atr_stop_multiple * sig_atr
                if atr_trailing_enabled:
                    trailing_stop = max(trailing_stop, sig_close - atr_trailing_multiple * sig_atr)
                if sig_close <= trailing_stop:
                    pnl = (sig_close - open_trade["entry_price"]) / open_trade["entry_price"]
                    trades.append(float(pnl))
                    position = 0
                    open_trade = None
                    trailing_stop = None

            elif position == -1:
                if trailing_stop is None:
                    trailing_stop = open_trade["entry_price"] + atr_stop_multiple * sig_atr
                if atr_trailing_enabled:
                    trailing_stop = min(trailing_stop, sig_close + atr_trailing_multiple * sig_atr)
                if sig_close >= trailing_stop:
                    pnl = (open_trade["entry_price"] - sig_close) / open_trade["entry_price"]
                    trades.append(float(pnl))
                    position = 0
                    open_trade = None
                    trailing_stop = None

        if strategy_family != "aberration":
            raise ValueError(f"Unsupported strategy_family: {strategy_family}")

        long_exit = bool(sig_row.get("long_exit", False))
        short_exit = bool(sig_row.get("short_exit", False))

        if position == 0:
            if long_signal:
                position = 1
                open_trade = {"entry_price": sig_close}
                trailing_stop = None
            elif short_signal:
                position = -1
                open_trade = {"entry_price": sig_close}
                trailing_stop = None
        elif position == 1 and long_exit:
            pnl = (sig_close - open_trade["entry_price"]) / open_trade["entry_price"]
            trades.append(float(pnl))
            position = 0
            open_trade = None
            trailing_stop = None
        elif position == -1 and short_exit:
            pnl = (open_trade["entry_price"] - sig_close) / open_trade["entry_price"]
            trades.append(float(pnl))
            position = 0
            open_trade = None
            trailing_stop = None

        positions[i] = position
        strategy_rets[i] = position * float(df.iloc[i]["ret"])

    df["position"] = positions
    df["strategy_ret"] = strategy_rets
    df["strategy_curve"] = (1.0 + df["strategy_ret"]).cumprod()
    df["buy_hold_curve"] = (1.0 + df["ret"]).cumprod()

    summary = _build_summary(df=df, trades=trades)
    curve = df[["Close", "strategy_curve", "buy_hold_curve", "position"]].copy()
    return BacktestResult(summary=summary, curve=curve)


def run_aberration_backtest(
    data: pd.DataFrame,
    length: int = 35,
    multiplier: float = 2.0,
    atr_length: int = 14,
    atr_stop_enabled: bool = False,
    atr_stop_multiple: float = 2.0,
    atr_trailing_enabled: bool = False,
    atr_trailing_multiple: float = 2.5,
    apply_filters: bool = False,
    filter_settings=None,
) -> BacktestResult:
    """Backtest Aberration with optional filter-gated entries and ATR risk rules."""
    if data.empty:
        return BacktestResult(summary={}, curve=pd.DataFrame())

    frame = apply_aberration_strategy(data, length=length, multiplier=multiplier)
    long_col = "long_entry"
    short_col = "short_entry"

    if apply_filters:
        if filter_settings is None:
            raise ValueError("filter_settings is required when apply_filters=True")
        frame = apply_entry_filters(frame, config=filter_settings)
        long_col = "long_entry_filtered"
        short_col = "short_entry_filtered"

    return run_signal_backtest(
        data=data,
        strategy_df=frame,
        strategy_family="aberration",
        long_entry_col=long_col,
        short_entry_col=short_col,
        atr_length=atr_length,
        atr_stop_enabled=atr_stop_enabled,
        atr_stop_multiple=atr_stop_multiple,
        atr_trailing_enabled=atr_trailing_enabled,
        atr_trailing_multiple=atr_trailing_multiple,
    )


def run_backtest(
    data: pd.DataFrame,
    bollinger_length: int = 35,
    bollinger_multiplier: float = 2.0,
    atr_length: int = 14,
    atr_stop_enabled: bool = False,
    atr_stop_multiple: float = 2.0,
    atr_trailing_enabled: bool = False,
    atr_trailing_multiple: float = 2.5,
    apply_filters: bool = False,
    filter_settings=None,
) -> BacktestResult:
    """Run an Aberration backtest with optional filters and ATR risk rules."""
    return run_aberration_backtest(
        data=data,
        length=bollinger_length,
        multiplier=bollinger_multiplier,
        atr_length=atr_length,
        atr_stop_enabled=atr_stop_enabled,
        atr_stop_multiple=atr_stop_multiple,
        atr_trailing_enabled=atr_trailing_enabled,
        atr_trailing_multiple=atr_trailing_multiple,
        apply_filters=apply_filters,
        filter_settings=filter_settings,
    )
