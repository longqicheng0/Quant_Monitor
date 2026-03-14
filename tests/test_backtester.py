import numpy as np
import pandas as pd

from config.settings import FilterSettings
from src.backtest.backtester import run_aberration_backtest, run_backtest


def _sample_df(seed: int = 42, n: int = 320) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prices = 100 + np.cumsum(rng.normal(0, 1, n))
    idx = pd.date_range("2020-01-01", periods=len(prices), freq="D")
    return pd.DataFrame(
        {
            "Open": prices,
            "High": prices + 1,
            "Low": prices - 1,
            "Close": prices,
            "Adj Close": prices,
            "Volume": 1_000_000,
        },
        index=idx,
    )


def test_backtest_runs_and_returns_metrics():
    result = run_aberration_backtest(_sample_df(), length=35, multiplier=2.0)
    assert "total_return" in result.summary
    assert "max_drawdown" in result.summary
    assert "strategy_curve" in result.curve.columns
    assert "buy_hold_curve" in result.curve.columns


def test_filtered_backtest_dispatch_runs():
    result = run_backtest(
        data=_sample_df(seed=7),
        bollinger_length=35,
        bollinger_multiplier=2.0,
        apply_filters=True,
        filter_settings=FilterSettings(
            trend_filter_enabled=True,
            adx_filter_enabled=False,
            volume_filter_enabled=False,
            overextension_filter_enabled=False,
        ),
    )
    assert "total_return" in result.summary
    assert "sharpe_ratio" in result.summary
    assert "position" in result.curve.columns
