import numpy as np
import pandas as pd

from config.settings import FilterSettings
from src.research.decision_engine import build_daily_decision_report, evaluate_aberration_decision
from src.strategy.aberration import apply_aberration_strategy


def _sample_df(n: int = 260) -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    base = 100 + np.cumsum(np.random.default_rng(11).normal(0.15, 1.0, n))
    return pd.DataFrame(
        {
            "Open": base + 0.1,
            "High": base + 1.2,
            "Low": base - 1.2,
            "Close": base,
            "Volume": np.full(n, 1_000_000),
        },
        index=idx,
    )


def test_decision_engine_returns_valid_bucket():
    strategy_df = apply_aberration_strategy(_sample_df(), length=35, multiplier=2.0)
    result = evaluate_aberration_decision(
        ticker="QQQ",
        strategy_df=strategy_df,
        filter_settings=FilterSettings(
            trend_filter_enabled=True,
            adx_filter_enabled=False,
            volume_filter_enabled=False,
            overextension_filter_enabled=False,
        ),
    )
    assert result.decision in {"TRADE_TOMORROW", "WATCH_TOMORROW", "NO_TRADE"}
    assert result.bias in {"LONG", "SHORT", "NEUTRAL"}


class _FakeClient:
    def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y") -> pd.DataFrame:
        return _sample_df()


def test_daily_decision_report_shape():
    from config.settings import AppSettings

    settings = AppSettings()
    settings.monitor.tickers = ["QQQ", "NVDA"]
    report_df = build_daily_decision_report(settings, data_client=_FakeClient())
    assert list(report_df["ticker"]) == ["QQQ", "NVDA"]
    assert {"decision", "bias", "notes"}.issubset(report_df.columns)
