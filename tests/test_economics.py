"""Cutoff-sweep economics tests (PLAN.md Phase 5). Synthetic + data-independent."""
import numpy as np

from src.economics import sweep


def test_sweep_endpoints_and_monotonicity():
    pd_arr = np.array([0.1, 0.2, 0.3, 0.9])
    y = np.array([0, 0, 1, 1])
    ead = np.full(4, 100.0)
    df = sweep(pd_arr, y, ead, lgd=0.5, steps=200)
    assert df.iloc[0]["approval_rate"] == 0.0      # cutoff 0 approves nobody
    assert df.iloc[-1]["approval_rate"] == 1.0      # cutoff 1 approves everyone
    ar = df["approval_rate"].to_numpy()
    assert np.all(np.diff(ar) >= 0)                 # approval rate is non-decreasing


def test_accounting_at_full_approval():
    pd_arr = np.array([0.1, 0.5, 0.9])
    y = np.array([0, 1, 1])
    df = sweep(pd_arr, y, np.full(3, 100.0), lgd=0.5, steps=200)
    last = df.iloc[-1]
    assert last["defaults_approved"] == 2          # all defaults approved
    assert last["good_rejected"] == 0              # nobody rejected


def test_better_ranking_lowers_loss_at_matched_approval():
    rng = np.random.default_rng(0)
    n = 3000
    y = rng.binomial(1, 0.1, n)
    ead = np.full(n, 100.0)
    good = y * 0.5 + rng.random(n) * 0.1           # score correlates with default
    bad = rng.random(n)                            # score is noise

    dg = sweep(good, y, ead, lgd=0.5)
    db = sweep(bad, y, ead, lgd=0.5)

    def loss_at(df, ar):
        return np.interp(ar, df["approval_rate"], df["realized_loss_per_1b"])

    # At 80% approval, the better-ranking model approves fewer defaults -> lower loss.
    assert loss_at(dg, 0.80) < loss_at(db, 0.80)


def test_loss_scales_with_lgd():
    pd_arr = np.array([0.1, 0.2, 0.9])
    y = np.array([0, 1, 1])
    ead = np.full(3, 100.0)
    lo = sweep(pd_arr, y, ead, lgd=0.2).iloc[-1]["realized_loss_per_1b"]
    hi = sweep(pd_arr, y, ead, lgd=0.4).iloc[-1]["realized_loss_per_1b"]
    assert np.isclose(hi, 2 * lo)                  # loss is linear in LGD
