"""Signal helpers for strict crossover event detection."""

from __future__ import annotations

import pandas as pd


def cross_above(price: pd.Series, line: pd.Series) -> pd.Series:
    """Return True where price crosses above line.

    Rule: previous price <= previous line AND current price > current line
    """
    prev_price = price.shift(1)
    prev_line = line.shift(1)
    return (prev_price <= prev_line) & (price > line)


def cross_below(price: pd.Series, line: pd.Series) -> pd.Series:
    """Return True where price crosses below line.

    Rule: previous price >= previous line AND current price < current line
    """
    prev_price = price.shift(1)
    prev_line = line.shift(1)
    return (prev_price >= prev_line) & (price < line)


def classify_latest_signal(df: pd.DataFrame, current_state: str = "flat") -> tuple[str, str]:
    """Classify latest signal using strategy booleans and position state.

    Args:
        df: DataFrame containing long_entry, short_entry, long_exit, short_exit.
        current_state: One of "flat", "long", "short".

    Returns:
        (signal_name, next_state)
    """
    if df.empty:
        return "NO_DATA", current_state

    return classify_latest_signal_for_strategy(df=df, strategy_name="aberration", current_state=current_state)


def classify_latest_signal_for_strategy(
    df: pd.DataFrame,
    strategy_name: str,
    current_state: str = "flat",
) -> tuple[str, str]:
    """Classify the latest signal for a specific strategy.

    Args:
        df: Strategy output DataFrame.
        strategy_name: aberration or dual_thrust.
        current_state: One of flat, long, short.

    Returns:
        (signal_name, next_state)
    """
    if df.empty:
        return "NO_DATA", current_state

    row = df.iloc[-1]
    signal = "NO_SIGNAL"
    next_state = current_state
    strategy = strategy_name.lower()

    if strategy == "aberration":
        if current_state == "flat":
            if bool(row.get("long_entry", False)):
                signal = "LONG_ENTRY"
                next_state = "long"
            elif bool(row.get("short_entry", False)):
                signal = "SHORT_ENTRY"
                next_state = "short"
        elif current_state == "long" and bool(row.get("long_exit", False)):
            signal = "LONG_EXIT"
            next_state = "flat"
        elif current_state == "short" and bool(row.get("short_exit", False)):
            signal = "SHORT_EXIT"
            next_state = "flat"

        return signal, next_state

    if strategy == "dual_thrust":
        long_entry = bool(row.get("long_entry", False))
        short_entry = bool(row.get("short_entry", False))

        if current_state == "flat":
            if long_entry:
                return "LONG_ENTRY", "long"
            if short_entry:
                return "SHORT_ENTRY", "short"
            return "NO_SIGNAL", "flat"

        if current_state == "long":
            if short_entry:
                return "LONG_EXIT_ON_FLIP_TO_SHORT", "short"
            return "NO_SIGNAL", "long"

        if current_state == "short":
            if long_entry:
                return "SHORT_EXIT_ON_FLIP_TO_LONG", "long"
            return "NO_SIGNAL", "short"

        return "NO_SIGNAL", current_state

    raise ValueError(f"Unsupported strategy_name: {strategy_name}")
