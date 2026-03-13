import pandas as pd

from src.strategy.signals import classify_latest_signal_for_strategy, cross_above, cross_below


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


def test_dual_thrust_flip_classification():
    df = pd.DataFrame(
        {
            "long_entry": [False, True],
            "short_entry": [False, False],
        }
    )
    signal, state = classify_latest_signal_for_strategy(df, strategy_name="dual_thrust", current_state="short")
    assert signal == "SHORT_EXIT_ON_FLIP_TO_LONG"
    assert state == "long"


def test_aberration_classification_unchanged():
    df = pd.DataFrame(
        {
            "long_entry": [False, False],
            "short_entry": [False, False],
            "long_exit": [False, True],
            "short_exit": [False, False],
        }
    )
    signal, state = classify_latest_signal_for_strategy(df, strategy_name="aberration", current_state="long")
    assert signal == "LONG_EXIT"
    assert state == "flat"
