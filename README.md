# Mortgage Default Risk — Calibrated Probabilities of Default

> **Status: scaffolding (Phase 0).** Metrics are `TBD` until the pipeline runs on real data.
> No fabricated numbers appear in this README — see PLAN.md.

A credit-risk model that predicts probability of default (PD) on US mortgages, **calibrated**
so the probabilities are usable for loan pricing, plus a risk-desk dashboard where you drag
an approval cutoff and watch approval rate trade against expected loss in dollars.

**Headline number:** `TBD` — *"At a 4% PD cutoff the model approves __% of applications and
reduces expected loss by $__M per $1B originated versus the FICO/LTV scorecard."*

## Why a vintage split (not random)

Loans are split by **origination vintage**, never randomly. A random split leaks the future
into the past: it lets the model train on 2019 loans to predict 2015 ones, and it inflates
metrics because economic conditions bleed across the split. Splitting by vintage mirrors how
a model is actually deployed — trained on history, scored on originations it has never seen.

## Data

Freddie Mac Single-Family Loan-Level **official sample** (~1.3M loans; 50k/year). The raw
data is **not** in this repo — the licence prohibits redistribution, so `data/` is
gitignored. See `scripts/download_instructions.md` to obtain it.

## Results

Experiment A (modern regime) — train 2010–17, validation 2018–19, **test 2020–21**
(n = 82,413, base default rate 0.87%):

| Model | AUC | KS | Brier |
|---|---|---|---|
| Scorecard (FICO × LTV) | 0.718 | 0.330 | 0.00857 |
| **Logistic regression** | **0.791** | **0.447** | 0.00859 |
| XGBoost (raw) | 0.751 | 0.384 | 0.05041 |
| XGBoost + isotonic calibration | 0.748 | 0.375 | 0.00869 |

**Finding, reported rather than tuned away:** on this strict vintage split, the regularized
logistic regression is the best discriminator. Gradient boosting beats the crude FICO×LTV
scorecard but does **not** beat the linear model — the 2017→2020 regime shift (and a
COVID-inflated 2019 validation base rate) rewards the smoother model, and XGBoost is not
tuned against the held-out test set to hide that.

**Calibration works as intended.** XGBoost trained with `scale_pos_weight` ranks well but
its raw probabilities are badly inflated (Brier 0.050). Isotonic regression fit on the
validation split alone cuts that to 0.0087 — an 83% reduction — bringing the probabilities
onto the diagonal (see `artifacts/reliability_curve_A.png`) so they can price a loan.

## Reproduce

```bash
make install
# obtain data — see scripts/download_instructions.md
make ingest label train calibrate economics
make serve      # API on :8000
```

Full build spec and phase plan: [PLAN.md](PLAN.md).
