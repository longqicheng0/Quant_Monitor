"""Helpers to build research config from app settings."""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import AppSettings


@dataclass
class ExperimentRunConfig:
    """Frozen runtime view of experiment settings."""

    tickers: list[str]
    benchmark_ticker: str | None
    interval: str
    period: str

    trend_filter_enabled: bool
    trend_ma_length: int
    adx_filter_enabled: bool
    adx_threshold: float
    adx_length: int
    volume_filter_enabled: bool
    volume_ma_length: int
    overextension_filter_enabled: bool
    max_body_atr_multiple: float
    atr_length: int
    atr_stop_enabled: bool
    atr_stop_multiple: float
    atr_trailing_enabled: bool
    atr_trailing_multiple: float


def build_experiment_run_config(settings: AppSettings) -> ExperimentRunConfig:
    exp = settings.experiment
    return ExperimentRunConfig(
        tickers=list(exp.experiment_tickers),
        benchmark_ticker=exp.benchmark_ticker,
        interval=exp.interval,
        period=exp.period,
        trend_filter_enabled=exp.trend_filter_enabled,
        trend_ma_length=exp.trend_ma_length,
        adx_filter_enabled=exp.adx_filter_enabled,
        adx_threshold=exp.adx_threshold,
        adx_length=exp.adx_length,
        volume_filter_enabled=exp.volume_filter_enabled,
        volume_ma_length=exp.volume_ma_length,
        overextension_filter_enabled=exp.overextension_filter_enabled,
        max_body_atr_multiple=exp.max_body_atr_multiple,
        atr_length=exp.atr_length,
        atr_stop_enabled=exp.atr_stop_enabled,
        atr_stop_multiple=exp.atr_stop_multiple,
        atr_trailing_enabled=exp.atr_trailing_enabled,
        atr_trailing_multiple=exp.atr_trailing_multiple,
    )
