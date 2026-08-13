"""Probability calibration via isotonic regression (PLAN.md section 6).

Fit isotonic on the VALIDATION split only -- never train (overfits), never test (leakage).
XGBoost trained with scale_pos_weight ranks well but its raw scores are inflated (the class
weight distorts them); isotonic maps them back onto observed frequencies. We report Brier
before/after on the held-out TEST split and render the reliability curve with both curves
and the 45-degree line.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import joblib
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression

from src import models
from src.evaluate import _ACCENT, _BG, _GRID, _MUTED, _RED, _TEXT
from src.models import ARTIFACTS, MODELS_DIR, metrics, split_experiment

ROOT = Path(__file__).resolve().parent.parent


def plot_reliability(y_test, p_raw, p_cal, brier_raw, brier_cal, exp: str) -> None:
    """Reliability curve on test: raw vs isotonic-calibrated vs the 45-degree line."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Quantile bins -- the base rate is < 1%, so equal-width bins would be nearly empty.
    fr_raw, mp_raw = calibration_curve(y_test, p_raw, n_bins=10, strategy="quantile")
    fr_cal, mp_cal = calibration_curve(y_test, p_cal, n_bins=10, strategy="quantile")

    fig, ax = plt.subplots(figsize=(6.2, 6.2), dpi=140)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    hi = max(mp_raw.max(), fr_raw.max(), mp_cal.max(), fr_cal.max()) * 1.05
    ax.plot([0, hi], [0, hi], color=_MUTED, lw=1, ls="--", label="perfect calibration")
    ax.plot(mp_raw, fr_raw, color=_RED, lw=1.5, marker="o", ms=4,
            label=f"XGBoost raw (Brier {brier_raw:.5f})")
    ax.plot(mp_cal, fr_cal, color=_ACCENT, lw=1.5, marker="o", ms=4,
            label=f"+ isotonic (Brier {brier_cal:.5f})")

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(_GRID)
    ax.grid(True, color=_GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(colors=_MUTED, length=0)
    ax.set_xlim(0, hi)
    ax.set_ylim(0, hi)
    ax.set_xlabel("mean predicted probability", color=_MUTED, fontsize=10)
    ax.set_ylabel("observed default frequency", color=_MUTED, fontsize=10)
    ax.set_title(f"Reliability curve — Experiment {exp} (test)", color=_TEXT,
                 fontsize=13, loc="left", pad=12)
    leg = ax.legend(frameon=False, fontsize=9, loc="upper left")
    for txt in leg.get_texts():
        txt.set_color(_TEXT)
    fig.text(0.13, -0.01,
             f"Isotonic fit on validation only. Brier {brier_raw:.5f} -> {brier_cal:.5f} "
             f"({100*(brier_raw-brier_cal)/brier_raw:+.0f}%).",
             color=_MUTED, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / f"reliability_curve_{exp}.png", facecolor=_BG, bbox_inches="tight")
    plt.close(fig)


def run_calibrated_xgboost(exp: str = "A",
                           con: duckdb.DuckDBPyConnection | None = None) -> dict:
    df = models.load_modeling_frame(con)
    train, val, test = split_experiment(df, exp)

    clf, cats, cols = models.train_xgboost(train, val)
    p_val_raw = models.xgb_scores(clf, cats, cols, val)
    p_test_raw = models.xgb_scores(clf, cats, cols, test)

    # Isotonic fit on validation raw scores -> validation labels; applied to test.
    iso = IsotonicRegression(out_of_bounds="clip").fit(p_val_raw, val["default_label"])
    p_test_cal = iso.transform(p_test_raw)

    m_raw = metrics(test["default_label"], p_test_raw)
    m_cal = metrics(test["default_label"], p_test_cal)
    plot_reliability(test["default_label"], p_test_raw, p_test_cal,
                     m_raw["brier"], m_cal["brier"], exp)

    # Persist models and merge into metrics.json.
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(clf, MODELS_DIR / f"xgboost_{exp}.joblib")
    joblib.dump(iso, MODELS_DIR / f"isotonic_{exp}.joblib")
    joblib.dump(cats, MODELS_DIR / f"xgb_categories_{exp}.joblib")

    path = ARTIFACTS / "metrics.json"
    allm = json.loads(path.read_text()) if path.exists() else {}
    allm.setdefault(exp, {"experiment": exp}).setdefault("models", {})
    allm[exp]["models"]["xgboost"] = {"test": m_raw}
    allm[exp]["models"]["xgboost_calibrated"] = {"test": m_cal}
    allm[exp]["best_iteration"] = int(getattr(clf, "best_iteration", -1))
    path.write_text(json.dumps(allm, indent=2))

    return {"raw": m_raw, "calibrated": m_cal, "best_iteration": clf.best_iteration}


if __name__ == "__main__":
    import sys
    exp = sys.argv[1] if len(sys.argv) > 1 else "A"
    r = run_calibrated_xgboost(exp)
    raw, cal = r["raw"], r["calibrated"]
    print(f"XGBoost raw        AUC={raw['auc']:.4f}  KS={raw['ks']:.4f}  Brier={raw['brier']:.6f}")
    print(f"XGBoost+isotonic   AUC={cal['auc']:.4f}  KS={cal['ks']:.4f}  Brier={cal['brier']:.6f}")
    print(f"best_iteration={r['best_iteration']}")
