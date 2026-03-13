"""Simple backtester for supported monitoring strategies."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.strategy.aberration import apply_aberration_strategy
from src.strategy.dual_thrust import apply_dual_thrust_strategy


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

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "buy_and_hold_return": buy_hold_return,
        "max_drawdown": _max_drawdown(df["strategy_curve"]),
        "sharpe_ratio": sharpe,
        "num_trades": float(num_trades),
        "win_rate": win_rate,
    }


def run_aberration_backtest(
    data: pd.DataFrame,
    length: int = 35,
    multiplier: float = 2.0,
) -> BacktestResult:
    """Backtest Aberration with one active position at a time.

    Position values:
    - 0 = flat
    - 1 = long
    - -1 = short
    """
    if data.empty:
        return BacktestResult(summary={}, curve=pd.DataFrame())

    df = apply_aberration_strategy(data, length=length, multiplier=multiplier).copy()
    df["ret"] = df["Close"].pct_change().fillna(0.0)

    positions = np.zeros(len(df), dtype=float)
    strategy_rets = np.zeros(len(df), dtype=float)

    position = 0
    trades = []
    open_trade = None

    for i in range(1, len(df)):
        sig_row = df.iloc[i - 1]
        sig_time = df.index[i - 1]
        sig_close = float(sig_row["Close"])

        if position == 0:
            if bool(sig_row["long_entry"]):
                position = 1
                open_trade = {"side": "long", "entry_price": sig_close, "entry_time": sig_time}
            elif bool(sig_row["short_entry"]):
                position = -1
                open_trade = {"side": "short", "entry_price": sig_close, "entry_time": sig_time}
        elif position == 1 and bool(sig_row["long_exit"]):
            if open_trade:
                pnl = (sig_close - open_trade["entry_price"]) / open_trade["entry_price"]
                trades.append(float(pnl))
            position = 0
            open_trade = None
        elif position == -1 and bool(sig_row["short_exit"]):
            if open_trade:
                pnl = (open_trade["entry_price"] - sig_close) / open_trade["entry_price"]
                trades.append(float(pnl))
            position = 0
            open_trade = None

        positions[i] = position
        strategy_rets[i] = position * float(df.iloc[i]["ret"])

    df["position"] = positions
    df["strategy_ret"] = strategy_rets
    df["strategy_curve"] = (1.0 + df["strategy_ret"]).cumprod()
    df["buy_hold_curve"] = (1.0 + df["ret"]).cumprod()

    summary = _build_summary(df=df, trades=trades)

    curve = df[["Close", "strategy_curve", "buy_hold_curve", "position"]].copy()
    return BacktestResult(summary=summary, curve=curve)


def run_dual_thrust_backtest(
    data: pd.DataFrame,
    lookback: int = 20,
    multiplier: float = 1.5,
) -> BacktestResult:
    """Backtest Dual Thrust with one position and opposite-signal flips."""
    if data.empty:
        return BacktestResult(summary={}, curve=pd.DataFrame())

    df = apply_dual_thrust_strategy(data, lookback=lookback, multiplier=multiplier).copy()
    df["ret"] = df["Close"].pct_change().fillna(0.0)

    positions = np.zeros(len(df), dtype=float)
    strategy_rets = np.zeros(len(df), dtype=float)

    position = 0
    trades = []
    open_trade = None

    for i in range(1, len(df)):
        sig_row = df.iloc[i - 1]
        sig_time = df.index[i - 1]
        sig_close = float(sig_row["Close"])

        long_signal = bool(sig_row.get("long_entry", False))
        short_signal = bool(sig_row.get("short_entry", False))

        if position == 0:
            if long_signal:
                position = 1
                open_trade = {"side": "long", "entry_price": sig_close, "entry_time": sig_time}
            elif short_signal:
                position = -1
                open_trade = {"side": "short", "entry_price": sig_close, "entry_time": sig_time}

        elif position == 1 and short_signal:
            if open_trade:
                pnl = (sig_close - open_trade["entry_price"]) / open_trade["entry_price"]
                trades.append(float(pnl))
            position = -1
            open_trade = {"side": "short", "entry_price": sig_close, "entry_time": sig_time}

        elif position == -1 and long_signal:
            if open_trade:
                pnl = (open_trade["entry_price"] - sig_close) / open_trade["entry_price"]
                trades.append(float(pnl))
            position = 1
            open_trade = {"side": "long", "entry_price": sig_close, "entry_time": sig_time}

        positions[i] = position
        strategy_rets[i] = position * float(df.iloc[i]["ret"])

    df["position"] = positions
    df["strategy_ret"] = strategy_rets
    df["strategy_curve"] = (1.0 + df["strategy_ret"]).cumprod()
    df["buy_hold_curve"] = (1.0 + df["ret"]).cumprod()

    summary = _build_summary(df=df, trades=trades)

    curve = df[["Close", "strategy_curve", "buy_hold_curve", "position"]].copy()
    return BacktestResult(summary=summary, curve=curve)


def run_backtest(
    strategy_name: str,
    data: pd.DataFrame,
    bollinger_length: int = 35,
    bollinger_multiplier: float = 2.0,
    dual_thrust_lookback: int = 20,
    dual_thrust_multiplier: float = 1.5,
) -> BacktestResult:
    """Dispatch backtest run by strategy name."""
    name = strategy_name.lower()

    if name == "aberration":
        return run_aberration_backtest(data, length=bollinger_length, multiplier=bollinger_multiplier)

    if name == "dual_thrust":
        return run_dual_thrust_backtest(data, lookback=dual_thrust_lookback, multiplier=dual_thrust_multiplier)

    raise ValueError(f"Unsupported strategy_name: {strategy_name}")
