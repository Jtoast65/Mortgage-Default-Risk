"""Default label construction with a fixed 24-month observation window.

Per PLAN.md section 3:

    Default = the loan reaches 180+ days delinquent, OR terminates through foreclosure,
    REO, short sale, or deed-in-lieu, within 24 months of origination.

The fixed 24-month window is mandatory so every loan is observed for the same length of
time. Loans that cannot be observed for the full window are dropped, and the drop count is
recorded. Prepayment is a competing risk noted as a simplification in the README.
"""


def build_label():
    """Return the 0/1 default label per loan over the 24-month window.

    Definition (verbatim, per PLAN.md section 3):
        Default = the loan reaches 180+ days delinquent, OR terminates through foreclosure,
        REO, short sale, or deed-in-lieu, within 24 months of origination.

    TODO(Phase 2): implement, then unit-test against hand-checked loans.
    """
    raise NotImplementedError("build_label() — Phase 2")
