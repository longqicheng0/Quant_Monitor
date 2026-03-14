"""Interactive prompts used for beginner-friendly CLI runs."""

from __future__ import annotations

from config.settings import AppSettings


def _ask_text(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def _ask_yes_no(prompt: str, default_yes: bool = True) -> bool:
    default = "y" if default_yes else "n"
    while True:
        value = input(f"{prompt} (y/n) [{default}]: ").strip().lower()
        if not value:
            return default_yes
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer y or n.")


def prompt_for_missing_runtime_options(settings: AppSettings) -> AppSettings:
    """Ask user for friendly runtime options."""
    print("\nInteractive setup: choose runtime options for this Aberration session.\n")

    tickers_text = _ask_text("Enter tickers (comma-separated)", ",".join(settings.monitor.tickers))
    settings.monitor.tickers = [ticker.strip().upper() for ticker in tickers_text.split(",") if ticker.strip()]
    settings.monitor.interval = _ask_text("Choose interval", settings.monitor.interval)
    settings.monitor.period = _ask_text("Choose history period", settings.monitor.period)

    logging_enabled = _ask_yes_no("Enable signal logging", settings.logging.enabled)
    settings.logging.enabled = logging_enabled

    alerts_enabled = _ask_yes_no("Enable console alerts", settings.alerts.enabled)
    settings.alerts.enabled = alerts_enabled
    settings.alerts.console = alerts_enabled

    return settings
