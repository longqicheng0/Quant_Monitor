import pandas as pd

from src.strategy.signals import cross_above, cross_below


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
