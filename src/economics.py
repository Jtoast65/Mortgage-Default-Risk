"""Loss economics and the precomputed cutoff sweep (PLAN.md section 7).

    LGD  : dollar-weighted realized loss / exposure over disposed defaulted loans
           (zero balance 03/09). Empirical, not assumed. Dollar-weighting avoids the
           small-denominator blow-ups that wreck a naive per-loan mean.
    EL   : EL = PD x LGD x EAD, with EAD approximated by original UPB.
    Sweep: PD cutoff 0..1 in 200 steps. At each: approval rate, expected loss ($),
           realized loss ($), defaults approved, good loans rejected -- for the deployed
           model (calibrated logistic) and the FICO x LTV scorecard, on the held-out test.

The whole thing is precomputed to artifacts/cutoff_curve.json so the frontend slider never
waits on a request. Losses are also expressed per $1B originated for the headline.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from src import models
from src.models import ARTIFACTS, fit_scorecard, make_logistic, score_scorecard, split_experiment

ROOT = Path(__file__).resolve().parent.parent
PERF_GLOB = str(ROOT / "data" / "processed" / "performance" / "*" / "data.parquet")

HEADLINE_CUTOFF = 0.04       # the 4% PD cutoff the plan's headline sentence uses
LGD_ASSUMPTION = 0.30        # fallback if the loss fields are unusable (PLAN.md section 7)


def compute_lgd(con: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Dollar-weighted empirical LGD from disposed defaulted loans."""
    con = con or duckdb.connect()
    row = con.sql(f"""
        WITH d AS (
            SELECT TRY_CAST(actual_loss AS DOUBLE) AS loss,
                   TRY_CAST(zero_balance_removal_upb AS DOUBLE) AS upb
            FROM read_parquet('{PERF_GLOB}')
            WHERE zero_balance_code IN ('03','09')
              AND TRY_CAST(actual_loss AS DOUBLE) IS NOT NULL
              AND TRY_CAST(zero_balance_removal_upb AS DOUBLE) > 0
        )
        SELECT count(*) AS n, sum(loss)/sum(upb) AS lgd FROM d
    """).fetchone()
    n, lgd = int(row[0]), float(row[1])
    if n < 500 or not (0.05 < lgd < 0.95):
        return {"lgd": LGD_ASSUMPTION, "source": "assumption", "n_dispositions": n}
    return {"lgd": round(lgd, 4), "source": "empirical", "n_dispositions": n}


def _deployed_logistic(train: pd.DataFrame, val: pd.DataFrame):
    """Calibrated logistic: fit on train, isotonic on validation (the deployed PD model)."""
    lr = make_logistic(train.columns)
    lr.fit(train, train["default_label"])
    iso = IsotonicRegression(out_of_bounds="clip").fit(
        lr.predict_proba(val)[:, 1], val["default_label"])
    return lambda X: iso.transform(lr.predict_proba(X)[:, 1])


def sweep(pd_arr, y, ead, lgd, steps=200) -> pd.DataFrame:
    """Approve loans with PD < cutoff; tabulate the approve/reject economics per cutoff."""
    pd_arr, y, ead = np.asarray(pd_arr), np.asarray(y), np.asarray(ead)
    total_ead = ead.sum()
    rows = []
    for c in np.linspace(0.0, 1.0, steps):
        appr = pd_arr < c
        rej = ~appr
        exp_loss = float((pd_arr[appr] * lgd * ead[appr]).sum())
        real_loss = float((y[appr] * lgd * ead[appr]).sum())
        rows.append({
            "cutoff": round(float(c), 5),
            "approval_rate": round(float(appr.mean()), 5),
            "expected_loss_per_1b": round(exp_loss / total_ead * 1e9, 2),
            "realized_loss_per_1b": round(real_loss / total_ead * 1e9, 2),
            "defaults_approved": int(y[appr].sum()),
            "good_rejected": int((y[rej] == 0).sum()),
        })
    return pd.DataFrame(rows)


