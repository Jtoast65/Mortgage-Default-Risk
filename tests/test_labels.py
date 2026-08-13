"""Hand-checked unit tests for build_label() (PLAN.md Phase 2, section 3).

Each synthetic loan is a small monthly performance panel whose correct label is known by
inspection. Columns match what label_query reads: loan_id, vintage, loan_age,
current_delinquency_status, zero_balance_code.
"""
import duckdb
import pandas as pd

from src import labels

COLS = ["loan_id", "vintage", "loan_age", "current_delinquency_status", "zero_balance_code"]


def _months(loan_id, ages, status="00", zb_at_last=None):
    """One row per month; optionally attach a zero-balance code to the final month."""
    rows = []
    for i, age in enumerate(ages):
        st = status[i] if isinstance(status, list) else status
        zb = zb_at_last if age == ages[-1] else None
        rows.append((loan_id, 2007, age, st, zb))
    return rows


def _label_map(rows):
    con = duckdb.connect()
    con.register("perf_test", pd.DataFrame(rows, columns=COLS))
    out = labels.build_label(perf_source="perf_test", con=con).df()
    return {r.loan_id: r.default_label for r in out.itertuples()}


def test_hand_checked_label_cases():
    rows = []
    # Clean loan observed well past the window -> survived, label 0.
    rows += _months("clean", list(range(0, 31)))
    # Hits 180+ DPD (status 06) at month 10, inside the window -> default, label 1.
    rows += _months("d180", list(range(0, 11)), status=["00"] * 10 + ["06"])
    # REO disposition (zero balance 09) at month 18 -> default, label 1.
    rows += _months("reo", list(range(0, 19)), zb_at_last="09")
    # Voluntary prepay (zero balance 01) at month 12, clean -> censored, dropped (NULL).
    rows += _months("prepay", list(range(0, 13)), zb_at_last="01")
    # Recent origination, clean, only observed to month 15 -> censored, dropped (NULL).
    rows += _months("recent", list(range(0, 16)))
    # Default AFTER the window (status 06 at month 30), clean through 24 -> label 0.
    rows += _months("late", list(range(0, 37)), status=["00"] * 36 + ["06"])
    # REO Acquisition status 'RA' at month 20 -> default, label 1.
    rows += _months("ra", list(range(0, 21)), status=["00"] * 20 + ["RA"])

    m = _label_map(rows)
    assert m["clean"] == 0
    assert m["d180"] == 1
    assert m["reo"] == 1
    assert pd.isna(m["prepay"]), "early clean prepay must be censored/dropped"
    assert pd.isna(m["recent"]), "un-observable recent loan must be censored/dropped"
    assert m["late"] == 0, "a default after month 24 is not a within-window default"
    assert m["ra"] == 1


def test_window_boundary_is_respected():
    # Default exactly at month 24 counts; at month 25 it does not.
    rows = _months("at24", list(range(0, 26)), status=["00"] * 24 + ["06", "00"])
    rows += _months("at25", list(range(0, 30)), status=["00"] * 25 + ["06"] + ["00"] * 4)
    m = _label_map(rows)
    assert m["at24"] == 1
    assert m["at25"] == 0
