# PLAN.md — Mortgage Default Risk with Calibrated Probabilities

> **This file is the build spec.** Copy it to the root of the new repo as `PLAN.md` and
> commit it. Claude Code should read it at the start of every session and update the
> checkboxes as phases complete.

**Owner:** Joseph Sandoval · **Started:** 2026-08-13 · **Target:** 2 weekends

---

## 0. What this is and who it is for

A credit-risk model that predicts probability of default on US mortgages, calibrated so the
probabilities are usable for pricing, plus a web interface where someone can drag an
approval cutoff and watch approval rate trade against expected loss in dollars.

**The audience is a risk analyst or a bank early-careers screener.** Every decision in this
spec is made for that reader. Two consequences that override normal instincts:

- **Discipline beats accuracy.** A model that scores 0.72 AUC with a vintage split, a
  reliability curve, and an honest crisis stress test is worth more here than 0.85 AUC with
  a random split. Credit people read a random split as not knowing the field.
- **Calibration is a requirement, not a flourish.** An uncalibrated probability of default
  cannot price a loan. This is the through-line from the NFL project and it is the reason
  this project is credible.

### Hard prohibitions

- ❌ **Never a random train/test split.** Split by origination vintage, always.
- ❌ **Never use post-origination fields as features.** Only what a lender knows at
  underwriting. Performance data exists solely to build the label.
- ❌ **Never commit the raw Freddie Mac data.** The licence covers redistribution.
  `.gitignore` the data directory and say so in the README.
- ❌ **No stock price prediction, no LSTM on returns.** Out of scope, and a negative signal.
- ❌ **Never resample or reweight the test set.** Class weights are a training-time choice.
- ❌ **No fabricated numbers anywhere.** If a metric has not been computed, write `TBD`.
  Never place a plausible-looking placeholder in a README.

---

## 1. Human-only steps — Claude Code cannot do these

Stop and ask Joey when you reach one of these. Do not attempt to work around them.

- [x] **Register at Clarity Data Intelligence and accept the Freddie Mac licence.**
      Done 2026-08-13. Sample dataset 1999–2026 + layout docs downloaded.
- [x] **Create the GitHub repo.** `github.com/Jtoast65/Mortgage-Default-Risk`.
- [x] **Create the Render service** for the API (`mortgage-default-risk-api.onrender.com`)
      and the **Vercel project** (`mortgage-default-risk.vercel.app`).
- [ ] ~~Any `git push`~~ — **Claude may commit and push directly.** Joey has authorized
      Claude Code to run `git push` on his behalf. Still branch off the default branch for
      non-trivial work and summarize what was pushed.
- [ ] **Buying a domain**, if that happens.

---

## 2. Data — scope it before touching it

The full dataset is ~55 million mortgages, 1999 through Q3 2025. **Do not attempt to ingest
all of it.** It will not fit on a laptop and it is not needed.

**Use the official sample dataset**, which Freddie Mac publishes alongside the full files: a
random 50,000-loan sample per origination year, with matching monthly performance records.
That is roughly 1.3M loans across the full history, which is tractable locally and is still
the real data with the real distribution.

**Files per vintage quarter, pipe-delimited, no header row:**

| File | Contents |
|---|---|
| `historical_data_YYYYQN.txt` | Origination records, one row per loan |
| `historical_data_time_YYYYQN.txt` | Monthly performance, many rows per loan |

Layouts change across eras. **Read the official file-layout PDF and write the column
specification from it — do not guess column names or positions.** Store the layout as a
versioned Python dict, not as magic numbers scattered through the code.

### Vintages to pull

- **Modern regime:** 2010–2021 (this produces the headline metrics)
- **Crisis regime:** 1999–2009 (this produces the stress-test story)

---

## 3. The label — define it precisely, once

**Default = the loan reaches 180+ days delinquent, OR terminates through foreclosure, REO,
short sale, or deed-in-lieu, within 24 months of origination.**

Two parts of that matter and both are easy to get wrong:

- **The fixed 24-month observation window is not optional.** Without it, recent vintages
  look artificially safe because they have had less time to fail. Every loan must be
  observed for the same length of time.
- **Drop loans that cannot be observed for the full 24 months** (originated too recently, or
  prepaid early with no delinquency). Record how many were dropped and why. Prepayment is a
  competing risk; note in the README that this is a simplification and that a full treatment
  would model it jointly.

