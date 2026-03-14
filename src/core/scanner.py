"""Aberration scanner orchestration layer."""

from __future__ import annotations

import pandas as pd

from config.settings import AppSettings
from src.core.models import ScanStatus, SignalEvent
from src.core.state import ScannerState
from src.datafeed.yfinance_client import YFinanceClient
from src.research.decision_engine import evaluate_aberration_decision
from src.strategy.aberration import apply_aberration_strategy
from src.strategy.signals import classify_latest_signal
from src.utils.time_utils import to_iso, utc_now


class StrategyScanner:
    """Scan one or more tickers using Aberration strategy logic."""

    def __init__(self, settings: AppSettings, data_client: YFinanceClient | None = None):
        self.settings = settings
        self.data_client = data_client or YFinanceClient()
        self.state = ScannerState(settings.monitor.tickers)

    @property
    def strategy_name(self) -> str:
        return "aberration"

    def scan_once(self) -> tuple[list[SignalEvent], list[ScanStatus]]:
        """Run one full scan pass over all configured tickers."""
        events: list[SignalEvent] = []
        statuses: list[ScanStatus] = []

        for ticker in self.settings.monitor.tickers:
            event, status = self.scan_ticker(ticker)
            if status is not None:
                statuses.append(status)
            if event is not None:
                events.append(event)

        return events, statuses

    def scan_ticker(self, ticker: str) -> tuple[SignalEvent | None, ScanStatus | None]:
        """Scan one ticker and return optional fresh event plus current status."""
        data = self.data_client.get_ohlcv(
            ticker=ticker,
            interval=self.settings.monitor.interval,
            period=self.settings.monitor.period,
        )
        if data.empty:
            return None, None

        result = apply_aberration_strategy(
            data,
            length=self.settings.strategy.bollinger_length,
            multiplier=self.settings.strategy.bollinger_multiplier,
        )
        return self._build_result_for_ticker(ticker=ticker, result=result)

    def _build_result_for_ticker(self, ticker: str, result: pd.DataFrame) -> tuple[SignalEvent | None, ScanStatus]:
        latest = result.iloc[-1]
        bar_time = to_iso(pd.to_datetime(result.index[-1]).to_pydatetime())

        current_state = self.state.get_position_state(ticker)
        signal_name, next_state = classify_latest_signal(result, current_state=current_state)
        signal_fresh = signal_name != "NO_SIGNAL" and not self.state.is_duplicate_alert(ticker=ticker, bar_time=bar_time)
        decision = evaluate_aberration_decision(ticker=ticker, strategy_df=result, filter_settings=self.settings.filters)

        status = ScanStatus(
            ticker=ticker,
            strategy_name=self.strategy_name,
            bar_time=bar_time,
            close=float(latest["Close"]),
            state=next_state,
            latest_signal=signal_name,
            signal_fresh=signal_fresh,
            middle_band=float(latest["middle_band"]) if pd.notna(latest.get("middle_band", float("nan"))) else float("nan"),
            upper_band=float(latest["upper_band"]) if pd.notna(latest.get("upper_band", float("nan"))) else float("nan"),
            lower_band=float(latest["lower_band"]) if pd.notna(latest.get("lower_band", float("nan"))) else float("nan"),
            decision=decision.decision,
            decision_notes=decision.notes,
        )

        self.state.set_position_state(ticker, next_state)
        if not signal_fresh:
            return None, status

        self.state.mark_alerted(ticker=ticker, bar_time=bar_time)
        event = SignalEvent(
            event_time=to_iso(utc_now()),
            strategy_name=self.strategy_name,
            ticker=ticker,
            timeframe=self.settings.monitor.interval,
            signal_type=signal_name,
            close=float(latest["Close"]),
            bar_time=bar_time,
            middle_band=float(latest["middle_band"]) if pd.notna(latest.get("middle_band", float("nan"))) else float("nan"),
            upper_band=float(latest["upper_band"]) if pd.notna(latest.get("upper_band", float("nan"))) else float("nan"),
            lower_band=float(latest["lower_band"]) if pd.notna(latest.get("lower_band", float("nan"))) else float("nan"),
        )
        return event, status
