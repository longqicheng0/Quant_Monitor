"""Indicator functions used by the Aberration strategy."""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, length: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=length, min_periods=length).mean()


def rolling_std(series: pd.Series, length: int) -> pd.Series:
    """Rolling standard deviation.

    Uses pandas default sample standard deviation (ddof=1).
    """
    return series.rolling(window=length, min_periods=length).std()


def bollinger_bands(
    close: pd.Series,
    length: int = 35,
    multiplier: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger middle, upper, and lower bands."""
    middle = sma(close, length)
    std = rolling_std(close, length)
    upper = middle + multiplier * std
    lower = middle - multiplier * std
    return middle, upper, lower
