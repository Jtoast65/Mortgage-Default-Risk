"""Default label construction with a fixed 24-month observation window (PLAN.md section 3).

    Default = the loan reaches 180+ days delinquent, OR terminates through foreclosure,
    REO, short sale, or deed-in-lieu, within 24 months of origination.

Operationalised against the SFLLD monthly performance file:
    - 180+ DPD  ->  Current Loan Delinquency Status numeric >= 6 (each unit = 30 days),
                    or status 'RA' (REO Acquisition).
    - terminates badly  ->  Zero Balance Code in {03 short sale/charge-off, 09 REO}.
    Both must occur within the first 24 months (loan_age <= 24).

Censoring (dropped, label = NULL): a loan that leaves the panel before month 24 without
defaulting cannot be observed for the full window. This is the competing-risk prepayment
case (Zero Balance Code 01) and the too-recently-originated case. A loan is retained as a
non-default (label 0) only if it is observed through month 24 (max loan_age >= 24) without
having defaulted. Prepayment is a competing risk; a full treatment would model it jointly.

Vintage comes from the parquet partition column, so no join to origination is needed here.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from src.layouts import (
    DEFAULT_ZERO_BALANCE_CODES,
    DELINQUENCY_DEFAULT_THRESHOLD,
    OBSERVATION_WINDOW_MONTHS,
    REO_ACQUISITION_STATUS,
)

ROOT = Path(__file__).resolve().parent.parent
PERF_GLOB = str(ROOT / "data" / "processed" / "performance" / "*" / "data.parquet")
LABELS_PARQUET = ROOT / "data" / "processed" / "labels.parquet"


def label_query(source: str,
                window: int = OBSERVATION_WINDOW_MONTHS,
                threshold: int = DELINQUENCY_DEFAULT_THRESHOLD) -> str:
    """SQL that collapses the monthly performance panel to one label per loan.

    `source` is any DuckDB-addressable relation: a table name, or a
    read_parquet('...') expression. Returns loan_id, vintage, and default_label
    (1 = default, 0 = survived the window, NULL = censored / dropped).
    """
    zb = ", ".join(f"'{c}'" for c in sorted(DEFAULT_ZERO_BALANCE_CODES))
    return f"""
    WITH agg AS (
        SELECT
            loan_id,
            any_value(vintage) AS vintage,
            max(TRY_CAST(loan_age AS INTEGER)) AS max_age,
            max(CASE
                    WHEN TRY_CAST(loan_age AS INTEGER) <= {window} AND (
                             COALESCE(TRY_CAST(current_delinquency_status AS INTEGER), 0) >= {threshold}
                          OR current_delinquency_status = '{REO_ACQUISITION_STATUS}'
                          OR zero_balance_code IN ({zb})
                         )
                    THEN 1 ELSE 0
                END) AS defaulted_in_window
        FROM {source}
        GROUP BY loan_id
    )
    SELECT
        loan_id,
        vintage,
        CASE
            WHEN defaulted_in_window = 1 THEN 1        -- defaulted within 24 months
            WHEN max_age >= {window}      THEN 0        -- observed through the full window, clean
            ELSE NULL                                   -- censored: left the panel early, drop
        END AS default_label
    FROM agg
    """


def build_label(perf_source: str | None = None,
                con: duckdb.DuckDBPyConnection | None = None) -> duckdb.DuckDBPyRelation:
    """Return a DuckDB relation of (loan_id, vintage, default_label) for every loan.

    Rows with default_label NULL are censored and should be dropped before modelling;
    `drop_report()` quantifies how many and why.
    """
    con = con or duckdb.connect()
    source = perf_source or f"read_parquet('{PERF_GLOB}')"
    return con.sql(label_query(source))


def materialize_labels(con: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Write the retained (non-censored) labels to parquet; return a drop report."""
    con = con or duckdb.connect()
    rel = build_label(con=con)
    con.sql(f"""
        COPY (SELECT * FROM rel WHERE default_label IS NOT NULL)
        TO '{LABELS_PARQUET}' (FORMAT parquet)
    """)
    total, defaults, censored = con.sql("""
        SELECT count(*),
               count(*) FILTER (WHERE default_label = 1),
               count(*) FILTER (WHERE default_label IS NULL)
        FROM rel
    """).fetchone()
    kept = total - censored
    return {
        "loans_total": total,
        "loans_kept": kept,
        "loans_dropped_censored": censored,
        "defaults": defaults,
        "default_rate": round(defaults / kept, 5) if kept else None,
    }


if __name__ == "__main__":
    print(materialize_labels())
