"""Central Aberration strategy calculation pipeline."""

from __future__ import annotations

import pandas as pd

from src.strategy.indicators import bollinger_bands
from src.strategy.signals import cross_above, cross_below


def apply_aberration_strategy(
    df: pd.DataFrame,
    length: int = 35,
    multiplier: float = 2.0,
) -> pd.DataFrame:
    """Apply Aberration strategy logic on OHLCV data.

    Args:
        df: DataFrame with at least a `Close` column.
        length: Bollinger moving average length.
        multiplier: Bollinger standard deviation multiplier.

    Returns:
        DataFrame containing close, bands, and signal columns.
    """
    if "Close" not in df.columns:
        raise ValueError("Input DataFrame must contain a 'Close' column.")

    out = df.copy()
    close = out["Close"]

    middle, upper, lower = bollinger_bands(close=close, length=length, multiplier=multiplier)

    out["middle_band"] = middle
    out["upper_band"] = upper
    out["lower_band"] = lower

    out["long_entry"] = cross_above(close, out["upper_band"])
    out["short_entry"] = cross_below(close, out["lower_band"])
    out["long_exit"] = cross_below(close, out["middle_band"])
    out["short_exit"] = cross_above(close, out["middle_band"])

    # Early rows without full indicator history cannot produce valid signals.
    warmup = out["middle_band"].isna()
    signal_cols = ["long_entry", "short_entry", "long_exit", "short_exit"]
    out.loc[warmup, signal_cols] = False

    return out