Write the label logic in one function, `build_label()`, with a docstring stating the
definition verbatim. Unit-test it against a handful of hand-checked loans.

---

## 4. Features — origination only

Permitted, all from the origination file:

`credit_score`, `original_ltv`, `original_cltv`, `original_dti`, `original_upb`,
`original_interest_rate`, `loan_term`, `loan_purpose` (purchase / refi / cash-out),
`occupancy_status`, `property_type`, `number_of_units`, `number_of_borrowers`,
`first_time_homebuyer_flag`, `mi_percent`, `channel`, `ppm_flag`, `amortization_type`,
`property_state`, `msa`.

- Sentinel values in this dataset are coded (`9`, `999`, `9999`, spaces). Map them to null
  explicitly and **add a missing-indicator column** rather than silently imputing.
- Treat `credit_score` outside 300–850 as missing.
- One-hot or target-encode categoricals; if target encoding, fit the encoder on train only.

**Write an assertion that fails the build if any column sourced from the performance file
appears in the feature matrix.** This is the leakage guard and it should be impossible to
bypass by accident.

---

## 5. Experiments — run exactly two

### Experiment A — modern regime (produces the headline numbers)

| Split | Vintages |
|---|---|
| Train | 2010–2017 |
| Validation | 2018–2019 (calibration is fit here) |
| Test | 2020–2021 |

### Experiment B — regime break (produces the interview story)

| Split | Vintages |
|---|---|
| Train | 1999–2005 |
| Validation | 2006 |
| Test | 2007–2009 |

**Experiment B is expected to degrade badly, and that is the point.** Do not tune it until
it looks good. Report the drop, quantify it, and frame it in the README as model risk under
regime change — which is what a risk analyst is actually paid to think about.

---

## 6. Models — baseline first, always

1. **Scorecard baseline.** Bin FICO and LTV, compute observed default rate per cell. Crude,
   interpretable, and it is what the industry actually used for decades.
2. **Logistic regression** on the full feature set, with standardised numerics.
3. **XGBoost.** Handle imbalance with `scale_pos_weight`, not by oversampling. Early-stop on
   the validation set.

**Report all three side by side.** If gradient boosting does not beat the scorecard by a
meaningful margin, say so plainly — that is a finding, and pretending otherwise is the kind
of thing that unravels in an interview.

### Calibration

Fit **isotonic regression** on the **validation** split only. Never on train (overfits),
never on test (leakage). Report Brier before and after, and plot the reliability curve with
both curves and the 45-degree line on the same axes.

---

## 7. Economics — the part that puts this on the business resume

- **LGD:** compute empirically from disposed defaulted loans in the performance file, using
  the actual loss fields. If the fields are unusable, fall back to a stated assumption
  (25–35% is the conventional range) and **label it as an assumption in the README and on
  the dashboard.**
- **Expected loss:** `EL = PD × LGD × EAD`, with EAD approximated by original UPB.
- **The cutoff curve:** sweep the PD cutoff from 0 to 1 in 200 steps. At each point compute
  approval rate, total expected loss in dollars, defaults approved, and good loans rejected.
  **Precompute this whole curve and save it as a static JSON artifact** so the frontend
  slider never waits on a request.

The single sentence this project has to be able to produce: *"At a 4% PD cutoff the model
approves 91% of applications and reduces expected loss by $X million per $1B originated
versus the FICO/LTV scorecard."* Everything above exists to make that sentence true.

---

## 8. Repo structure

```
mortgage-default-risk/
├── PLAN.md
├── README.md
├── .gitignore              # data/ must be in here
├── data/                   # gitignored. Raw + processed
├── scripts/
│   └── download_instructions.md
├── src/
│   ├── layouts.py          # column specs from the official layout PDF
│   ├── ingest.py           # parse pipe-delimited files to parquet
│   ├── labels.py           # build_label(), 24-month window
│   ├── features.py         # origination-only, with the leakage assertion
│   ├── models.py           # scorecard, logistic, xgboost
│   ├── calibrate.py        # isotonic, reliability curve
│   ├── economics.py        # LGD, expected loss, cutoff sweep
│   └── evaluate.py         # AUC, KS, Brier, all plots
├── artifacts/              # committed: metrics.json, cutoff_curve.json, model card
├── tests/
├── api/                    # FastAPI
└── web/                    # Next.js frontend
```

