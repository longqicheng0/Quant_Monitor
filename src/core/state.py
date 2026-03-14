"""In-memory scanner state for position and duplicate-event control."""

from __future__ import annotations


class ScannerState:
    """Keeps per-ticker state between scan cycles."""

    def __init__(self, tickers: list[str]):
        self.state_by_ticker: dict[str, str] = {ticker: "flat" for ticker in tickers}
        self.last_alert_bar_by_key: dict[str, str] = {}

    def get_position_state(self, ticker: str) -> str:
        return self.state_by_ticker.get(ticker, "flat")

    def set_position_state(self, ticker: str, state: str) -> None:
        self.state_by_ticker[ticker] = state

    def is_duplicate_alert(self, ticker: str, bar_time: str) -> bool:
        return self.last_alert_bar_by_key.get(ticker) == bar_time

    def mark_alerted(self, ticker: str, bar_time: str) -> None:
        self.last_alert_bar_by_key[ticker] = bar_time
