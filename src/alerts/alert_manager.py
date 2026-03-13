"""Alert manager for signal notifications."""

from __future__ import annotations

from dataclasses import asdict

from src.scanner import SignalEvent


class AlertManager:
    """Dispatch alerts to enabled channels."""

    def __init__(self, enabled: bool = True, console: bool = True, webhook_url: str | None = None):
        self.enabled = enabled
        self.console = console
        self.webhook_url = webhook_url

    def send(self, event: SignalEvent) -> None:
        """Send alert for a signal event."""
        if not self.enabled:
            return

        if self.console:
            print(
                "[ALERT] "
                f"{event.event_time} | {event.ticker} | {event.timeframe} | {event.signal_type} "
                f"close={event.close:.2f}"
            )

        # Placeholder: Future webhook/Discord/email integrations.
        if self.webhook_url:
            self._send_webhook_placeholder(event)

    def _send_webhook_placeholder(self, event: SignalEvent) -> None:
        """Placeholder for future webhook support."""
        payload = asdict(event)
        print(f"[ALERT][WEBHOOK_PLACEHOLDER] target={self.webhook_url} payload={payload}")
