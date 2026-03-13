"""Application settings models for the strategy monitor."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StrategySettings(BaseModel):
    """Strategy selection and parameters."""

    strategy_name: str = Field(default="aberration")

    bollinger_length: int = Field(default=35, ge=2)
    bollinger_multiplier: float = Field(default=2.0, gt=0)

    dual_thrust_lookback: int = Field(default=20, ge=2)
    dual_thrust_multiplier: float = Field(default=1.5, gt=0)


class MonitorSettings(BaseModel):
    """Settings related to market scanning behavior."""

    tickers: list[str] = Field(default_factory=lambda: ["SPY", "QQQ", "IWM"])
    timeframe: str = "1d"
    history_period: str = "1y"
    scan_interval_seconds: int = Field(default=60, ge=5)


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


class AppSettings(BaseModel):
    """Top-level settings container."""

    strategy: StrategySettings = Field(default_factory=StrategySettings)
    monitor: MonitorSettings = Field(default_factory=MonitorSettings)
    alerts: AlertSettings = Field(default_factory=AlertSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    backtest: BacktestSettings = Field(default_factory=BacktestSettings)


DEFAULT_SETTINGS = AppSettings()