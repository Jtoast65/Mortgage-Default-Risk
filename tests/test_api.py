"""API smoke tests (PLAN.md Phase 7). Exercises all five endpoints via TestClient.

Skips if the deployed model artifact is absent (raw data is gitignored, so a fresh clone
without `make experiments` cannot build it).
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import serving

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    not serving.deployed_path("A").exists(),
    reason="deployed model not built (run `python -m src.serving`)",
)


@pytest.fixture(scope="module")
def client():
    from api.main import app
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_metrics_has_both_experiments(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "A" in body and "B" in body
    assert body["A"]["models"]["logistic"]["test"]["auc"] > 0.7


def test_cutoff_curve(client):
    r = client.get("/cutoff-curve?experiment=A")
    assert r.status_code == 200
    body = r.json()
    assert len(body["curve"]) == 200
    assert "headline" in body


def test_cutoff_curve_rejects_bad_experiment(client):
    assert client.get("/cutoff-curve?experiment=Z").status_code == 422


def test_vintage_performance(client):
    r = client.get("/vintage-performance")
    assert r.status_code == 200
    assert any(row["vintage"] == 2007 for row in r.json())


def test_score_ranks_risky_above_safe(client):
    # Fully-specified loans (as the frontend form submits them).
    safe = {"credit_score": 800, "original_ltv": 50, "original_cltv": 50, "original_dti": 20,
            "original_upb": 200000, "original_interest_rate": 3.5, "loan_term": 360,
            "loan_purpose": "N", "occupancy_status": "P", "property_type": "SF",
            "number_of_units": 1, "number_of_borrowers": 2, "first_time_homebuyer_flag": "N",
            "mi_percent": 0, "channel": "R", "ppm_flag": "N", "amortization_type": "FRM",
            "property_state": "CA", "msa": "31080"}
    risky = {**safe, "credit_score": 600, "original_ltv": 95, "original_cltv": 97,
             "original_dti": 50, "original_interest_rate": 6.5, "loan_purpose": "C",
             "occupancy_status": "I", "mi_percent": 25, "property_state": "FL"}
    ps = client.post("/score", json=safe).json()
    pr = client.post("/score", json=risky).json()
    assert 0 <= ps["calibrated_pd"] <= 1
    assert pr["calibrated_pd"] > ps["calibrated_pd"]
    assert pr["expected_loss"] > 0
    assert ps["risk_band"] == "low"


def test_score_validates_input(client):
    # credit_score out of range -> 422 from the pydantic constraint.
    assert client.post("/score", json={"credit_score": 100}).status_code == 422
