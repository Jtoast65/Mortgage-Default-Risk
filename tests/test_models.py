"""Model unit tests (PLAN.md Phase 3). Synthetic + data-independent."""
import numpy as np
import pandas as pd

from src import models
from src.models import fit_scorecard, ks_stat, make_logistic, metrics, score_scorecard


def test_metrics_perfect_separation():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.2, 0.8, 0.9])
    m = metrics(y, p)
    assert m["auc"] == 1.0
    assert m["ks"] == 1.0
    assert ks_stat(y, p) == 1.0


def test_scorecard_recovers_cell_rates():
    train = pd.DataFrame({
        "credit_score": [720] * 100 + [800] * 100,
        "original_ltv": [75] * 100 + [50] * 100,
        "default_label": [1] * 10 + [0] * 90 + [0] * 100,  # cell A 10%, cell B 0%
    })
    sc = fit_scorecard(train)
    preds = score_scorecard(sc, pd.DataFrame({
        "credit_score": [720, 800], "original_ltv": [75, 50]}))
    assert np.isclose(preds[0], 0.10)
    assert np.isclose(preds[1], 0.00)


def test_scorecard_falls_back_to_overall_for_unseen_cell():
    train = pd.DataFrame({
        "credit_score": [720] * 50, "original_ltv": [75] * 50,
        "default_label": [1] * 5 + [0] * 45,
    })
    sc = fit_scorecard(train)
    # A loan whose (FICO, LTV) cell never appeared in train -> overall rate, not NaN.
    pred = score_scorecard(sc, pd.DataFrame({"credit_score": [810], "original_ltv": [95]}))
    assert not np.isnan(pred[0])
    assert np.isclose(pred[0], sc["overall"])


def _synthetic_frame(n=200, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "credit_score": rng.integers(600, 820, n).astype(float),
        "original_ltv": rng.integers(40, 97, n).astype(float),
        "original_cltv": rng.integers(40, 97, n).astype(float),
        "original_dti": rng.integers(15, 50, n).astype(float),
        "original_upb": rng.integers(50_000, 500_000, n).astype(float),
        "original_interest_rate": rng.uniform(3, 7, n),
        "loan_term": np.full(n, 360.0),
        "number_of_units": np.ones(n),
        "number_of_borrowers": rng.integers(1, 3, n).astype(float),
        "mi_percent": np.zeros(n),
        "loan_purpose": rng.choice(["P", "C", "N"], n),
        "occupancy_status": rng.choice(["P", "I", "S"], n),
        "property_type": rng.choice(["SF", "CO", "PU"], n),
        "channel": rng.choice(["R", "B", "C"], n),
        "ppm_flag": rng.choice(["Y", "N"], n),
        "amortization_type": np.full(n, "FRM"),
        "property_state": rng.choice(["CA", "TX", "FL", "OH"], n),
        "first_time_homebuyer_flag": rng.choice(["Y", "N"], n),
        "credit_score_missing": np.zeros(n, dtype=np.int8),
    })
    # Signal: lower FICO -> higher default odds.
    prob = 1 / (1 + np.exp((df["credit_score"] - 700) / 40))
    df["default_label"] = (rng.random(n) < prob).astype(int)
    return df


def test_logistic_pipeline_fits_and_predicts_valid_proba():
    df = _synthetic_frame()
    pipe = make_logistic(df.columns)
    pipe.fit(df, df["default_label"])
    p = pipe.predict_proba(df)[:, 1]
    assert p.shape == (len(df),)
    assert np.all((p >= 0) & (p <= 1))


def test_experiment_split_uses_declared_vintages():
    df = pd.DataFrame({"vintage": [2009, 2010, 2015, 2018, 2020, 2022]})
    df["default_label"] = 0
    train, val, test = models.split_experiment(df, "A")
    assert set(train["vintage"]) == {2010, 2015}
    assert set(val["vintage"]) == {2018}
    assert set(test["vintage"]) == {2020}
