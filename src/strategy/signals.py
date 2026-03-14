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
    """Classify latest Aberration signal using position state."""
    if df.empty:
        return "NO_DATA", current_state

    row = df.iloc[-1]
    signal = "NO_SIGNAL"
    next_state = current_state

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
