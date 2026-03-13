"""Ticker scanner for multi-strategy signal monitoring."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.settings import AppSettings
from src.datafeed.yfinance_client import YFinanceClient
from src.strategy.aberration import apply_aberration_strategy
from src.strategy.dual_thrust import apply_dual_thrust_strategy
from src.strategy.signals import classify_latest_signal_for_strategy
from src.utils.time_utils import to_iso, utc_now


@dataclass
class SignalEvent:
    """Structured signal event for alerts and logging."""

    event_time: str
    strategy_name: str
    ticker: str
    timeframe: str
    signal_type: str
    close: float
    bar_time: str
    middle_band: float = float("nan")
    upper_band: float = float("nan")
    lower_band: float = float("nan")
    open_price: float = float("nan")
    range_value: float = float("nan")
    upper_trigger: float = float("nan")
    lower_trigger: float = float("nan")


@dataclass
class ScanStatus:
    """Latest status snapshot for one ticker."""

    ticker: str
    strategy_name: str
    bar_time: str
    close: float
    state: str
    latest_signal: str
    middle_band: float = float("nan")
    upper_band: float = float("nan")
    lower_band: float = float("nan")
    open_price: float = float("nan")
    range_value: float = float("nan")
    upper_trigger: float = float("nan")
    lower_trigger: float = float("nan")


class AberrationScanner:
    """Scan one or more tickers using configured strategy logic."""

    def __init__(self, settings: AppSettings, data_client: YFinanceClient | None = None):
        self.settings = settings
        self.data_client = data_client or YFinanceClient()
        self.strategy_name = settings.strategy.strategy_name.lower()
        self.state_by_ticker: dict[str, str] = {ticker: "flat" for ticker in settings.monitor.tickers}
        self.last_alert_bar_by_ticker: dict[str, str] = {}

    def _apply_strategy(self, data: pd.DataFrame) -> pd.DataFrame:
        """Run the selected strategy and return strategy output DataFrame."""
        if self.strategy_name == "aberration":
            return apply_aberration_strategy(
                data,
                length=self.settings.strategy.bollinger_length,
                multiplier=self.settings.strategy.bollinger_multiplier,
            )

        if self.strategy_name == "dual_thrust":
            return apply_dual_thrust_strategy(
                data,
                lookback=self.settings.strategy.dual_thrust_lookback,
                multiplier=self.settings.strategy.dual_thrust_multiplier,
            )

        raise ValueError(f"Unsupported strategy_name: {self.strategy_name}")

    def scan_once(self) -> tuple[list[SignalEvent], list[ScanStatus]]:
        """Run one full scan pass over all configured tickers."""
        events: list[SignalEvent] = []
        statuses: list[ScanStatus] = []

        for ticker in self.settings.monitor.tickers:
            event, status = self._scan_ticker(ticker)
            if status is not None:
                statuses.append(status)
            if event is not None:
                events.append(event)

        return events, statuses

    def _scan_ticker(self, ticker: str) -> tuple[SignalEvent | None, ScanStatus | None]:
        """Scan one ticker and return optional event + current status."""
        data = self.data_client.get_ohlcv(
            ticker=ticker,
            interval=self.settings.monitor.timeframe,
            period=self.settings.monitor.history_period,
        )

        if data.empty:
            return None, None

        result = self._apply_strategy(data)

        latest = result.iloc[-1]
        bar_time = to_iso(pd.to_datetime(result.index[-1]).to_pydatetime())

        current_state = self.state_by_ticker.get(ticker, "flat")
        signal_name, next_state = classify_latest_signal_for_strategy(
            result,
            strategy_name=self.strategy_name,
            current_state=current_state,
        )

        status = ScanStatus(
            ticker=ticker,
            strategy_name=self.strategy_name,
            bar_time=bar_time,
            close=float(latest["Close"]),
            state=next_state,
            latest_signal=signal_name,
            middle_band=float(latest["middle_band"]) if pd.notna(latest.get("middle_band", float("nan"))) else float("nan"),
            upper_band=float(latest["upper_band"]) if pd.notna(latest.get("upper_band", float("nan"))) else float("nan"),
            lower_band=float(latest["lower_band"]) if pd.notna(latest.get("lower_band", float("nan"))) else float("nan"),
            open_price=float(latest["Open"]) if pd.notna(latest.get("Open", float("nan"))) else float("nan"),
            range_value=float(latest["range_value"]) if pd.notna(latest.get("range_value", float("nan"))) else float("nan"),
            upper_trigger=float(latest["upper_trigger"]) if pd.notna(latest.get("upper_trigger", float("nan"))) else float("nan"),
            lower_trigger=float(latest["lower_trigger"]) if pd.notna(latest.get("lower_trigger", float("nan"))) else float("nan"),
        )

        self.state_by_ticker[ticker] = next_state

        if signal_name == "NO_SIGNAL":
            return None, status

        # Avoid duplicate alerts when scanning repeatedly before a new bar is formed.
        dedupe_key = f"{ticker}:{self.strategy_name}"
        if self.last_alert_bar_by_ticker.get(dedupe_key) == bar_time:
            return None, status

        self.last_alert_bar_by_ticker[dedupe_key] = bar_time
        event = SignalEvent(
            event_time=to_iso(utc_now()),
            strategy_name=self.strategy_name,
            ticker=ticker,
            timeframe=self.settings.monitor.timeframe,
            signal_type=signal_name,
            close=float(latest["Close"]),
            bar_time=bar_time,
            middle_band=float(latest["middle_band"]) if pd.notna(latest.get("middle_band", float("nan"))) else float("nan"),
            upper_band=float(latest["upper_band"]) if pd.notna(latest.get("upper_band", float("nan"))) else float("nan"),
            lower_band=float(latest["lower_band"]) if pd.notna(latest.get("lower_band", float("nan"))) else float("nan"),
            open_price=float(latest["Open"]) if pd.notna(latest.get("Open", float("nan"))) else float("nan"),
            range_value=float(latest["range_value"]) if pd.notna(latest.get("range_value", float("nan"))) else float("nan"),
            upper_trigger=float(latest["upper_trigger"]) if pd.notna(latest.get("upper_trigger", float("nan"))) else float("nan"),
            lower_trigger=float(latest["lower_trigger"]) if pd.notna(latest.get("lower_trigger", float("nan"))) else float("nan"),
        )
        return event, status
