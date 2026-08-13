"""Phase 0 sanity checks. Real assertions so `pytest` is green but not vacuous.

Everything substantive (label logic, leakage guard, metrics) is tested in later phases.
"""
from pathlib import Path

from src import features

ROOT = Path(__file__).resolve().parent.parent


def test_repo_structure_exists():
    for d in ["src", "api", "web", "tests", "artifacts", "data", "scripts"]:
        assert (ROOT / d).is_dir(), f"missing directory: {d}"


def test_plan_is_committed_at_root():
    assert (ROOT / "PLAN.md").is_file(), "PLAN.md must live at the repo root"


def test_data_dir_is_gitignored():
    gitignore = (ROOT / ".gitignore").read_text()
    assert "data/*" in gitignore, "raw Freddie Mac data must never be committed"


def test_allowed_features_are_origination_only():
    # Guards against a performance-file column being pasted into the allow-list by accident.
    forbidden = {"current_upb", "loan_age", "delinquency_status", "zero_balance_code"}
    assert forbidden.isdisjoint(features.ALLOWED_FEATURES)
    assert "credit_score" in features.ALLOWED_FEATURES
