"""Parse the raw pipe-delimited Freddie Mac sample files into parquet (PLAN.md Phase 1).

The sample dataset ships two files per origination year in data/raw/:
    sample_orig_YYYY.txt   -> data/processed/origination/vintage=YYYY/data.parquet
    sample_perf_YYYY.txt   -> data/processed/performance/vintage=YYYY/data.parquet

DuckDB does the parsing: it reads the delimited text out-of-core (the performance files are
~3.5M rows each, ~90M total) and writes parquet directly, so nothing has to fit in RAM.

Every column is read as VARCHAR -- a faithful, lossless dump. Sentinel handling, missing
indicators, and numeric casting happen downstream in features.py / labels.py, never here.
The parquet is hive-partitioned by `vintage`, so downstream code can glob all years at once
and get the origination year for free.

Run:  python -m src.ingest            # all vintages found in data/raw/
      python -m src.ingest 2010       # a single vintage
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

from src.layouts import ORIGINATION_LAYOUT, PERFORMANCE_LAYOUT

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def _columns_sql(names: list[str]) -> str:
    """DuckDB read_csv `columns` struct: every field VARCHAR, in layout order."""
    return "{" + ", ".join(f"'{n}': 'VARCHAR'" for n in names) + "}"


def _ingest_one(con: duckdb.DuckDBPyConnection, src: Path, names: list[str],
                out_dir: Path, vintage: int) -> int:
    """Parse one pipe-delimited file to a single parquet, return the row count."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.parquet"
    con.execute(
        f"""
        COPY (
            SELECT *, {vintage} AS vintage
            FROM read_csv(
                ?,
                delim = '|',
                header = false,
                columns = {_columns_sql(names)},
                nullstr = '',
                quote = '',
                ignore_errors = false
            )
        ) TO '{out_file}' (FORMAT parquet, COMPRESSION zstd);
        """,
        [str(src)],
    )
    (rows,) = con.execute(f"SELECT count(*) FROM read_parquet('{out_file}')").fetchone()
    return rows


def ingest_vintage(year: int, con: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Ingest both files for one origination year. Returns row counts, with a raw cross-check."""
    con = con or duckdb.connect()
    orig_src = RAW_DIR / f"sample_orig_{year}.txt"
    perf_src = RAW_DIR / f"sample_perf_{year}.txt"
    if not orig_src.exists() or not perf_src.exists():
        raise FileNotFoundError(f"missing sample files for {year} in {RAW_DIR}")

    orig_rows = _ingest_one(con, orig_src, ORIGINATION_LAYOUT,
                            PROCESSED_DIR / "origination" / f"vintage={year}", year)
    perf_rows = _ingest_one(con, perf_src, PERFORMANCE_LAYOUT,
                            PROCESSED_DIR / "performance" / f"vintage={year}", year)

    # Cross-check against the raw line counts -- the parser must not silently drop rows.
    raw_orig = sum(1 for _ in orig_src.open("rb"))
    raw_perf = sum(1 for _ in perf_src.open("rb"))
    assert orig_rows == raw_orig, f"{year} orig: parquet {orig_rows} != raw {raw_orig}"
    assert perf_rows == raw_perf, f"{year} perf: parquet {perf_rows} != raw {raw_perf}"

    return {"year": year, "orig_rows": orig_rows, "perf_rows": perf_rows}


def discover_vintages() -> list[int]:
    return sorted(int(p.stem.split("_")[-1]) for p in RAW_DIR.glob("sample_orig_*.txt"))


def ingest_all() -> list[dict]:
    con = duckdb.connect()
    results = []
    for year in discover_vintages():
        r = ingest_vintage(year, con)
        results.append(r)
        print(f"  {year}: orig {r['orig_rows']:>7,}  perf {r['perf_rows']:>12,}")
    total_perf = sum(r["perf_rows"] for r in results)
    print(f"ingested {len(results)} vintages, {total_perf:,} performance rows total")
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(ingest_vintage(int(sys.argv[1])))
    else:
        ingest_all()