def build_cutoff_curve(exp: str = "A", con: duckdb.DuckDBPyConnection | None = None) -> dict:
    con = con or duckdb.connect()
    lgd_info = compute_lgd(con)
    lgd = lgd_info["lgd"]

    df = models.load_modeling_frame(con)
    train, val, test = split_experiment(df, exp)
    y = test["default_label"].to_numpy()
    ead = pd.to_numeric(test["original_upb"], errors="coerce").fillna(0).to_numpy()

    pd_model = _deployed_logistic(train, val)(test)
    pd_scorecard = score_scorecard(fit_scorecard(train), test)

    model_curve = sweep(pd_model, y, ead, lgd)
    scorecard_curve = sweep(pd_scorecard, y, ead, lgd)

    # Headline: model at the 4% cutoff vs the scorecard at the SAME approval rate.
    mrow = model_curve.iloc[(model_curve["cutoff"] - HEADLINE_CUTOFF).abs().idxmin()]
    appr_rate = float(mrow["approval_rate"])
    sc_loss = float(np.interp(appr_rate, scorecard_curve["approval_rate"],
                              scorecard_curve["realized_loss_per_1b"]))
    model_loss = float(mrow["realized_loss_per_1b"])
    headline = {
        "cutoff": HEADLINE_CUTOFF,
        "approval_rate": round(appr_rate, 4),
        "model_realized_loss_per_1b": round(model_loss, 2),
        "scorecard_realized_loss_per_1b": round(sc_loss, 2),
        "reduction_per_1b": round(sc_loss - model_loss, 2),
        "reduction_pct": round(100 * (sc_loss - model_loss) / sc_loss, 1) if sc_loss else None,
    }

    out = {
        "experiment": exp,
        "model": "logistic_isotonic",
        "lgd": lgd,
        "lgd_source": lgd_info["source"],
        "lgd_n_dispositions": lgd_info["n_dispositions"],
        "ead_total": float(ead.sum()),
        "n_applicants": int(len(y)),
        "base_default_rate": round(float(y.mean()), 5),
        "headline": headline,
        "curve": model_curve.to_dict(orient="records"),
        "scorecard_curve": scorecard_curve.to_dict(orient="records"),
    }
    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / "cutoff_curve.json").write_text(json.dumps(out, indent=2))
    return out


def plot_cutoff_tradeoff(curve: dict) -> None:
    """Approval rate vs realized loss per $1B: deployed model vs scorecard, 4% marker."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from src.evaluate import _ACCENT, _BG, _GRID, _MUTED, _RED, _TEXT

    m = pd.DataFrame(curve["curve"])
    s = pd.DataFrame(curve["scorecard_curve"])
    h = curve["headline"]

    fig, ax = plt.subplots(figsize=(8.5, 5), dpi=140)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.plot(s["approval_rate"] * 100, s["realized_loss_per_1b"] / 1e6,
            color=_MUTED, lw=1.6, label="FICO × LTV scorecard")
    ax.plot(m["approval_rate"] * 100, m["realized_loss_per_1b"] / 1e6,
            color=_ACCENT, lw=1.8, label="calibrated model")
    ax.scatter([h["approval_rate"] * 100], [h["model_realized_loss_per_1b"] / 1e6],
               color=_RED, zorder=5, s=40)
    ax.annotate(f"4% cutoff: approve {h['approval_rate']:.0%},\n"
                f"−\\${h['reduction_per_1b']/1e3:,.0f}K per \\$1B vs scorecard",
                xy=(h["approval_rate"] * 100, h["model_realized_loss_per_1b"] / 1e6),
                xytext=(h["approval_rate"] * 100 - 34, h["model_realized_loss_per_1b"] / 1e6 + 0.6),
                color=_TEXT, fontsize=9,
                arrowprops=dict(color=_MUTED, arrowstyle="->", lw=1))

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(_GRID)
    ax.grid(True, color=_GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(colors=_MUTED, length=0)
    ax.set_xlabel("approval rate (%)", color=_MUTED, fontsize=10)
    ax.set_ylabel("realized loss (\\$M per \\$1B originated)", color=_MUTED, fontsize=10)
    ax.set_title("Approval rate vs credit loss — Experiment A (test)", color=_TEXT,
                 fontsize=13, loc="left", pad=12)
    leg = ax.legend(frameon=False, fontsize=9, loc="upper left")
    for t in leg.get_texts():
        t.set_color(_TEXT)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "cutoff_tradeoff.png", facecolor=_BG, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    r = build_cutoff_curve("A")
    plot_cutoff_tradeoff(r)
    h = r["headline"]
    print(f"LGD = {r['lgd']} ({r['lgd_source']}, n={r['lgd_n_dispositions']:,})")
    print(f"At a {h['cutoff']:.0%} PD cutoff: approve {h['approval_rate']:.1%} of applications,")
    print(f"  model realized loss ${h['model_realized_loss_per_1b']:,.0f} per $1B originated")
    print(f"  scorecard (same approval rate) ${h['scorecard_realized_loss_per_1b']:,.0f} per $1B")
    print(f"  -> reduction ${h['reduction_per_1b']:,.0f} per $1B ({h['reduction_pct']}%)")
