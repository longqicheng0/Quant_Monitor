"""Run baseline vs filtered Aberration experiments across ticker baskets."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.settings import AppSettings
from src.backtest.backtester import BacktestResult, run_signal_backtest
from src.datafeed.yfinance_client import YFinanceClient
from src.research.comparison import aggregate_metrics, pairwise_family_comparison
from src.research.report_builder import (
    build_terminal_summary,
    plot_drawdown_comparison,
    plot_return_comparison,
    plot_return_heatmap,
    save_experiment_tables,
)
from src.strategy.aberration import apply_aberration_strategy

from .filters import apply_entry_filters


@dataclass
class ExperimentArtifacts:
    results_df: pd.DataFrame
    aggregate_df: pd.DataFrame
    family_df: pd.DataFrame
    files: dict[str, str]
    summary_lines: list[str]


def _prepare_strategy_frame(
    data: pd.DataFrame,
    variant: str,
    app_settings: AppSettings,
) -> tuple[pd.DataFrame, str, str, str]:
    """Return strategy frame and signal column settings for backtest."""
    if variant == "baseline_aberration":
        df = apply_aberration_strategy(
            data,
            length=app_settings.strategy.bollinger_length,
            multiplier=app_settings.strategy.bollinger_multiplier,
        )
        return df, "aberration", "long_entry", "short_entry"

    if variant == "filtered_aberration":
        base = apply_aberration_strategy(
            data,
            length=app_settings.strategy.bollinger_length,
            multiplier=app_settings.strategy.bollinger_multiplier,
        )
        filt = apply_entry_filters(base, config=app_settings.filters)
        return filt, "aberration", "long_entry_filtered", "short_entry_filtered"

    raise ValueError(f"Unsupported strategy variant: {variant}")


def _variant_list(strategy_family: str | None) -> list[str]:
    if strategy_family not in {None, "aberration"}:
        raise ValueError("Only the aberration family is supported.")
    return ["baseline_aberration", "filtered_aberration"]


def run_strategy_experiments(
    app_settings: AppSettings,
    strategy_family: str | None = None,
    output_prefix: str = "experiment",
) -> ExperimentArtifacts:
    """Run experiments and return result tables plus saved file paths."""
    exp_settings = app_settings.experiment
    client = YFinanceClient()

    rows: list[dict[str, object]] = []
    variants = _variant_list(strategy_family)

    for ticker in exp_settings.experiment_tickers:
        data = client.get_ohlcv(ticker=ticker, interval=exp_settings.interval, period=exp_settings.period)
        if data.empty:
            continue

        for variant in variants:
            frame, family, long_col, short_col = _prepare_strategy_frame(
                data=data,
                variant=variant,
                app_settings=app_settings,
            )

            bt: BacktestResult = run_signal_backtest(
                data=data,
                strategy_df=frame,
                strategy_family=family,
                long_entry_col=long_col,
                short_entry_col=short_col,
                atr_length=app_settings.filters.atr_length,
                atr_stop_enabled=exp_settings.atr_stop_enabled and variant.startswith("filtered"),
                atr_stop_multiple=exp_settings.atr_stop_multiple,
                atr_trailing_enabled=exp_settings.atr_trailing_enabled and variant.startswith("filtered"),
                atr_trailing_multiple=exp_settings.atr_trailing_multiple,
            )

            summary = dict(bt.summary)
            summary["ticker"] = ticker
            summary["strategy_variant"] = variant
            summary["strategy_family"] = family
            rows.append(summary)

    results_df = pd.DataFrame(rows)
    aggregate_df = aggregate_metrics(results_df)
    family_df = pairwise_family_comparison(results_df)

    files = save_experiment_tables(
        results_df=results_df,
        aggregate_df=aggregate_df,
        family_df=family_df,
        output_dir="data/processed",
        prefix=output_prefix,
    )

    plot_return_heatmap(results_df, f"data/processed/{output_prefix}_return_heatmap.png")
    plot_drawdown_comparison(results_df, f"data/processed/{output_prefix}_drawdown_comparison.png")
    plot_return_comparison(results_df, f"data/processed/{output_prefix}_return_comparison.png")

    summary_lines = build_terminal_summary(results_df, family_df)
    return ExperimentArtifacts(
        results_df=results_df,
        aggregate_df=aggregate_df,
        family_df=family_df,
        files=files,
        summary_lines=summary_lines,
    )
