"""Deployed model for the /score endpoint: calibrated logistic (PLAN.md sections 6, 9).

Persists the logistic pipeline + its isotonic calibrator + the exact feature schema the
pipeline was fit on, so a single loan can be scored identically to training. The API loads
this rather than retraining on cold start.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import joblib
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from src import features as F
from src import models
from src.models import MODELS_DIR, make_logistic, split_experiment

ROOT = Path(__file__).resolve().parent.parent


def deployed_path(exp: str = "A") -> Path:
    return MODELS_DIR / f"deployed_logistic_{exp}.joblib"


def build_and_save(exp: str = "A", con: duckdb.DuckDBPyConnection | None = None) -> Path:
    """Fit the deployed calibrated logistic and persist it with its feature schema."""
    con = con or duckdb.connect()
    df = models.load_modeling_frame(con)
    train, val, _ = split_experiment(df, exp)

    pipe = make_logistic(train.columns)
    pipe.fit(train, train["default_label"])
    iso = IsotonicRegression(out_of_bounds="clip").fit(
        pipe.predict_proba(val)[:, 1], val["default_label"])

    missing_cols = [c for c in train.columns if c.endswith("_missing")]
    bundle = {
        "experiment": exp,
        "pipeline": pipe,
        "isotonic": iso,
        "missing_columns": missing_cols,
        "allowed_features": F.ALLOWED_FEATURES,
    }
    MODELS_DIR.mkdir(exist_ok=True)
    path = deployed_path(exp)
    joblib.dump(bundle, path)
    return path


def load(exp: str = "A"):
    return joblib.load(deployed_path(exp))


def score(bundle: dict, raw: dict) -> float:
    """Calibrated PD for one loan given a dict of raw origination features."""
    row = {c: raw.get(c) for c in bundle["allowed_features"]}
    df = pd.DataFrame([row])
    df = F.clean_features(df, missing_columns=bundle["missing_columns"])
    raw_pd = bundle["pipeline"].predict_proba(df)[:, 1]
    return float(bundle["isotonic"].transform(raw_pd)[0])


if __name__ == "__main__":
    p = build_and_save("A")
    b = load("A")
    demo = {"credit_score": 720, "original_ltv": 80, "original_cltv": 80, "original_dti": 35,
            "original_upb": 250000, "original_interest_rate": 4.0, "loan_term": 360,
            "loan_purpose": "P", "occupancy_status": "P", "property_type": "SF",
            "number_of_units": 1, "number_of_borrowers": 2, "first_time_homebuyer_flag": "N",
            "mi_percent": 0, "channel": "R", "ppm_flag": "N", "amortization_type": "FRM",
            "property_state": "CA", "msa": "31080"}
    print(f"saved {p.name}; demo loan calibrated PD = {score(b, demo):.4f}")
