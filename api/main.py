"""FastAPI service (PLAN.md section 9). Mirrors the nfl-analytics service conventions.

Endpoints:
    GET  /health              liveness; keep-warm cron pings this
    GET  /metrics             AUC, KS, Brier before/after calibration, per experiment
    GET  /cutoff-curve        the precomputed sweep (query: experiment=A|B)
    POST /score               a loan's origination features in, calibrated PD out
    GET  /vintage-performance default rate by origination year

Artifacts are served from artifacts/*.json (committed) and the deployed calibrated-logistic
model from models/ -- so the site renders and scores even when nothing is warm.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src import serving

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
DEPLOYED_EXPERIMENT = "A"          # modern regime is the deployed/headline model
LGD_FALLBACK = 0.4555

app = FastAPI(
    title="Mortgage Default Risk API",
    version="1.0.0",
    description="Calibrated probability of default on US mortgages, with loss economics.",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"],
)


# --------------------------------------------------------------------------- helpers

def _artifact(name: str) -> dict:
    path = ARTIFACTS / name
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"artifact not built: {name}")
    return json.loads(path.read_text())


@lru_cache(maxsize=1)
def _model():
    return serving.load(DEPLOYED_EXPERIMENT)


@lru_cache(maxsize=1)
def _lgd() -> float:
    try:
        return float(_artifact(f"cutoff_curve_{DEPLOYED_EXPERIMENT}.json")["lgd"])
    except Exception:
        return LGD_FALLBACK


# ---------------------------------------------------------------------------- schemas

class HealthResponse(BaseModel):
    status: str = "ok"
    experiment: str
    algorithm: str = "logistic + isotonic calibration"


class LoanFeatures(BaseModel):
    """Origination-only inputs (what a lender knows at underwriting). Missing -> None."""
    credit_score: int | None = Field(None, ge=300, le=850, examples=[720])
    original_ltv: float | None = Field(None, ge=1, le=200, examples=[80])
    original_cltv: float | None = Field(None, ge=1, le=200, examples=[80])
    original_dti: float | None = Field(None, ge=1, le=100, examples=[35])
    original_upb: float | None = Field(None, gt=0, examples=[250000])
    original_interest_rate: float | None = Field(None, ge=0, le=25, examples=[4.0])
    loan_term: int | None = Field(None, ge=1, le=600, examples=[360])
    loan_purpose: str | None = Field(None, examples=["P"])
    occupancy_status: str | None = Field(None, examples=["P"])
    property_type: str | None = Field(None, examples=["SF"])
    number_of_units: int | None = Field(None, ge=1, le=4, examples=[1])
    number_of_borrowers: int | None = Field(None, ge=1, le=10, examples=[2])
    first_time_homebuyer_flag: str | None = Field(None, examples=["N"])
    mi_percent: float | None = Field(None, ge=0, le=100, examples=[0])
    channel: str | None = Field(None, examples=["R"])
    ppm_flag: str | None = Field(None, examples=["N"])
    amortization_type: str | None = Field(None, examples=["FRM"])
    property_state: str | None = Field(None, examples=["CA"])
    msa: str | None = Field(None, examples=["31080"])


class ScoreResponse(BaseModel):
    calibrated_pd: float = Field(..., description="Calibrated 24-month probability of default")
    risk_band: str
    lgd: float = Field(..., description="Loss given default (empirical)")
    expected_loss: float = Field(..., description="EL = PD x LGD x original UPB, in dollars")


def _risk_band(pd_: float) -> str:
    if pd_ < 0.01:
        return "low"
    if pd_ < 0.04:
        return "moderate"
    if pd_ < 0.10:
        return "elevated"
    return "high"


# -------------------------------------------------------------------------- endpoints

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(experiment=DEPLOYED_EXPERIMENT)


@app.get("/metrics")
def metrics():
    """AUC / KS / Brier per experiment and per model (raw and calibrated)."""
    return _artifact("metrics.json")


@app.get("/cutoff-curve")
def cutoff_curve(experiment: str = Query("A", pattern="^[AB]$")):
    """Precomputed approval-cutoff sweep for the dashboard slider."""
    return _artifact(f"cutoff_curve_{experiment}.json")


@app.get("/vintage-performance")
def vintage_performance():
    """Default rate by origination vintage."""
    return _artifact("vintage_default_rate.json")


@app.post("/score", response_model=ScoreResponse)
def score(loan: LoanFeatures):
    """Calibrated probability of default and expected loss for one loan."""
    pd_ = serving.score(_model(), loan.model_dump())
    lgd = _lgd()
    ead = loan.original_upb or 0.0
    return ScoreResponse(
        calibrated_pd=round(pd_, 5),
        risk_band=_risk_band(pd_),
        lgd=lgd,
        expected_loss=round(pd_ * lgd * ead, 2),
    )
