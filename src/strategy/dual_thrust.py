"""Dual Thrust strategy calculations.

This daily implementation computes trigger levels using only previously
completed bars. It is designed so an intraday extension can later reuse the
same precomputed daily range and open-based trigger levels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.signals import cross_above, cross_below


def _compute_bias(long_entry: pd.Series, short_entry: pd.Series) -> pd.Series:
    """Build running position bias from entry signals with flip behavior."""
    state = "flat"
    values: list[str] = []

    for is_long, is_short in zip(long_entry.fillna(False), short_entry.fillna(False)):
        if state == "flat":
            if bool(is_long):
                state = "long"
            elif bool(is_short):
                state = "short"
        elif state == "long" and bool(is_short):
            state = "short"
        elif state == "short" and bool(is_long):
            state = "long"
        values.append(state)

    return pd.Series(values, index=long_entry.index, name="current_bias")


def apply_dual_thrust_strategy(
    df: pd.DataFrame,
    lookback: int = 20,
    multiplier: float = 1.5,
) -> pd.DataFrame:
    """Apply Dual Thrust strategy.

    Definitions:
    - HH: highest high over previous N completed days
    - LL: lowest low over previous N completed days
    - HC: highest close over previous N completed days
    - LC: lowest close over previous N completed days
    - range_value: max(HH - LC, HC - LL)
    - upper_trigger: today_open + K * range_value
    - lower_trigger: today_open - K * range_value
    """
    required = {"Open", "High", "Low", "Close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Input DataFrame missing required columns: {sorted(missing)}")

    out = df.copy()

    prev_high = out["High"].shift(1)
    prev_low = out["Low"].shift(1)
    prev_close = out["Close"].shift(1)

    out["HH"] = prev_high.rolling(window=lookback, min_periods=lookback).max()
    out["LL"] = prev_low.rolling(window=lookback, min_periods=lookback).min()
    out["HC"] = prev_close.rolling(window=lookback, min_periods=lookback).max()
    out["LC"] = prev_close.rolling(window=lookback, min_periods=lookback).min()

    out["range_value"] = np.maximum(out["HH"] - out["LC"], out["HC"] - out["LL"])
    out["upper_trigger"] = out["Open"] + multiplier * out["range_value"]
    out["lower_trigger"] = out["Open"] - multiplier * out["range_value"]

    out["long_entry"] = cross_above(out["Close"], out["upper_trigger"])
    out["short_entry"] = cross_below(out["Close"], out["lower_trigger"])

    # These columns indicate opposite-side exits when an immediate flip occurs.
    out["long_exit_on_flip"] = out["short_entry"]
    out["short_exit_on_flip"] = out["long_entry"]

    warmup = out["range_value"].isna()
    signal_cols = ["long_entry", "short_entry", "long_exit_on_flip", "short_exit_on_flip"]
    out.loc[warmup, signal_cols] = False

    out["current_bias"] = _compute_bias(out["long_entry"], out["short_entry"])
    return out
