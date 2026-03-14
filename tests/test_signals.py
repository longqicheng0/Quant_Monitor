import pandas as pd

from src.strategy.signals import classify_latest_signal, cross_above, cross_below


def test_cross_above_strict_rule():
    price = pd.Series([9.0, 10.0, 10.5])
    line = pd.Series([10.0, 10.0, 10.0])
    out = cross_above(price, line)
    assert bool(out.iloc[1]) is False
    assert bool(out.iloc[2]) is True


def test_cross_below_strict_rule():
    price = pd.Series([11.0, 10.0, 9.5])
    line = pd.Series([10.0, 10.0, 10.0])
    out = cross_below(price, line)
    assert bool(out.iloc[1]) is False
    assert bool(out.iloc[2]) is True


def test_aberration_entry_classification():
    df = pd.DataFrame(
        {
            "long_entry": [False, True],
            "short_entry": [False, False],
            "long_exit": [False, False],
            "short_exit": [False, False],
        }
    )
    signal, state = classify_latest_signal(df, current_state="flat")
    assert signal == "LONG_ENTRY"
    assert state == "long"


def test_aberration_exit_classification():
    df = pd.DataFrame(
        {
            "long_entry": [False, False],
            "short_entry": [False, False],
            "long_exit": [False, True],
            "short_exit": [False, False],
        }
    )
    signal, state = classify_latest_signal(df, current_state="long")
    assert signal == "LONG_EXIT"
    assert state == "flat"