**Artifacts are committed; data is not.** The frontend reads the committed JSON, so the site
renders even when the API is asleep.

---

## 9. API

FastAPI, mirroring the NFL service's conventions so the two projects look like one
engineer's work.

| Endpoint | Returns |
|---|---|
| `GET /health` | Liveness. Keep-warm cron pings this. |
| `GET /metrics` | AUC, KS, Brier before/after calibration, per experiment |
| `GET /cutoff-curve` | The precomputed sweep |
| `POST /score` | A loan's features in, calibrated PD out |
| `GET /vintage-performance` | Metrics by origination year |

Pydantic models on every request and response. OpenAPI docs enabled.

---

## 10. Frontend — Next.js on Vercel

**The design target is a risk desk terminal, not a startup landing page.** Restrained,
dense, precise. Gradients, glassmorphism, rounded card stacks, emoji, and animated counters
all read as junior to this audience.

### Design system, non-negotiable

- **Type:** Inter or IBM Plex Sans for UI; IBM Plex Mono or JetBrains Mono for **every
  number**, with `font-variant-numeric: tabular-nums` so digits stop jittering on update.
- **Scale:** 12 / 14 / 16 / 20 / 32px only. Body 14. Metrics 32.
- **Palette:** background `#0B0E14`; surfaces `#151A23` and `#1E252F`; text `#E6EAF0`;
  secondary text `#8B97A8`; one accent `#4F8EF7`; red `#E5484D` reserved strictly for loss
  and default.
- **Spacing:** 8px grid. 1px hairline borders `#252C38`. No drop shadows.
- **Charts:** Recharts, default styling stripped. 1px axes, faint horizontal gridlines only,
  direct labels instead of legends where possible, units on axis labels, a one-line caption
  under every chart saying what to take from it. **No pie charts.**

### Panels, in build order

1. **⭐ Approval-cutoff panel — build this first and make it feel instant.** One slider for
   the PD cutoff. Dragging updates approval rate, expected loss in dollars, defaults
   approved, good loans rejected, and a marker on the tradeoff curve. Reads from the
   precomputed JSON, so it never waits on a network call. **This is the interaction that
   makes a risk person stop scrolling.**
2. **Header metrics strip.** AUC, KS, Brier, expected loss at current cutoff. Mono, 32px.
3. **Reliability curve.** Calibrated and uncalibrated against the 45-degree line. Caption
   states the Brier improvement.
4. **Vintage panel.** Performance by origination year, with 2007–2009 visible and the
   degradation legible.
5. **Model card.** Data source and licence, label definition, split strategy, feature list,
   metric definitions, stated assumptions. Boring, and its presence signals governance
   literacy to anyone from a bank.

### Polish checklist

- [ ] Skeleton loaders, not spinners
- [ ] First paint under 1s; page renders from static JSON, hydrates live values after
- [ ] Keep-warm cron pinging `/health` so Render never cold-starts on a visitor
- [ ] Responsive to 390px without horizontal scroll
- [ ] `og:image` preview card so the link renders as a screenshot when pasted
- [ ] Favicon
- [ ] Error and empty states written as sentences

---

## 11. Phases and acceptance criteria

Work through these in order. **Do not start a phase before the previous one's criteria pass.**

- [x] **Phase 0 — Scaffold.** Repo structure, `.gitignore` with `data/`, `PLAN.md`,
      dependencies pinned. *Accepted:* `pytest` green. Storage: DuckDB + parquet (not
      Postgres) — the API serves committed JSON, so no runtime DB is needed.

- [x] **Phase 1 — Ingest.** Layout spec written from the official July-2026 XLSX (31 orig /
      35 perf cols), DuckDB parser to hive-partitioned parquet. *Accepted:* all 28 vintages
      parse (1.4M loans, 74.9M perf rows), row counts match the raw files exactly, five rows
      eyeballed against raw text. 8.0 GB raw → 731 MB parquet.

- [x] **Phase 2 — Label and features.** 24-month window, leakage assertion in place.
      *Accepted:* leakage guard proven to fail on a deliberately bad matrix (3 tests);
      build_label() unit-tested on hand-checked loans. Vintage default rates plotted
      (artifacts/vintage_default_rate.png) — **2007 spikes to 5.3%**, 2006/08 elevated,
      2019 flagged as COVID-forbearance artifact. 957k loans kept, 405k censored/dropped,
      overall default rate 1.32%.

