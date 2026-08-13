"""Origination-only feature matrix, with the leakage guard (PLAN.md section 4).

Features come exclusively from the origination file -- only what a lender knows at
underwriting. Coded sentinels map to null with an explicit missing-indicator column
(never silent imputation); credit_score outside 300-850 is treated as missing.

`assert_no_performance_leakage` is the build's safety catch: it raises if any column in the
feature matrix is sourced from the performance file, or is not a permitted origination
feature. Nothing downstream can bypass it by accident.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from src.layouts import ORIGINATION_LAYOUT, PERFORMANCE_LAYOUT

ROOT = Path(__file__).resolve().parent.parent
ORIG_GLOB = str(ROOT / "data" / "processed" / "origination" / "*" / "data.parquet")

# Keys that are not features but legitimately travel with the matrix (present in both files).
KEY_COLUMNS = {"loan_id", "vintage"}

# Columns permitted in the feature matrix (all from the origination file).
ALLOWED_FEATURES: list[str] = [
    "credit_score", "original_ltv", "original_cltv", "original_dti", "original_upb",
    "original_interest_rate", "loan_term", "loan_purpose", "occupancy_status",
    "property_type", "number_of_units", "number_of_borrowers", "first_time_homebuyer_flag",
    "mi_percent", "channel", "ppm_flag", "amortization_type", "property_state", "msa",
]

# Numeric features and their valid ranges (inclusive). Values outside -> missing.
# Ranges are set to exclude the coded sentinels (9 / 999 / 9999) documented in the guide.
NUMERIC_RANGES: dict[str, tuple[float, float]] = {
    "credit_score": (300, 850),          # 9999 sentinel and out-of-range -> missing
    "original_ltv": (1, 998),            # 999 = not available
    "original_cltv": (1, 998),           # 999 = not available
    "original_dti": (1, 998),            # 999 = not available
    "mi_percent": (0, 998),              # 000 = no MI (valid); 999 = not available
    "number_of_units": (1, 4),           # 99 = not available
    "number_of_borrowers": (1, 10),      # 99 = not available
    "original_upb": (1, 1e9),
    "original_interest_rate": (0.01, 25),
    "loan_term": (1, 600),
}
CATEGORICAL_FEATURES: list[str] = [
    "loan_purpose", "occupancy_status", "property_type", "channel", "ppm_flag",
    "amortization_type", "property_state", "first_time_homebuyer_flag", "msa",
]
# Coded-missing tokens for categoricals (space, and 9-filled unknowns).
CATEGORICAL_MISSING = {"", " ", "9", "99", "999", "9999", "X", "XX"}


class LeakageError(AssertionError):
    """Raised when a performance-sourced or non-permitted column reaches the feature matrix."""


def assert_no_performance_leakage(feature_columns,
                                  performance_columns=PERFORMANCE_LAYOUT) -> None:
    """Fail the build if any feature column is performance-sourced or not on the allow-list.

    A `<feature>_missing` indicator is accepted iff `<feature>` is permitted. Key columns
    (loan_id, vintage) are allowed through as identifiers, not features.
    """
    perf = set(performance_columns) - KEY_COLUMNS  # loan_id is in both files; not leakage
    allowed = set(ALLOWED_FEATURES)
    for col in feature_columns:
        if col in KEY_COLUMNS:
            continue
        base = col[:-len("_missing")] if col.endswith("_missing") else col
        if base in perf:
            raise LeakageError(f"performance-file column in feature matrix: {col!r}")
        if base not in allowed:
            raise LeakageError(f"column not in origination allow-list: {col!r}")


def build_feature_matrix(orig_source: str | None = None,
                         con: duckdb.DuckDBPyConnection | None = None) -> pd.DataFrame:
    """Load origination parquet, clean sentinels, add missing indicators, guard leakage."""
    con = con or duckdb.connect()
    source = orig_source or f"read_parquet('{ORIG_GLOB}')"
    cols = ", ".join(["loan_id", "vintage", *ALLOWED_FEATURES])
    df = con.sql(f"SELECT {cols} FROM {source}").df()

    # Numeric: coerce, then null out anything outside the valid range (kills sentinels).
    for col, (lo, hi) in NUMERIC_RANGES.items():
        x = pd.to_numeric(df[col], errors="coerce")
        df[col] = x.where((x >= lo) & (x <= hi))

    # Categorical: strip, map coded-missing tokens to null.
    for col in CATEGORICAL_FEATURES:
        s = df[col].astype("string").str.strip()
        df[col] = s.where(~s.isin(CATEGORICAL_MISSING))

    # Explicit missing indicators (only for features that actually have missings).
    for col in ALLOWED_FEATURES:
        if df[col].isna().any():
            df[f"{col}_missing"] = df[col].isna().astype(np.int8)

    assert_no_performance_leakage(df.columns)
    return df


if __name__ == "__main__":
    m = build_feature_matrix()
    print(f"feature matrix: {len(m):,} loans x {m.shape[1]} columns")
    miss = [c for c in m.columns if c.endswith("_missing")]
    print(f"missing-indicator columns: {len(miss)} -> {miss}")
