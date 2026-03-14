"""Shared data models used by scanner, alerts, and storage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SignalEvent:
    """Structured signal event produced by scan cycles."""

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


@dataclass
class ScanStatus:
    """Latest status snapshot for one ticker from scanner."""

    ticker: str
    strategy_name: str
    bar_time: str
    close: float
    state: str
    latest_signal: str
    signal_fresh: bool
    middle_band: float = float("nan")
    upper_band: float = float("nan")
    lower_band: float = float("nan")
    decision: str = "NO_TRADE"
    decision_notes: str = ""
