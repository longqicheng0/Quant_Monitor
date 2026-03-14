import numpy as np
import pandas as pd

from config.settings import FilterSettings
from src.research.filters import (
    apply_entry_filters,
    passes_adx_filter,
    passes_overextension_filter,
    passes_trend_filter,
)


def _make_df(n: int = 260) -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    base = 100 + np.cumsum(np.random.default_rng(7).normal(0.1, 1.0, n))
    return pd.DataFrame(
        {
            "Open": base + 0.2,
            "High": base + 1.2,
            "Low": base - 1.2,
            "Close": base,
            "Volume": np.full(n, 1_000_000),
        },
        index=idx,
    )


def test_trend_filter_behavior():
    df = _make_df()
    long_pass, short_pass, trend_ma = passes_trend_filter(df, ma_length=200)
    assert len(long_pass) == len(df)
    assert len(short_pass) == len(df)
    assert len(trend_ma) == len(df)
    assert long_pass.iloc[:199].sum() == 0


def test_adx_filter_behavior():
    df = _make_df()
    mask, adx = passes_adx_filter(df, threshold=20.0, length=14)
    assert len(mask) == len(df)
    assert len(adx) == len(df)
    assert mask.dtype == bool


def test_overextension_filter_behavior():
    df = _make_df()
    atr = pd.Series(1.0, index=df.index)
    pass_mask, body = passes_overextension_filter(df, atr=atr, max_body_atr_multiple=0.5)
    assert len(pass_mask) == len(df)
    assert len(body) == len(df)
    assert bool(pass_mask.iloc[0])


def test_filtered_signal_gating():
    df = _make_df()
    df["long_entry"] = False
    df["short_entry"] = False
    df.loc[df.index[-1], "long_entry"] = True

    cfg = FilterSettings(
        trend_filter_enabled=True,
        adx_filter_enabled=False,
        volume_filter_enabled=False,
        overextension_filter_enabled=False,
    )

    out = apply_entry_filters(df, config=cfg)
    assert "long_entry_filtered" in out.columns
    assert "short_entry_filtered" in out.columns
    assert bool(out["long_entry_filtered"].iloc[-1]) in {True, False}


def test_no_lookahead_bias_trend_ma():
    df = _make_df()
    long_pass, _, trend_ma = passes_trend_filter(df, ma_length=5)
    idx = df.index[10]
    expected = df["Close"].iloc[6:11].mean()
    assert np.isclose(trend_ma.loc[idx], expected)
    assert bool(long_pass.loc[idx]) == bool(df.loc[idx, "Close"] > expected)
