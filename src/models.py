"""Models reported side by side (PLAN.md section 6): scorecard, logistic, [XGBoost=Phase 4].

    1. Scorecard baseline -- bin FICO and LTV, observed default rate per cell. What the
       industry actually used for decades; crude but interpretable.
    2. Logistic regression -- full feature set, standardised numerics, one-hot categoricals.
       The encoder/scaler are fit on TRAIN only (no leakage across the vintage split).

Experiment A (modern regime) produces the headline numbers. Splits are strictly by
origination vintage -- never random (PLAN.md sections 1, 5).
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src import features as F
from src import labels as L
from src.features import CATEGORICAL_FEATURES, NUMERIC_RANGES

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
MODELS_DIR = ROOT / "models"

# Vintage splits per experiment (inclusive ranges). Never a random split.
EXPERIMENTS = {
    "A": {"train": range(2010, 2018), "val": range(2018, 2020), "test": range(2020, 2022)},
    "B": {"train": range(1999, 2006), "val": range(2006, 2007), "test": range(2007, 2010)},
}

# Scorecard bins: standard credit tiers and LTV bands.
FICO_BINS = [300, 620, 660, 700, 740, 780, 851]
LTV_BINS = [0, 60, 70, 80, 90, 95, 200]

NUMERIC_COLS = list(NUMERIC_RANGES)
# msa is dropped from the linear model (hundreds of levels); XGBoost uses it natively.
LOGISTIC_CATEGORICALS = [c for c in CATEGORICAL_FEATURES if c != "msa"]


# --------------------------------------------------------------------------- data

def load_modeling_frame(con: duckdb.DuckDBPyConnection | None = None) -> pd.DataFrame:
    """Origination features inner-joined to the (non-censored) default label."""
    con = con or duckdb.connect()
    feats = F.build_feature_matrix(con=con)
    labs = L.build_label(con=con).df()
    labs = labs[labs["default_label"].notna()][["loan_id", "default_label"]]
    df = feats.merge(labs, on="loan_id", how="inner")
    df["default_label"] = df["default_label"].astype(int)
    # Categoricals -> object with np.nan so sklearn's imputer/encoder handle them.
    for c in LOGISTIC_CATEGORICALS:
        df[c] = df[c].astype(object).where(df[c].notna(), np.nan)
    return df


def split_experiment(df: pd.DataFrame, exp: str = "A"):
    cfg = EXPERIMENTS[exp]
    pick = lambda years: df[df["vintage"].isin(list(years))]
    return pick(cfg["train"]), pick(cfg["val"]), pick(cfg["test"])


# ----------------------------------------------------------------------- scorecard

def fit_scorecard(train: pd.DataFrame) -> dict:
    t = train.copy()
    t["fico_bin"] = pd.cut(t["credit_score"], FICO_BINS, include_lowest=True)
    t["ltv_bin"] = pd.cut(t["original_ltv"], LTV_BINS, include_lowest=True)
    cell = t.groupby(["fico_bin", "ltv_bin"], observed=False)["default_label"].mean()
    return {"cell": cell, "overall": float(t["default_label"].mean())}


def score_scorecard(model: dict, X: pd.DataFrame) -> np.ndarray:
    x = pd.DataFrame({
        "fico_bin": pd.cut(X["credit_score"], FICO_BINS, include_lowest=True),
        "ltv_bin": pd.cut(X["original_ltv"], LTV_BINS, include_lowest=True),
    })
    s = x.join(model["cell"].rename("score"), on=["fico_bin", "ltv_bin"])["score"]
    return s.fillna(model["overall"]).to_numpy()


# ------------------------------------------------------------------------ logistic

def make_logistic(columns) -> Pipeline:
    missing_cols = [c for c in columns if c.endswith("_missing")]
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                          ("sc", StandardScaler())]), NUMERIC_COLS),
        ("miss", "passthrough", missing_cols),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="constant", fill_value="MISSING")),
                          ("ohe", OneHotEncoder(handle_unknown="ignore", min_frequency=50))]),
         LOGISTIC_CATEGORICALS),
    ], remainder="drop")
    return Pipeline([("pre", pre),
                     ("clf", LogisticRegression(max_iter=2000))])


# ------------------------------------------------------------------------- xgboost

def xgb_feature_frame(df: pd.DataFrame, categories: dict | None = None):
    """Build the XGBoost design matrix with native dtypes.

    Numerics stay float (NaN preserved -- XGBoost handles missing natively); every
    categorical, INCLUDING high-cardinality msa, becomes a pandas category. Passing
    `categories` from the train split pins the category set so val/test encode identically
    and unseen levels map to missing -- no target encoding, so no leakage.
    """
    X = pd.DataFrame(index=df.index)
    for c in NUMERIC_COLS:
        X[c] = pd.to_numeric(df[c], errors="coerce")
    for c in [c for c in df.columns if c.endswith("_missing")]:
        X[c] = df[c].astype(float)
    out_cats = {}
    for c in CATEGORICAL_FEATURES:
        s = df[c].astype("object")
        if categories is None:
            col = s.astype("category")
        else:
            # Null out unseen levels first, then pin -- no leakage, no deprecation warning.
            col = pd.Categorical(s.where(s.isin(categories[c])), categories=categories[c])
        X[c] = col
        out_cats[c] = X[c].cat.categories if categories is None else pd.Index(categories[c])
    return X, out_cats


def train_xgboost(train: pd.DataFrame, val: pd.DataFrame):
    """Fit XGBoost with scale_pos_weight for imbalance and early stopping on validation."""
    from xgboost import XGBClassifier

    Xtr, cats = xgb_feature_frame(train)
    Xva, _ = xgb_feature_frame(val, cats)
    Xva = Xva[Xtr.columns]
    ytr, yva = train["default_label"], val["default_label"]
    spw = float((ytr == 0).sum() / max((ytr == 1).sum(), 1))

    # Early-stop on AUC, not logloss: the validation split (2018-19) carries a COVID-
    # inflated base rate, so logloss is a poor stopping guide there; AUC targets the ranking
    # we actually report and is robust to the base-rate shift. scale_pos_weight is kept per
    # spec -- it inflates the raw scores, which isotonic calibration then corrects.
    clf = XGBClassifier(
        n_estimators=1000, max_depth=5, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        reg_lambda=1.0, tree_method="hist", enable_categorical=True,
        eval_metric="auc", early_stopping_rounds=50,
        scale_pos_weight=spw, random_state=42,
    )
    clf.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    return clf, cats, list(Xtr.columns)


def xgb_scores(clf, cats, cols, split: pd.DataFrame) -> np.ndarray:
    X, _ = xgb_feature_frame(split, cats)
    return clf.predict_proba(X[cols])[:, 1]


# ------------------------------------------------------------------------- metrics

def ks_stat(y, p) -> float:
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr - fpr))


def metrics(y, p) -> dict:
    return {
        "n": int(len(y)),
        "base_rate": round(float(np.mean(y)), 5),
        "auc": round(float(roc_auc_score(y, p)), 4),
        "ks": round(ks_stat(y, p), 4),
        "brier": round(float(brier_score_loss(y, p)), 6),
    }


# ---------------------------------------------------------------------- experiment

def run_experiment(exp: str = "A", con: duckdb.DuckDBPyConnection | None = None) -> dict:
    df = load_modeling_frame(con)
    train, val, test = split_experiment(df, exp)

    scorecard = fit_scorecard(train)
    logistic = make_logistic(train.columns)
    logistic.fit(train, train["default_label"])

    scorers = {
        "scorecard": lambda X: score_scorecard(scorecard, X),
        "logistic": lambda X: logistic.predict_proba(X)[:, 1],
    }
    models_out = {
        name: {"validation": metrics(val["default_label"], sc(val)),
               "test": metrics(test["default_label"], sc(test))}
        for name, sc in scorers.items()
    }

    result = {
        "experiment": exp,
        "split": {k: [min(v), max(v)] for k, v in EXPERIMENTS[exp].items()},
        "counts": {"train": len(train), "validation": len(val), "test": len(test)},
        "models": models_out,
    }

    # Persist models and metrics.
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(logistic, MODELS_DIR / f"logistic_{exp}.joblib")
    joblib.dump(scorecard, MODELS_DIR / f"scorecard_{exp}.joblib")
    ARTIFACTS.mkdir(exist_ok=True)
    path = ARTIFACTS / "metrics.json"
    allm = json.loads(path.read_text()) if path.exists() else {}
    allm[exp] = result
    path.write_text(json.dumps(allm, indent=2))
    return result


if __name__ == "__main__":
    import sys
    exp = sys.argv[1] if len(sys.argv) > 1 else "A"
    r = run_experiment(exp)
    for name, m in r["models"].items():
        t = m["test"]
        print(f"{name:10s}  test  AUC={t['auc']:.4f}  KS={t['ks']:.4f}  "
              f"Brier={t['brier']:.5f}  (n={t['n']:,}, base={t['base_rate']:.3%})")
