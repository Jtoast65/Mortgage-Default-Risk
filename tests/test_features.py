"""Leakage guard and sentinel-cleaning tests (PLAN.md Phase 2, section 4)."""
import duckdb
import pandas as pd
import pytest

from src import features
from src.features import LeakageError, assert_no_performance_leakage


def test_leakage_assertion_fails_on_performance_column():
    # The deliberately bad matrix the plan requires: a performance field slipped in.
    bad = ["loan_id", "credit_score", "current_delinquency_status"]
    with pytest.raises(LeakageError, match="performance-file column"):
        assert_no_performance_leakage(bad)


def test_leakage_assertion_fails_on_zero_balance_code():
    with pytest.raises(LeakageError):
        assert_no_performance_leakage(["credit_score", "zero_balance_code"])


def test_leakage_assertion_fails_on_unknown_column():
    with pytest.raises(LeakageError, match="allow-list"):
        assert_no_performance_leakage(["credit_score", "made_up_feature"])


def test_clean_matrix_passes():
    good = ["loan_id", "vintage", "credit_score", "credit_score_missing",
            "original_ltv", "loan_purpose", "property_state"]
    assert_no_performance_leakage(good) is None  # does not raise


def test_sentinels_become_missing_with_indicator():
    # Two loans: one clean, one all-sentinel. Only ALLOWED_FEATURES columns are needed.
    clean = {c: "1" for c in features.ALLOWED_FEATURES}
    clean.update(loan_id="L1", vintage=2015, credit_score="740", original_dti="35",
                 loan_purpose="P", original_upb="200000", original_interest_rate="4.0",
                 loan_term="360", original_ltv="80", original_cltv="80", mi_percent="0",
                 number_of_units="1", number_of_borrowers="2")
    sentinel = {c: "9" for c in features.ALLOWED_FEATURES}
    sentinel.update(loan_id="L2", vintage=2015, credit_score="9999", original_dti="999",
                    loan_purpose="9", original_upb="150000", original_interest_rate="5.0",
                    loan_term="360", original_ltv="999", original_cltv="999",
                    mi_percent="999", number_of_units="1", number_of_borrowers="1")
    df = pd.DataFrame([clean, sentinel])

    con = duckdb.connect()
    con.register("orig_test", df)
    out = features.build_feature_matrix(orig_source="orig_test", con=con)
    row = out.set_index("loan_id")

    # Sentinels on L2 mapped to null; clean L1 preserved.
    assert row.loc["L1", "credit_score"] == 740
    assert pd.isna(row.loc["L2", "credit_score"])       # 9999 -> missing
    assert pd.isna(row.loc["L2", "original_dti"])       # 999  -> missing
    assert pd.isna(row.loc["L2", "loan_purpose"])       # '9'  -> missing
    # Missing indicator is present and set for the sentinel loan.
    assert row.loc["L2", "credit_score_missing"] == 1
    assert row.loc["L1", "credit_score_missing"] == 0
