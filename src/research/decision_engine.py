"""Daily decision engine for next-session Aberration decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from config.settings import AppSettings, FilterSettings
from src.datafeed.yfinance_client import YFinanceClient
from src.research.filters import apply_entry_filters
from src.strategy.aberration import apply_aberration_strategy
from src.strategy.signals import classify_latest_signal
from src.utils.time_utils import to_iso


@dataclass
class DecisionResult:
    ticker: str
    decision: str
    bias: str
    latest_signal: str
    close: float
    bar_time: str
    upper_band: float
    lower_band: float
    middle_band: float
    distance_to_upper_pct: float
    distance_to_lower_pct: float
    notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _safe_pct_distance(close: float, level: float) -> float:
    if close == 0:
        return 0.0
    return abs(close - level) / close


def _filter_notes(row: pd.Series, settings: FilterSettings) -> list[str]:
    notes: list[str] = []
    if settings.trend_filter_enabled:
        if bool(row.get("trend_long_pass", False)) or bool(row.get("trend_short_pass", False)):
            notes.append("trend aligned")
        else:
            notes.append("trend filter blocked")

    if settings.adx_filter_enabled:
        notes.append("adx confirmed" if bool(row.get("adx_pass", False)) else "adx weak")

    if settings.volume_filter_enabled:
        notes.append("volume confirmed" if bool(row.get("volume_pass", False)) else "volume filter blocked")

    if settings.overextension_filter_enabled:
        notes.append(
            "candle not overextended" if bool(row.get("overextension_pass", False)) else "candle overextended"
        )

    return notes


def evaluate_aberration_decision(
    ticker: str,
    strategy_df: pd.DataFrame,
    filter_settings: FilterSettings,
) -> DecisionResult:
    """Classify the latest completed bar into a next-day decision bucket."""
    filtered = apply_entry_filters(strategy_df, config=filter_settings)
    latest = filtered.iloc[-1]
    signal, _ = classify_latest_signal(filtered, current_state="flat")

    close = float(latest["Close"])
    upper_band = float(latest["upper_band"])
    lower_band = float(latest["lower_band"])
    middle_band = float(latest["middle_band"])
    distance_to_upper_pct = _safe_pct_distance(close, upper_band)
    distance_to_lower_pct = _safe_pct_distance(close, lower_band)
    notes = _filter_notes(latest, filter_settings)
    bar_time = to_iso(pd.to_datetime(filtered.index[-1]).to_pydatetime())

    if bool(latest.get("long_entry_filtered", False)):
        return DecisionResult(
            ticker=ticker,
            decision="TRADE_TOMORROW",
            bias="LONG",
            latest_signal=signal,
            close=close,
            bar_time=bar_time,
            upper_band=upper_band,
            lower_band=lower_band,
            middle_band=middle_band,
            distance_to_upper_pct=distance_to_upper_pct,
            distance_to_lower_pct=distance_to_lower_pct,
            notes=", ".join(["validated long breakout", *notes]),
        )

    if bool(latest.get("short_entry_filtered", False)):
        return DecisionResult(
            ticker=ticker,
            decision="TRADE_TOMORROW",
            bias="SHORT",
            latest_signal=signal,
            close=close,
            bar_time=bar_time,
            upper_band=upper_band,
            lower_band=lower_band,
            middle_band=middle_band,
            distance_to_upper_pct=distance_to_upper_pct,
            distance_to_lower_pct=distance_to_lower_pct,
            notes=", ".join(["validated short breakdown", *notes]),
        )

    near_band = min(distance_to_upper_pct, distance_to_lower_pct) <= 0.01
    raw_breakout = bool(latest.get("long_entry", False)) or bool(latest.get("short_entry", False))
    if raw_breakout or near_band:
        bias = "LONG" if distance_to_upper_pct <= distance_to_lower_pct else "SHORT"
        lead = "raw breakout seen but filters blocked" if raw_breakout else "price closed near trigger band"
        return DecisionResult(
            ticker=ticker,
            decision="WATCH_TOMORROW",
            bias=bias,
            latest_signal=signal,
            close=close,
            bar_time=bar_time,
            upper_band=upper_band,
            lower_band=lower_band,
            middle_band=middle_band,
            distance_to_upper_pct=distance_to_upper_pct,
            distance_to_lower_pct=distance_to_lower_pct,
            notes=", ".join([lead, *notes]),
        )

    return DecisionResult(
        ticker=ticker,
        decision="NO_TRADE",
        bias="NEUTRAL",
        latest_signal=signal,
        close=close,
        bar_time=bar_time,
        upper_band=upper_band,
        lower_band=lower_band,
        middle_band=middle_band,
        distance_to_upper_pct=distance_to_upper_pct,
        distance_to_lower_pct=distance_to_lower_pct,
        notes=", ".join(["no validated setup on latest close", *notes]),
    )


def build_daily_decision_report(
    settings: AppSettings,
    data_client: YFinanceClient | None = None,
) -> pd.DataFrame:
    """Build a daily next-session decision table for all configured tickers."""
    client = data_client or YFinanceClient()
    rows: list[dict[str, object]] = []

    for ticker in settings.monitor.tickers:
        data = client.get_ohlcv(
            ticker=ticker,
            interval=settings.monitor.interval,
            period=settings.monitor.period,
        )
        if data.empty:
            rows.append(
                DecisionResult(
                    ticker=ticker,
                    decision="NO_DATA",
                    bias="NEUTRAL",
                    latest_signal="NO_DATA",
                    close=float("nan"),
                    bar_time="",
                    upper_band=float("nan"),
                    lower_band=float("nan"),
                    middle_band=float("nan"),
                    distance_to_upper_pct=float("nan"),
                    distance_to_lower_pct=float("nan"),
                    notes="no market data returned",
                ).to_dict()
            )
            continue

        strategy_df = apply_aberration_strategy(
            data,
            length=settings.strategy.bollinger_length,
            multiplier=settings.strategy.bollinger_multiplier,
        )
        rows.append(evaluate_aberration_decision(ticker, strategy_df, settings.filters).to_dict())

    return pd.DataFrame(rows)
