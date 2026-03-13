"""Terminal entrypoint for scheduled Aberration monitoring."""

from __future__ import annotations

import argparse
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from src.alerts.alert_manager import AlertManager
from src.scanner import AberrationScanner
from src.storage.signal_logger import SignalLogger
from src.utils.config_loader import load_settings
from src.utils.logger import setup_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aberration Strategy Monitor")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Optional JSON config path, e.g. config/settings.example.json",
    )
    return parser


def run_once(scanner: AberrationScanner, alert_manager: AlertManager, signal_logger: SignalLogger) -> None:
    """Run one scanner cycle, print status, and dispatch events."""
    events, statuses = scanner.scan_once()

    print("\n=== Aberration Monitor Scan ===")
    for status in statuses:
        print(
            f"{status.ticker:<8} close={status.close:>8.2f} "
            f"mid={status.middle_band:>8.2f} up={status.upper_band:>8.2f} low={status.lower_band:>8.2f} "
            f"state={status.state:<5} signal={status.latest_signal}"
        )

    for event in events:
        alert_manager.send(event)
        signal_logger.log(event)


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings(args.config)

    Path("data/logs").mkdir(parents=True, exist_ok=True)
    app_logger = setup_logger("aberration-monitor", log_file="data/logs/app.log")

    scanner = AberrationScanner(settings=settings)
    alert_manager = AlertManager(
        enabled=settings.alerts.enabled,
        console=settings.alerts.console,
        webhook_url=settings.alerts.webhook_url,
    )
    signal_logger = SignalLogger(
        enabled=settings.logging.enabled,
        csv_path=settings.logging.csv_path,
        sqlite_path=settings.logging.sqlite_path,
        use_sqlite=settings.logging.use_sqlite,
    )

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_once,
        "interval",
        seconds=settings.monitor.scan_interval_seconds,
        args=[scanner, alert_manager, signal_logger],
        max_instances=1,
        coalesce=True,
    )

    app_logger.info("Starting Aberration monitor. Press Ctrl+C to stop.")
    run_once(scanner, alert_manager, signal_logger)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        app_logger.info("Monitor stopped by user.")


if __name__ == "__main__":
    main()
