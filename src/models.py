"""Three models, reported side by side (PLAN.md section 6).

    1. Scorecard baseline -- bin FICO and LTV, observed default rate per cell.
    2. Logistic regression -- full feature set, standardised numerics.
    3. XGBoost -- imbalance via scale_pos_weight (not oversampling), early-stop on validation.

If gradient boosting does not beat the scorecard by a meaningful margin, that is reported
plainly as a finding.
"""
