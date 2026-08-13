"""Layout spec tests (PLAN.md Phase 1). Data-independent -- pass on a fresh clone."""
from src import features, layouts


def test_column_counts_match_official_layout():
    # From file_layout_july_2026.xlsx and the header files: 31 orig, 35 perf.
    assert len(layouts.ORIGINATION_LAYOUT) == 31
    assert len(layouts.PERFORMANCE_LAYOUT) == 35


def test_no_duplicate_columns():
    assert len(set(layouts.ORIGINATION_LAYOUT)) == 31
    assert len(set(layouts.PERFORMANCE_LAYOUT)) == 35


def test_allowed_features_are_all_origination_columns():
    # Every permitted feature must exist in the origination file -- nothing invented.
    missing = set(features.ALLOWED_FEATURES) - set(layouts.ORIGINATION_LAYOUT)
    assert not missing, f"features not in origination layout: {missing}"


def test_allowed_features_share_nothing_with_performance():
    # The leakage line: no origination feature may collide with a performance column.
    leak = set(features.ALLOWED_FEATURES) & set(layouts.PERFORMANCE_LAYOUT)
    assert not leak, f"features overlap performance file (leakage): {leak}"


def test_label_code_constants_present():
    assert layouts.DELINQUENCY_DEFAULT_THRESHOLD == 6           # 180+ DPD
    assert layouts.DEFAULT_ZERO_BALANCE_CODES == {"03", "09"}   # short sale/charge-off, REO
    assert layouts.PREPAY_ZERO_BALANCE_CODES == {"01"}          # competing-risk prepayment
    assert layouts.OBSERVATION_WINDOW_MONTHS == 24
