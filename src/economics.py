"""Loss economics and the precomputed cutoff sweep (PLAN.md section 7).

    LGD: computed empirically from disposed defaulted loans; if loss fields are unusable,
         fall back to a stated assumption (25-35%) LABELLED as an assumption.
    Expected loss: EL = PD x LGD x EAD, with EAD approximated by original UPB.
    Cutoff curve: sweep the PD cutoff 0..1 in 200 steps; at each point compute approval
         rate, total expected loss ($), defaults approved, good loans rejected.

The full curve is precomputed and saved as static JSON (artifacts/cutoff_curve.json) so the
frontend slider never waits on a request.
"""
