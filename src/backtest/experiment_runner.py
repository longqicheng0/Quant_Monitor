"""CLI entrypoint for baseline vs filtered Aberration experiments."""

from __future__ import annotations

import argparse

from src.research.experiment_runner import run_strategy_experiments
from src.utils.config_loader import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run baseline vs filtered Aberration experiments")
    parser.add_argument("--config", default="config/settings.example.json")
    parser.add_argument(
        "--strategy-family",
        choices=["aberration"],
        default="aberration",
        help="Aberration is the only supported family in this repository.",
    )
    parser.add_argument(
        "--tickers",
        default=None,
        help="Optional comma-separated override for experiment basket.",
    )
    parser.add_argument("--interval", default=None, help="Optional override for experiment interval.")
    parser.add_argument("--period", default=None, help="Optional override for experiment period.")
    parser.add_argument("--output-prefix", default="experiment", help="Prefix used for CSV/plot outputs.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings(args.config)

    if args.tickers:
        settings.experiment.experiment_tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if args.interval:
        settings.experiment.interval = args.interval
    if args.period:
        settings.experiment.period = args.period

    artifacts = run_strategy_experiments(
        app_settings=settings,
        strategy_family=args.strategy_family,
        output_prefix=args.output_prefix,
    )

    print("\nExperiment complete.")
    print(f"Rows generated: {len(artifacts.results_df)}")
    print("Saved files:")
    for key, path in artifacts.files.items():
        print(f"- {key}: {path}")

    print("\nAggregate Summary")
    if artifacts.aggregate_df.empty:
        print("No aggregate rows. Check ticker data availability.")
    else:
        print(artifacts.aggregate_df.to_string(index=False))

    print("\nFamily Comparison")
    if artifacts.family_df.empty:
        print("No family comparison rows.")
    else:
        print(artifacts.family_df.to_string(index=False))

    print("\nBeginner Summary")
    for line in artifacts.summary_lines:
        print(f"- {line}")


if __name__ == "__main__":
    main()
