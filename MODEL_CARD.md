# Model Card — Mortgage Default Risk (calibrated PD)

## Model details
- **Task:** binary classification — probability that a mortgage defaults within 24 months of
  origination, calibrated so the probability is usable for pricing.
- **Deployed model:** logistic regression on origination features, with isotonic calibration
  fit on the validation vintage. Scorecard (FICO×LTV) and XGBoost are trained and reported
  alongside as baselines.
- **Version:** Experiment A (modern regime). Owner: Joseph Sandoval.

## Intended use
- **Intended:** demonstrate a disciplined credit-risk workflow — vintage splits, calibration,
  loss economics, and honest stress testing. Educational / portfolio.
- **Out of scope:** real underwriting or pricing decisions. Trained on a public sample, with a
  single constant LGD and a censoring treatment of prepayment; not production-grade.

## Data
- Freddie Mac Single-Family Loan-Level **official sample**, 1999–2026 (~1.4M loans, ~75M
  monthly performance rows). Licence prohibits redistribution — the raw data is not committed.

## Label
- Default = **180+ days delinquent, or foreclosure / REO / short-sale**, within a **fixed
  24-month window** from origination. Loans that leave the panel early without defaulting
  (mostly voluntary prepayment) are **censored and dropped** — a competing-risk simplification.

## Features
- **Origination-only** (what a lender knows at underwriting): FICO, LTV/CLTV, DTI, UPB, rate,
  term, purpose, occupancy, property type, units, borrowers, first-time-buyer, MI %, channel,
  PPM, amortization, state, MSA. Coded sentinels → null with explicit missing indicators.
- A build-time assertion fails if any performance-file column enters the feature matrix.

## Training & evaluation
- **Split by origination vintage, never random.** Experiment A: train 2010–17, calibrate
  2018–19, test 2020–21. Encoders/scalers and calibration fit on train/validation only.

| Model | AUC | KS | Brier |
|---|---|---|---|
| Scorecard (FICO×LTV) | 0.718 | 0.330 | 0.00857 |
| Logistic (deployed) | 0.791 | 0.447 | 0.00859 |
| XGBoost + isotonic | 0.748 | 0.375 | 0.00869 |

- **Calibration:** isotonic on validation cuts XGBoost Brier 0.050 → 0.0087 (−83%).
- **Stress test (Experiment B, 2007–09):** discrimination holds (AUC 0.85) but calibration
  breaks — the crisis model under-predicts defaults 41%. Model risk under regime change.

## Economics
- **LGD = 0.456**, empirical (dollar-weighted realized loss over 15,130 disposed defaulted
  loans). EL = PD × LGD × EAD (EAD ≈ original UPB). At a 4% PD cutoff the model cuts realized
  losses ~$480K per $1B vs the scorecard at the same 94% approval rate.

## Limitations & ethical considerations
- Prepayment censoring, constant LGD, and 2019 COVID-forbearance inflation (reported as
  delinquency) are documented in the README. Protected-class attributes are not used, but
  geography (state/MSA) and FICO can proxy for them; a production deployment would require
  fair-lending (disparate-impact) testing not performed here.
