"""Ingest smoke test (PLAN.md Phase 1).

Data-optional: the raw Freddie Mac files are gitignored, so these tests skip when the
processed parquet is absent (e.g. on a fresh clone / CI) and run when it is present.
"""
from pathlib import Path

import pytest

from src import layouts

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"


def _parquet(kind: str, year: int) -> Path:
    return PROCESSED / kind / f"vintage={year}" / "data.parquet"


pytestmark = pytest.mark.skipif(
    not _parquet("origination", 2010).exists(),
    reason="processed parquet not present (raw data is gitignored)",
)


def test_origination_parquet_has_layout_columns_plus_vintage():
    import duckdb
    cols = duckdb.sql(f"SELECT * FROM read_parquet('{_parquet('origination', 2010)}') LIMIT 0").columns
    assert cols == layouts.ORIGINATION_LAYOUT + ["vintage"]


def test_performance_parquet_has_layout_columns_plus_vintage():
    import duckdb
    cols = duckdb.sql(f"SELECT * FROM read_parquet('{_parquet('performance', 2010)}') LIMIT 0").columns
    assert cols == layouts.PERFORMANCE_LAYOUT + ["vintage"]


def test_sample_is_50k_loans_per_full_vintage():
    import duckdb
    (n,) = duckdb.sql(
        f"SELECT count(*) FROM read_parquet('{_parquet('origination', 2010)}')"
    ).fetchone()
    assert n == 50_000
