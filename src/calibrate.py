"""Probability calibration via isotonic regression (PLAN.md section 6).

Fit isotonic regression on the VALIDATION split only -- never train (overfits), never test
(leakage). Report Brier before and after, and plot the reliability curve with both curves
and the 45-degree line on one set of axes.
"""
