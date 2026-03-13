import numpy as np
import pandas as pd

from src.strategy.dual_thrust import apply_dual_thrust_strategy


def _sample_df() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=30, freq="D")
    base = np.linspace(100, 120, 30)
    return pd.DataFrame(
        {
            "Open": base + 0.5,
            "High": base + 1.5,
            "Low": base - 1.5,
            "Close": base,
            "Adj Close": base,
            "Volume": 1_000_000,
        },
        index=idx,
    )


def test_dual_thrust_columns_exist():
    out = apply_dual_thrust_strategy(_sample_df(), lookback=20, multiplier=1.5)
    required = {
        "HH",
        "LL",
        "HC",
        "LC",
        "range_value",
        "upper_trigger",
        "lower_trigger",
        "long_entry",
        "short_entry",
        "long_exit_on_flip",
        "short_exit_on_flip",
        "current_bias",
    }
    assert required.issubset(set(out.columns))


def test_dual_thrust_no_lookahead_in_range():
    df = _sample_df()
    out = apply_dual_thrust_strategy(df, lookback=20, multiplier=1.5)

    check_idx = out.index[25]
    previous_window = df.loc[out.index[5]:out.index[24]]

    expected_hh = previous_window["High"].max()
    expected_ll = previous_window["Low"].min()
    expected_hc = previous_window["Close"].max()
    expected_lc = previous_window["Close"].min()
    expected_range = max(expected_hh - expected_lc, expected_hc - expected_ll)

    assert np.isclose(out.loc[check_idx, "HH"], expected_hh)
    assert np.isclose(out.loc[check_idx, "LL"], expected_ll)
    assert np.isclose(out.loc[check_idx, "HC"], expected_hc)
    assert np.isclose(out.loc[check_idx, "LC"], expected_lc)
    assert np.isclose(out.loc[check_idx, "range_value"], expected_range)


def test_dual_thrust_trigger_formula():
    df = _sample_df()
    out = apply_dual_thrust_strategy(df, lookback=20, multiplier=1.5)

    row = out.iloc[25]
    assert np.isclose(row["upper_trigger"], row["Open"] + 1.5 * row["range_value"])
    assert np.isclose(row["lower_trigger"], row["Open"] - 1.5 * row["range_value"])
