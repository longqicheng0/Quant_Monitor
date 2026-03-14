"""Application settings models for the Aberration strategy monitor."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StrategySettings(BaseModel):
    """Aberration strategy parameters."""

    bollinger_length: int = Field(default=35, ge=2)
    bollinger_multiplier: float = Field(default=2.0, gt=0)


class MonitorSettings(BaseModel):
    """Settings related to market scanning behavior."""

    tickers: list[str] = Field(
        default_factory=lambda: ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "NFLX"]
    )
    interval: str = "1d"
    period: str = "1y"
    scan_interval_seconds: int = Field(default=60, ge=5)


class FilterSettings(BaseModel):
    """Decision and research filters used around Aberration entries."""

    trend_filter_enabled: bool = True
    trend_ma_length: int = Field(default=200, ge=20)

    adx_filter_enabled: bool = True
    adx_threshold: float = Field(default=25.0, ge=1.0)
    adx_length: int = Field(default=14, ge=2)

    volume_filter_enabled: bool = False
    volume_ma_length: int = Field(default=20, ge=2)

    overextension_filter_enabled: bool = True
    max_body_atr_multiple: float = Field(default=1.8, gt=0)

    atr_length: int = Field(default=14, ge=2)


class AlertSettings(BaseModel):
    """Settings for alert output channels."""

    enabled: bool = True
    console: bool = True
    webhook_url: Optional[str] = None


class LoggingSettings(BaseModel):
    """Settings for signal/event persistence."""

    enabled: bool = True
    csv_path: str = "data/logs/signals.csv"
    sqlite_path: str = "data/logs/signals.db"
    use_sqlite: bool = False


class BacktestSettings(BaseModel):
    """Historical backtest date and defaults."""

    enabled: bool = True
    default_ticker: str = "SPY"
    start_date: str = "2018-01-01"
    end_date: str = "2026-01-01"


class ExperimentSettings(BaseModel):
    """Settings for baseline vs filtered Aberration experiments."""

    experiment_enabled: bool = True
    experiment_tickers: list[str] = Field(
        default_factory=lambda: ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "NFLX"]
    )
    benchmark_ticker: Optional[str] = "SPY"
    interval: str = "1d"
    period: str = "5y"
    atr_stop_enabled: bool = False
    atr_stop_multiple: float = Field(default=2.0, gt=0)
    atr_trailing_enabled: bool = False
    atr_trailing_multiple: float = Field(default=2.5, gt=0)


class AppSettings(BaseModel):
    """Top-level settings container."""

    strategy: StrategySettings = Field(default_factory=StrategySettings)
    monitor: MonitorSettings = Field(default_factory=MonitorSettings)
    filters: FilterSettings = Field(default_factory=FilterSettings)
    alerts: AlertSettings = Field(default_factory=AlertSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    backtest: BacktestSettings = Field(default_factory=BacktestSettings)
    experiment: ExperimentSettings = Field(default_factory=ExperimentSettings)


DEFAULT_SETTINGS = AppSettings()