"""Build experiment reports, CSV outputs, and simple plots."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def save_experiment_tables(
    results_df: pd.DataFrame,
    aggregate_df: pd.DataFrame,
    family_df: pd.DataFrame,
    output_dir: str = "data/processed",
    prefix: str = "experiment",
) -> dict[str, str]:
    """Write result tables to CSV and return file paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    files = {
        "results": str(out / f"{prefix}_results.csv"),
        "aggregate": str(out / f"{prefix}_aggregate.csv"),
        "family": str(out / f"{prefix}_family_comparison.csv"),
    }

    results_df.to_csv(files["results"], index=False)
    aggregate_df.to_csv(files["aggregate"], index=False)
    family_df.to_csv(files["family"], index=False)
    return files


def plot_return_heatmap(results_df: pd.DataFrame, output_path: str) -> None:
    """Save return heatmap by ticker/strategy variant."""
    if results_df.empty:
        return
    pivot = results_df.pivot(index="ticker", columns="strategy_variant", values="total_return")

    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(pivot.values, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("Total Return Heatmap")
    fig.colorbar(im, ax=ax, label="Total Return")
    fig.tight_layout()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)


def plot_drawdown_comparison(results_df: pd.DataFrame, output_path: str) -> None:
    """Save max drawdown bar chart by strategy variant."""
    if results_df.empty:
        return
    grouped = results_df.groupby("strategy_variant", dropna=False)["max_drawdown"].mean().sort_values()

    fig, ax = plt.subplots(figsize=(8, 4))
    grouped.plot(kind="bar", ax=ax)
    ax.set_title("Mean Max Drawdown by Strategy Variant")
    ax.set_ylabel("Max Drawdown")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)


def plot_return_comparison(results_df: pd.DataFrame, output_path: str) -> None:
    """Save mean total return comparison bar chart."""
    if results_df.empty:
        return
    grouped = results_df.groupby("strategy_variant", dropna=False)["total_return"].mean().sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(8, 4))
    grouped.plot(kind="bar", ax=ax)
    ax.set_title("Mean Total Return by Strategy Variant")
    ax.set_ylabel("Total Return")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)


def build_terminal_summary(results_df: pd.DataFrame, family_df: pd.DataFrame) -> list[str]:
    """Build beginner-friendly summary lines."""
    lines: list[str] = []
    if results_df.empty:
        return ["No experiment results were generated."]

    for _, row in family_df.iterrows():
        family = row["strategy_family"]
        lines.append(
            f"Filtered {family} outperformed baseline on "
            f"{int(row['filtered_beats_baseline_count'])}/{int(row['stocks_compared'])} stocks."
        )
        lines.append(
            f"Filtered {family} reduced drawdown on "
            f"{int(row['filtered_reduces_drawdown_count'])}/{int(row['stocks_compared'])} stocks."
        )

    top = results_df.sort_values("total_return", ascending=False).iloc[0]
    lines.append(
        "Best-performing stock-strategy combination: "
        f"{top['ticker']} + {top['strategy_variant']} (return={top['total_return']:.2%})."
    )
    return lines
