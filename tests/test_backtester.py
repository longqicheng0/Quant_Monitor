import numpy as np
import pandas as pd

from src.backtest.backtester import run_aberration_backtest


def test_backtest_runs_and_returns_metrics():
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.normal(0, 1, 300))
    idx = pd.date_range("2020-01-01", periods=len(prices), freq="D")
    df = pd.DataFrame(
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

    result = run_aberration_backtest(df, length=35, multiplier=2.0)
    assert "total_return" in result.summary
    assert "max_drawdown" in result.summary
    assert "strategy_curve" in result.curve.columns
    assert "buy_hold_curve" in result.curve.columns
