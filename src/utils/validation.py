"""Runtime validation helpers with beginner-friendly error messages."""

from __future__ import annotations

from config.settings import AppSettings


def validate_runtime_settings(settings: AppSettings) -> list[str]:
    """Return a list of human-readable validation errors."""
    errors: list[str] = []

    if not settings.monitor.tickers:
        errors.append("monitor.tickers cannot be empty. Example: ['SPY', 'QQQ']")

    if settings.monitor.scan_interval_seconds < 5:
        errors.append("monitor.scan_interval_seconds must be at least 5 seconds.")

    if not settings.monitor.interval:
        errors.append("monitor.interval is required. Example: '1d'.")

    if not settings.monitor.period:
        errors.append("monitor.period is required. Example: '1y'.")

    return errors


def format_validation_errors(errors: list[str]) -> str:
    """Format errors for terminal output."""
    lines = ["Configuration validation failed:"]
    for idx, err in enumerate(errors, start=1):
        lines.append(f"  {idx}. {err}")

    lines.append("")
    lines.append("Example fix in config/settings.example.json:")
    lines.append('  "monitor": { "interval": "1d", "period": "1y" }')
    return "\n".join(lines)
