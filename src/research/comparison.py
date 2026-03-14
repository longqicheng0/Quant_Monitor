"""Comparison helpers for baseline vs filtered Aberration experiments."""

from __future__ import annotations

import pandas as pd


def aggregate_metrics(results_df: pd.DataFrame) -> pd.DataFrame:
    """Compute aggregate summary by strategy variant."""
    if results_df.empty:
        return pd.DataFrame()

    grouped = results_df.groupby("strategy_variant", dropna=False)
    out = grouped.agg(
        mean_total_return=("total_return", "mean"),
        median_total_return=("total_return", "median"),
        mean_max_drawdown=("max_drawdown", "mean"),
        mean_sharpe=("sharpe_ratio", "mean"),
        mean_win_rate=("win_rate", "mean"),
        mean_profit_factor=("profit_factor", "mean"),
        stocks_tested=("ticker", "nunique"),
    )
    return out.reset_index()


def pairwise_family_comparison(results_df: pd.DataFrame) -> pd.DataFrame:
    """Build family-level comparison counts baseline vs filtered."""
    if results_df.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    family = "aberration"
    base_name = f"baseline_{family}"
    filt_name = f"filtered_{family}"

    base = results_df[results_df["strategy_variant"] == base_name].set_index("ticker")
    filt = results_df[results_df["strategy_variant"] == filt_name].set_index("ticker")
    common = base.index.intersection(filt.index)

    if len(common) == 0:
        return pd.DataFrame()

    b = base.loc[common]
    f = filt.loc[common]
    rows.append(
        {
            "strategy_family": family,
            "stocks_compared": int(len(common)),
            "filtered_beats_baseline_count": int((f["total_return"] > b["total_return"]).sum()),
            "filtered_reduces_drawdown_count": int((f["max_drawdown"] > b["max_drawdown"]).sum()),
            "mean_return_delta": float((f["total_return"] - b["total_return"]).mean()),
            "mean_drawdown_delta": float((f["max_drawdown"] - b["max_drawdown"]).mean()),
        }
    )
    return pd.DataFrame(rows)
