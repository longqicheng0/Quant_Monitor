import numpy as np
import pandas as pd

from src.strategy.indicators import bollinger_bands, rolling_std, sma


def test_sma_length_and_values():
    series = pd.Series([1, 2, 3, 4, 5])
    out = sma(series, 3)
    assert np.isnan(out.iloc[0])
    assert np.isnan(out.iloc[1])
    assert out.iloc[2] == 2
    assert out.iloc[4] == 4


def test_rolling_std_basic():
    series = pd.Series([1, 2, 3, 4, 5])
    out = rolling_std(series, 3)
    assert np.isnan(out.iloc[0])
    assert np.isnan(out.iloc[1])
    assert out.iloc[2] > 0


def test_bollinger_bands_output_shapes():
    close = pd.Series(np.arange(1, 50))
    middle, upper, lower = bollinger_bands(close, length=35, multiplier=2.0)
    assert len(middle) == len(close)
    assert len(upper) == len(close)
    assert len(lower) == len(close)
    valid_idx = middle.dropna().index[0]
    assert upper.loc[valid_idx] >= middle.loc[valid_idx]
    assert lower.loc[valid_idx] <= middle.loc[valid_idx]
