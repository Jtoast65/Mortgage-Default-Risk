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

| Model | AUC | KS | Brier (raw → calibrated) |
|---|---|---|---|
| Scorecard (FICO × LTV) | TBD | TBD | TBD |
| Logistic regression | TBD | TBD | TBD |
| XGBoost | TBD | TBD | TBD |

## Reproduce

```bash
make install
# obtain data — see scripts/download_instructions.md
make ingest label train calibrate economics
make serve      # API on :8000
```

Full build spec and phase plan: [PLAN.md](PLAN.md).
