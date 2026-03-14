"""Console formatting helpers for beginner-friendly output."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from config.settings import AppSettings
from src.core.models import ScanStatus


def startup_banner(settings: AppSettings) -> str:
    """Return a startup banner with key runtime details."""
    logging_status = "enabled" if settings.logging.enabled else "disabled"
    alerts_status = "enabled" if settings.alerts.enabled else "disabled"

    lines = [
        "=" * 72,
        " Aberration Strategy Monitor",
        "=" * 72,
        f" Start Time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        " Strategy       : aberration",
        f" Tickers        : {', '.join(settings.monitor.tickers)}",
        f" Interval       : {settings.monitor.interval}",
        f" Lookback       : {settings.monitor.period}",
        f" Scan Interval  : {settings.monitor.scan_interval_seconds}s",
        f" Logging        : {logging_status} ({settings.logging.csv_path})",
        f" Alerts         : {alerts_status} (console={settings.alerts.console})",
        "=" * 72,
    ]
    return "\n".join(lines)


def level_summary(status: ScanStatus) -> str:
    """Return concise key levels text for a status row."""
    return f"mid={status.middle_band:.2f}, up={status.upper_band:.2f}, low={status.lower_band:.2f}"


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values))

    sep = "-+-".join("-" * width for width in widths)
    out = [fmt_row(headers), sep]
    out.extend(fmt_row(row) for row in rows)
    return "\n".join(out)


def scan_summary_table(statuses: list[ScanStatus]) -> str:
    """Return summary table for one scan cycle."""
    headers = ["Ticker", "Close", "State", "Latest Signal", "Fresh", "Decision", "Key Levels"]
    rows: list[list[str]] = []

    for status in statuses:
        rows.append(
            [
                status.ticker,
                f"{status.close:.2f}",
                status.state,
                status.latest_signal,
                "YES" if status.signal_fresh else "NO",
                status.decision,
                level_summary(status),
            ]
        )

    return _format_table(headers, rows) if rows else "No status rows returned in this cycle."


def decision_report_table(report_df: pd.DataFrame) -> str:
    """Format the daily decision report for terminal output."""
    if report_df.empty:
        return "No report rows generated."

    headers = ["Ticker", "Decision", "Bias", "Signal", "Close", "Notes"]
    rows: list[list[str]] = []
    for _, row in report_df.iterrows():
        rows.append(
            [
                str(row.get("ticker", "")),
                str(row.get("decision", "")),
                str(row.get("bias", "")),
                str(row.get("latest_signal", "")),
                f"{float(row.get('close', float('nan'))):.2f}" if pd.notna(row.get("close")) else "nan",
                str(row.get("notes", "")),
            ]
        )

    return _format_table(headers, rows)
