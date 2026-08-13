"""FastAPI service (PLAN.md section 9). Mirrors the nfl-analytics service conventions.

Endpoints (implemented in Phase 7):
    GET  /health              liveness; keep-warm cron pings this
    GET  /metrics             AUC, KS, Brier before/after calibration, per experiment
    GET  /cutoff-curve        the precomputed sweep
    POST /score               a loan's origination features in, calibrated PD out
    GET  /vintage-performance metrics by origination year

Artifacts are served from artifacts/*.json so the site renders even when the model is cold.
"""
from fastapi import FastAPI

app = FastAPI(title="Mortgage Default Risk API", version="0.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}