- [x] **Phase 3 — Baseline.** Scorecard and logistic regression, Experiment A.
      *Accepted (test 2020–21):* scorecard AUC 0.718 / KS 0.330; logistic AUC 0.791 /
      KS 0.447. Splits strictly by vintage; encoder/scaler fit on train only. Metrics in
      artifacts/metrics.json, models in models/.

- [x] **Phase 4 — XGBoost and calibration.** Isotonic on validation.
      *Accepted:* reliability curve rendered (artifacts/reliability_curve_A.png); Brier
      0.0504 → 0.0087 after isotonic (−83%). XGBoost (AUC 0.751) beats the scorecard but
      not logistic (0.791) — reported honestly as a regime-shift finding, not tuned away.
      Native categorical (incl. msa), scale_pos_weight, auc early-stopping on validation.

- [x] **Phase 5 — Economics.** LGD, expected loss, cutoff sweep to JSON.
      *Accepted:* empirical LGD 0.456 (dollar-weighted, 15,130 dispositions). Headline —
      at a 4% PD cutoff the calibrated logistic approves 94.4% and cuts realized losses
      ~$480K per $1B (13.7%) vs the scorecard at matched approval. 200-point sweep +
      scorecard curve in artifacts/cutoff_curve.json; tradeoff plot rendered.

- [x] **Phase 6 — Experiment B.** The regime break.
      *Accepted:* quantified in artifacts/experiment_comparison.{json,png}. Counterintuitive
      finding, reported honestly: discrimination does NOT degrade (AUC 0.79→0.85 — crisis
      defaults are more predictable at origination); the break is in **calibration** — the
      crisis model under-predicts defaults 41% (0.59× actual) because it was calibrated on
      pre-crisis 2006. Modern model over-predicts 50% (COVID-inflated 2019 validation).

- [x] **Phase 7 — API.** All five endpoints live on Render
      (`https://mortgage-default-risk-api.onrender.com`, `/docs` loads publicly). Pydantic
      on every request/response; `/score` discriminates (risky 16.7% vs safe 0%). Serves
      committed artifacts + the deployed calibrated-logistic (no DB, cold-start safe).

- [x] **Phase 8 — Frontend.** Next.js risk-desk dashboard, **live at
      `https://mortgage-default-risk.vercel.app`**. Design system honoured (#0B0E14, IBM Plex
      Mono tabular nums, one accent, red for loss only, hairline borders, no gradients).
      Panels: metrics strip, ⭐ approval-cutoff (reads static JSON, instant), reliability
      curve, vintage panel, live /score form, model card. Static 187kB first load; verified
      at 1440px and 390px (no horizontal scroll). og:image + favicon + keep-warm Action.

- [ ] **Phase 9 — Write-up.** README, model card, screen recording.
      *Accept when:* a stranger can read the README and state the headline number.

---

## 12. README requirements

Write it for a recruiter who will spend 90 seconds. Structure:

1. **One sentence on what it does, and the headline number.** Above the fold.
2. **A screenshot or GIF of the cutoff slider.** Most viewers will never click the live
   link; the GIF plays inline on GitHub.
3. Live links: dashboard, API docs.
4. **Why the vintage split** — two sentences on why a random split would be wrong.
5. Results table: scorecard vs. logistic vs. XGBoost, AUC / KS / Brier.
6. The reliability curve image.
7. **The crisis stress test**, framed as model risk under regime change.
8. Stated assumptions and limitations, including the LGD assumption and the competing-risk
   simplification.
9. Data licensing note explaining why the data is not in the repo.
10. How to reproduce.

---

## 13. When this lands

- [ ] Update `01_master/fact_sheet.md` with the repo URL, the live URL, and every metric,
      the same day it ships. Packets can then use it immediately.
- [ ] Add a portfolio site card linking to the live dashboard.
- [ ] Mark Project 4 complete in `01_master/PROJECT_PLAN.md`.

**Résumé keywords this unlocks:** credit risk, probability of default, model calibration,
KS statistic, expected loss, scorecard, vintage analysis, imbalanced classification,
gradient boosting, model risk, financial services data, React, Next.js.
