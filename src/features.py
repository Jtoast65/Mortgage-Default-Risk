"""Origination-only feature matrix, with the leakage guard.

Per PLAN.md section 4: features come exclusively from the origination file -- only what a
lender knows at underwriting. Coded sentinels (9, 999, 9999, spaces) map to null with an
explicit missing-indicator column; credit_score outside 300-850 is treated as missing.

The leakage guard (`assert_no_performance_leakage`) MUST fail the build if any column
sourced from the performance file appears in the feature matrix. Phase 2 acceptance
requires proving it fails on a deliberately bad feature matrix.
"""

# Columns permitted in the feature matrix (all from the origination file).
ALLOWED_FEATURES: list[str] = [
    "credit_score", "original_ltv", "original_cltv", "original_dti", "original_upb",
    "original_interest_rate", "loan_term", "loan_purpose", "occupancy_status",
    "property_type", "number_of_units", "number_of_borrowers", "first_time_homebuyer_flag",
    "mi_percent", "channel", "ppm_flag", "amortization_type", "property_state", "msa",
]


def assert_no_performance_leakage(feature_columns, performance_columns):
    """Fail the build if any performance-file column leaks into the feature matrix.

    TODO(Phase 2): implement. Must raise on any overlap with performance_columns and on any
    column not derivable from ALLOWED_FEATURES.
    """
    raise NotImplementedError("assert_no_performance_leakage() — Phase 2")
