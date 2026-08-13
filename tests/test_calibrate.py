"""Calibration tests (PLAN.md Phase 4). Synthetic + data-independent."""
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

from src import features, models


def test_isotonic_on_val_reduces_test_brier_for_inflated_scores():
    # Monotonic but inflated scores (a stand-in for scale_pos_weight output): ranking is
    # right, magnitudes are too high. Isotonic fit on val should fix magnitudes on test.
    rng = np.random.default_rng(0)
    n = 8000
    latent = rng.normal(size=n)
    y = rng.binomial(1, 1 / (1 + np.exp(-(latent - 2.5))))     # low base rate
    inflated = 1 / (1 + np.exp(-latent))                        # same ranking, too high
    val, test = slice(0, n // 2), slice(n // 2, n)

    iso = IsotonicRegression(out_of_bounds="clip").fit(inflated[val], y[val])
    cal_test = iso.transform(inflated[test])

    brier_raw = brier_score_loss(y[test], inflated[test])
    brier_cal = brier_score_loss(y[test], cal_test)
    assert brier_cal < brier_raw
    assert brier_cal < 0.5 * brier_raw          # a large, not marginal, improvement


def test_isotonic_barely_changes_ranking():
    # Isotonic is monotonic, so ordering is preserved; it only introduces ties (plateaus),
    # which nudge AUC by a hair. The improvement is in probabilities, not discrimination.
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(1)
    n = 4000
    p = rng.random(n)
    y = rng.binomial(1, p * 0.1)
    iso = IsotonicRegression(out_of_bounds="clip").fit(p, y)
    assert abs(roc_auc_score(y, p) - roc_auc_score(y, iso.transform(p))) < 0.02


def _tiny_orig_frame():
    row = {c: "1" for c in features.ALLOWED_FEATURES}
    row.update(loan_id="L1", vintage=2015, credit_score="740", original_ltv="80",
               loan_purpose="P", property_state="CA", msa="31080", default_label=0)
    row2 = dict(row, loan_id="L2", credit_score="680", property_state="TX", msa="12060",
                default_label=1)
    df = pd.DataFrame([row, row2])
    for c in features.NUMERIC_RANGES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def test_xgb_feature_frame_types_and_category_pinning():
    df = _tiny_orig_frame()
    X, cats = models.xgb_feature_frame(df)
    # Numerics stay numeric, every categorical (incl. msa) is a pandas category.
    assert is_numeric_dtype(X["credit_score"])
    for c in features.CATEGORICAL_FEATURES:
        assert isinstance(X[c].dtype, pd.CategoricalDtype)
    assert "msa" in cats
    # Pinning categories from a prior split constrains encoding; unseen -> NaN category.
    X2, _ = models.xgb_feature_frame(
        pd.DataFrame([dict(zip(df.columns, df.iloc[0]))]).assign(property_state="ZZ"),
        categories=cats,
    )
    assert pd.isna(X2["property_state"]).all()   # 'ZZ' not in pinned categories
