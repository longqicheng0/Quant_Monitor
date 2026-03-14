"""CLI command entrypoints for scanner, report, and doctor tasks."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from config.settings import AppSettings, DEFAULT_SETTINGS
from src.alerts.alert_manager import AlertManager
from src.cli.formatter import decision_report_table, scan_summary_table, startup_banner
from src.cli.prompts import prompt_for_missing_runtime_options
from src.core.scanner import StrategyScanner
from src.research.decision_engine import build_daily_decision_report
from src.storage.signal_logger import SignalLogger
from src.utils.config_loader import load_settings
from src.utils.logger import setup_logger
from src.utils.validation import format_validation_errors, validate_runtime_settings


def _parse_tickers(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    values = [item.strip().upper() for item in raw.split(",") if item.strip()]
    return values or None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Beginner-friendly Aberration market scanner and daily decision tool",
        epilog=(
            "Examples:\n"
            "  python -m src.main --tickers QQQ,NVDA --once\n"
            "  python -m src.main --report\n"
            "  python -m src.cli.commands --doctor"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--config", type=str, default="config/settings.example.json", help="Path to JSON config file.")
    parser.add_argument("--tickers", type=str, default=None, help="Comma-separated symbols, e.g. QQQ,NVDA,MSFT")
    parser.add_argument("--interval", "--timeframe", dest="interval", type=str, default=None, help="Market data interval, e.g. 1d or 1h")
    parser.add_argument("--period", type=str, default=None, help="History period, e.g. 6mo, 1y, 2y")
    parser.add_argument("--report", action="store_true", help="Generate a daily next-session decision report and exit.")
    parser.add_argument("--once", action="store_true", help="Run exactly one scan cycle and exit.")
    parser.add_argument("--verbose", action="store_true", help="Print step-by-step progress messages.")
    parser.add_argument("--no-prompt", action="store_true", help="Disable interactive prompts and use defaults/config only.")
    parser.add_argument("--doctor", action="store_true", help="Run environment checks and exit.")
    return parser


def run_doctor(config_path: str) -> int:
    """Run basic environment checks for beginners."""
    print("\nRunning project doctor checks...\n")

    checks: list[tuple[str, bool, str]] = []
    py_ok = sys.version_info >= (3, 9)
    checks.append(("Python version >= 3.9", py_ok, f"Current: {sys.version.split()[0]}"))

    cfg_path = Path(config_path)
    checks.append(("Config file exists", cfg_path.exists(), str(cfg_path)))

    req_path = Path("requirements.txt")
    checks.append(("requirements.txt exists", req_path.exists(), str(req_path)))

    for package in ["pandas", "numpy", "yfinance", "streamlit", "apscheduler", "pydantic"]:
        try:
            __import__(package)
            checks.append((f"Dependency import: {package}", True, "import ok"))
        except Exception as exc:
            checks.append((f"Dependency import: {package}", False, str(exc)))

    for folder in [Path("data/logs"), Path("data/processed")]:
        folder.mkdir(parents=True, exist_ok=True)
        checks.append((f"{folder} directory writable", folder.exists() and folder.is_dir(), str(folder)))

    all_ok = True
    for name, ok, details in checks:
        icon = "OK" if ok else "FAIL"
        print(f"[{icon}] {name} -> {details}")
        all_ok = all_ok and ok

    print("\nDoctor result:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


def _apply_runtime_overrides(args: argparse.Namespace) -> AppSettings:
    try:
        settings = load_settings(args.config)
    except FileNotFoundError:
        print(f"Config file not found at {args.config}. Starting with built-in defaults instead.")
        settings = AppSettings.model_validate(DEFAULT_SETTINGS.model_dump())

    tickers = _parse_tickers(args.tickers)
    if tickers:
        settings.monitor.tickers = tickers
    if args.interval:
        settings.monitor.interval = args.interval
    if args.period:
        settings.monitor.period = args.period

    should_prompt = (
        not args.no_prompt
        and sys.stdin.isatty()
        and args.tickers is None
        and args.interval is None
        and args.period is None
        and not args.report
    )
    if should_prompt:
        settings = prompt_for_missing_runtime_options(settings)

    return settings


def _run_single_cycle(
    scanner: StrategyScanner,
    alert_manager: AlertManager,
    signal_logger: SignalLogger,
    verbose: bool = False,
) -> None:
    statuses = []

    for ticker in scanner.settings.monitor.tickers:
        print(f"Loading market data for {ticker}...")
        event, status = scanner.scan_ticker(ticker)
        if status is None:
            print(f"No data returned for {ticker}. Skipping.")
            continue

        statuses.append(status)
        if event is None:
            print(f"No fresh signal detected on latest completed bar for {ticker}. Decision: {status.decision}.")
            continue

        print(f"Fresh {event.signal_type} signal detected for {ticker}.")
        alert_manager.send(event)
        signal_logger.log(event)

        if verbose:
            destination = "SQLite" if signal_logger.use_sqlite else "CSV"
            print(f"Signal logged to {destination} successfully.")

    print("\nScan Summary")
    print(scan_summary_table(statuses))


def run_report(settings: AppSettings) -> int:
    """Generate and save a daily next-session decision report."""
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    report_df = build_daily_decision_report(settings)
    output_path = Path("data/processed") / f"daily_report_{date.today().isoformat()}.csv"
    report_df.to_csv(output_path, index=False)

    print("\nDaily Decision Report")
    print(decision_report_table(report_df))
    print(f"\nSaved report to {output_path}")
    return 0


def run_scanner(args: argparse.Namespace) -> int:
    """Run scanner with beginner-friendly UX and safe defaults."""
    try:
        settings = _apply_runtime_overrides(args)
    except Exception as exc:
        print("Could not load runtime settings.")
        print(f"Details: {exc}")
        print("Tip: run with --doctor or verify config/settings.example.json")
        return 1

    validation_errors = validate_runtime_settings(settings)
    if validation_errors:
        print(format_validation_errors(validation_errors))
        return 1

    if args.report:
        return run_report(settings)

    Path("data/logs").mkdir(parents=True, exist_ok=True)
    app_logger = setup_logger("aberration-monitor", log_file="data/logs/app.log")
    print(startup_banner(settings))

    scanner = StrategyScanner(settings=settings)
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

    if args.once:
        _run_single_cycle(scanner, alert_manager, signal_logger, verbose=args.verbose)
        return 0

    scheduler = BlockingScheduler()
    scheduler.add_job(
        _run_single_cycle,
        "interval",
        seconds=settings.monitor.scan_interval_seconds,
        args=[scanner, alert_manager, signal_logger, args.verbose],
        max_instances=1,
        coalesce=True,
    )

    app_logger.info("Starting Aberration scanner loop.")
    _run_single_cycle(scanner, alert_manager, signal_logger, verbose=args.verbose)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        app_logger.info("Scanner stopped by user.")

    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.doctor:
        return run_doctor(args.config)
    return run_scanner(args)


if __name__ == "__main__":
    raise SystemExit(main())
