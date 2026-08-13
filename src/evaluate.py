"""Metrics and plots: AUC, KS, Brier, reliability curve, vintage panel (PLAN.md sections 6-7).

Emits artifacts/metrics.json (per experiment) and the plot images the README and dashboard
consume. No fabricated numbers -- any metric not yet computed is written as TBD.

Only aggregate statistics are written to artifacts/ (committed). Per-loan derived data stays
in data/ (gitignored), so nothing licensed is redistributed.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src import labels

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"

# Risk-desk palette (matches the frontend design system in PLAN.md section 10).
_BG = "#0B0E14"
_SURFACE = "#151A23"
_TEXT = "#E6EAF0"
_MUTED = "#8B97A8"
_ACCENT = "#4F8EF7"
_RED = "#E5484D"
_GRID = "#252C38"

CRISIS_VINTAGES = {2006, 2007, 2008}


def vintage_default_rates(con: duckdb.DuckDBPyConnection | None = None):
    """Return a DataFrame of per-vintage kept/defaults/default_pct from the label logic."""
    con = con or duckdb.connect()
    rel = labels.build_label(con=con)  # noqa: F841 -- referenced by name in SQL below
    return con.sql("""
        SELECT vintage,
               count(*) FILTER (WHERE default_label IS NOT NULL) AS kept,
               count(*) FILTER (WHERE default_label = 1)         AS defaults,
               round(100.0 * count(*) FILTER (WHERE default_label = 1)
                     / nullif(count(*) FILTER (WHERE default_label IS NOT NULL), 0), 3) AS default_pct
        FROM rel
        GROUP BY vintage
        ORDER BY vintage
    """).df()


def plot_vintage_default_rate(con: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Write artifacts/vintage_default_rate.{png,json}. Crisis vintages highlighted.

    Restricted to vintages with enough observable loans to be meaningful (kept >= 10k),
    which drops the censored 2024-2026 tail.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = vintage_default_rates(con)
    df = df[df["kept"] >= 10_000].reset_index(drop=True)

    ARTIFACTS.mkdir(exist_ok=True)
    df.to_json(ARTIFACTS / "vintage_default_rate.json", orient="records", indent=2)

    fig, ax = plt.subplots(figsize=(11, 4.5), dpi=140)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    # Red marks elevated-default vintages (crisis + COVID); calm vintages in the accent blue.
    elevated = CRISIS_VINTAGES | {2019}
    colors = [_RED if v in elevated else _ACCENT for v in df["vintage"]]
    ax.bar(df["vintage"], df["default_pct"], color=colors, width=0.72)

    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=_GRID, linewidth=1)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(_GRID)
    ax.tick_params(colors=_MUTED, length=0)
    ax.set_xticks(df["vintage"][::2])
    ax.set_xticklabels(df["vintage"][::2], rotation=0)
    ax.set_ylabel("24-month default rate (%)", color=_MUTED, fontsize=10)
    ax.set_title("Default rate by origination vintage", color=_TEXT, fontsize=13,
                 loc="left", pad=12)

    def _label(year: str, text: str) -> None:
        row = df[df["vintage"] == year]
        if row.empty:
            return
        y = float(row["default_pct"].iloc[0])
        ax.annotate(text, xy=(year, y), xytext=(year, y + 0.35),
                    color=_TEXT, fontsize=9, ha="center", va="bottom")

    crisis = df[df["vintage"].isin(CRISIS_VINTAGES)]
    if not crisis.empty:
        cpeak = crisis.loc[crisis["default_pct"].idxmax()]
        _label(int(cpeak["vintage"]), "housing crisis")
    _label(2019, "COVID forbearance")

    fig.text(0.125, -0.02,
             "180+ DPD or foreclosure/REO/short-sale within 24 months of origination. "
             "2006-08 = housing crisis; 2019 elevated by COVID-era forbearance (reported as delinquent).",
             color=_MUTED, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "vintage_default_rate.png", facecolor=_BG,
                bbox_inches="tight")
    plt.close(fig)

    overall_peak = df.loc[df["default_pct"].idxmax()]
    crisis_peak = crisis.loc[crisis["default_pct"].idxmax()] if not crisis.empty else overall_peak
    return {
        "vintages_plotted": len(df),
        "peak_vintage": int(overall_peak["vintage"]),
        "peak_default_pct": float(overall_peak["default_pct"]),
        "crisis_peak_vintage": int(crisis_peak["vintage"]),
        "crisis_peak_default_pct": float(crisis_peak["default_pct"]),
    }


if __name__ == "__main__":
    print(plot_vintage_default_rate())
