"""Reusable entry filters for constrained Aberration experiments."""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import FilterSettings


def compute_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Average true range using rolling mean."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=length, min_periods=length).mean()


def compute_adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Compute ADX from OHLC data with Wilder-style smoothing via rolling means.

    This implementation is designed for readability and stable daily research,
    not micro-optimized speed.
    """
    high = df["High"]
    low = df["Low"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    atr = compute_atr(df, length=length)
    plus_di = 100.0 * (plus_dm.rolling(window=length, min_periods=length).mean() / atr)
    minus_di = 100.0 * (minus_dm.rolling(window=length, min_periods=length).mean() / atr)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.rolling(window=length, min_periods=length).mean()


def passes_trend_filter(df: pd.DataFrame, ma_length: int = 200) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (long_pass, short_pass, trend_ma)."""
    trend_ma = df["Close"].rolling(window=ma_length, min_periods=ma_length).mean()
    long_pass = df["Close"] > trend_ma
    short_pass = df["Close"] < trend_ma
    return long_pass.fillna(False), short_pass.fillna(False), trend_ma


def passes_adx_filter(df: pd.DataFrame, threshold: float = 20.0, length: int = 14) -> tuple[pd.Series, pd.Series]:
    """Return (pass_mask, adx_series)."""
    adx = compute_adx(df, length=length)
    return (adx > threshold).fillna(False), adx


def passes_volume_filter(df: pd.DataFrame, length: int = 20) -> tuple[pd.Series, pd.Series]:
    """Return (pass_mask, volume_ma). Missing volume gracefully passes filter."""
    if "Volume" not in df.columns:
        true_mask = pd.Series(True, index=df.index)
        return true_mask, pd.Series(np.nan, index=df.index)

    volume = df["Volume"]
    volume_ma = volume.rolling(window=length, min_periods=length).mean()

    # If volume data is missing on a row, do not block entries by default.
    pass_mask = (volume > volume_ma) | volume.isna() | volume_ma.isna()
    return pass_mask.fillna(True), volume_ma


def passes_overextension_filter(
    df: pd.DataFrame,
    atr: pd.Series,
    max_body_atr_multiple: float = 1.8,
) -> tuple[pd.Series, pd.Series]:
    """Return (pass_mask, body_size)."""
    body_size = (df["Close"] - df["Open"]).abs()
    pass_mask = body_size <= (max_body_atr_multiple * atr)
    return pass_mask.fillna(False), body_size


def apply_entry_filters(
    base_df: pd.DataFrame,
    config: FilterSettings,
    long_col: str = "long_entry",
    short_col: str = "short_entry",
) -> pd.DataFrame:
    """Apply configured filters and create filtered entry columns.

    Adds:
    - trend_ma_*
    - adx_*
    - volume_ma_*
    - atr_*
    - body_size_*
    - long_entry_filtered
    - short_entry_filtered
    """
    df = base_df.copy()

    atr = compute_atr(df, length=config.atr_length)
    df["atr"] = atr

    long_gate = pd.Series(True, index=df.index)
    short_gate = pd.Series(True, index=df.index)

    if config.trend_filter_enabled:
        long_pass, short_pass, trend_ma = passes_trend_filter(df, ma_length=config.trend_ma_length)
        df["trend_ma"] = trend_ma
        df["trend_long_pass"] = long_pass
        df["trend_short_pass"] = short_pass
        long_gate &= long_pass
        short_gate &= short_pass

    if config.adx_filter_enabled:
        adx_pass, adx = passes_adx_filter(df, threshold=config.adx_threshold, length=config.adx_length)
        df["adx"] = adx
        df["adx_pass"] = adx_pass
        long_gate &= adx_pass
        short_gate &= adx_pass

    if config.volume_filter_enabled:
        vol_pass, volume_ma = passes_volume_filter(df, length=config.volume_ma_length)
        df["volume_ma"] = volume_ma
        df["volume_pass"] = vol_pass
        long_gate &= vol_pass
        short_gate &= vol_pass

    if config.overextension_filter_enabled:
        overext_pass, body_size = passes_overextension_filter(
            df,
            atr=atr,
            max_body_atr_multiple=config.max_body_atr_multiple,
        )
        df["body_size"] = body_size
        df["overextension_pass"] = overext_pass
        long_gate &= overext_pass
        short_gate &= overext_pass

    df["long_entry_filtered"] = df[long_col].fillna(False) & long_gate.fillna(False)
    df["short_entry_filtered"] = df[short_col].fillna(False) & short_gate.fillna(False)
    return df
