import numpy as np
import pandas as pd

from config.settings import AppSettings
from src.research.experiment_runner import run_strategy_experiments


class _FakeClient:
    def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y") -> pd.DataFrame:
        n = 320
        idx = pd.date_range("2021-01-01", periods=n, freq="D")
        base = 100 + np.cumsum(np.random.default_rng(abs(hash(ticker)) % 12345).normal(0, 1, n))
        return pd.DataFrame(
            {
                "Open": base + 0.1,
                "High": base + 1.0,
                "Low": base - 1.0,
                "Close": base,
                "Volume": np.full(n, 1_000_000),
            },
            index=idx,
        )


def test_experiment_runner_output_structure(monkeypatch):
    settings = AppSettings()
    settings.experiment.experiment_tickers = ["AAPL", "MSFT"]
    settings.experiment.interval = "1d"
    settings.experiment.period = "1y"

    monkeypatch.setattr("src.research.experiment_runner.YFinanceClient", _FakeClient)
    artifacts = run_strategy_experiments(settings, strategy_family="aberration", output_prefix="test_experiment")

    assert not artifacts.results_df.empty
    assert {"ticker", "strategy_variant", "total_return"}.issubset(set(artifacts.results_df.columns))
    assert set(artifacts.results_df["strategy_variant"]) == {"baseline_aberration", "filtered_aberration"}
    assert "mean_total_return" in artifacts.aggregate_df.columns
