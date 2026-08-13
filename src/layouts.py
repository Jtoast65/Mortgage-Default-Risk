"""Column specifications for the Freddie Mac Single-Family Loan-Level Dataset (SFLLD).

Transcribed verbatim from the official layout, NOT guessed (PLAN.md section 2):
    - file_layout_july_2026.xlsx  (Effective July 2026, Release 47)
    - general_user_guide_july_2026.pdf  (coded values below)
    - file_headers_july_2026.zip  (column order cross-checked, 31 orig / 35 perf)

Both files are pipe-delimited with NO header row. Field position in the layout == column
order in the file. The sample dataset ships two files per origination year:
    sample_orig_YYYY.txt   one row per loan        (ORIGINATION_LAYOUT, 31 cols)
    sample_perf_YYYY.txt   one row per loan-month  (PERFORMANCE_LAYOUT, 35 cols)

Column order verified against the real 2010 sample on 2026-08-13.
"""

LAYOUT_VERSION = "2026-07"  # Effective July 2026 / Release 47

# --- Origination file: ordered snake_case names (field position 1..31) ---------------
# Right of each name is the official attribute from the layout PDF.
ORIGINATION_LAYOUT: list[str] = [
    "credit_score",               # 1  Classic FICO
    "first_payment_date",         # 2  First Payment Date (YYYYMM)
    "first_time_homebuyer_flag",  # 3  First Time Homebuyer Indicator
    "maturity_date",              # 4  Maturity Date (YYYYMM)
    "msa",                        # 5  Metropolitan Statistical Area / Division
    "mi_percent",                 # 6  Mortgage Insurance Percentage (MI %)
    "number_of_units",            # 7  Number of Units
    "occupancy_status",           # 8  Occupancy Status
    "original_cltv",              # 9  Original Combined Loan-to-Value (CLTV)
    "original_dti",               # 10 Original Debt-to-Income (DTI) Ratio
    "original_upb",               # 11 Original UPB
    "original_ltv",               # 12 Original Loan-to-Value (LTV)
    "original_interest_rate",     # 13 Original Interest Rate
    "channel",                    # 14 Channel (Retail / Broker / Correspondent)
    "ppm_flag",                   # 15 Prepayment Penalty Indicator
    "amortization_type",          # 16 Amortization Type (FRM / ARM)
    "property_state",             # 17 Property State
    "property_type",              # 18 Property Type
    "postal_code",                # 19 Postal Code (3-digit)
    "loan_id",                    # 20 Loan Identifier  (PYYQnXXXXXXX)
    "loan_purpose",               # 21 Loan Purpose (P / C / N / R)
    "loan_term",                  # 22 Original Loan Term
    "number_of_borrowers",        # 23 Number of Borrowers
    "seller_name",                # 24 Seller Name
    "super_conforming_flag",      # 25 Super Conforming Flag
    "pre_harp_loan_seq",          # 26 Pre-HARP Loan Sequence Number
    "special_eligibility_program",  # 27 Special Eligibility Program
    "harp_indicator",             # 28 HARP Indicator
    "property_valuation_method",  # 29 Property Valuation Method
    "interest_only_flag",         # 30 Interest Only (I/O) Indicator
    "vantage_score",              # 31 VantageScore 4.0
]

# --- Monthly performance file: ordered snake_case names (field position 1..35) --------
PERFORMANCE_LAYOUT: list[str] = [
    "loan_id",                        # 1  Loan Identifier
    "period",                         # 2  Monthly reporting period (YYYYMM)
    "current_actual_upb",             # 3  Current Actual UPB
    "current_delinquency_status",     # 4  Current Loan Delinquency Status (see codes below)
    "loan_age",                       # 5  Loan Age (scheduled payments since origination)
    "remaining_months_to_maturity",   # 6  Remaining Months to Legal Maturity
    "defect_settlement_date",         # 7  Underwriting/Major Servicing Defect Settlement Date
    "modification_flag",              # 8  Modification Flag (Y / P / null)
    "zero_balance_code",              # 9  Zero Balance Code (see codes below)
    "zero_balance_effective_date",    # 10 Zero Balance Effective Date (YYYYMM)
    "current_interest_rate",          # 11 Current Interest Rate
    "current_non_interest_bearing_upb",  # 12 Current Non-Interest Bearing UPB
    "ddlpi",                          # 13 Due Date of Last Paid Installment
    "mi_recoveries",                  # 14 MI Recoveries
    "net_sales_proceeds",             # 15 Net Sales Proceeds
    "non_mi_recoveries",              # 16 Non MI Recoveries
    "total_expenses",                 # 17 Total Expenses
    "legal_costs",                    # 18 Legal Costs
    "maintenance_costs",              # 19 Maintenance and Preservation Costs
    "taxes_and_insurance",            # 20 Taxes and Insurance
    "miscellaneous_expenses",         # 21 Miscellaneous Expenses
    "actual_loss",                    # 22 Actual Loss
    "cumulative_modification_costs",  # 23 Cumulative Modification Costs
    "interest_rate_step_flag",        # 24 Interest Rate Step Indicator
    "payment_deferral_flag",          # 25 Payment Deferral Flag
    "estimated_ltv",                  # 26 Estimated Loan-to-Value (ELTV)
    "zero_balance_removal_upb",       # 27 Zero Balance Removal UPB
    "delinquent_accrued_interest",    # 28 Delinquent Accrued Interest
    "delinquency_due_to_disaster",    # 29 Delinquency Due to Disaster
    "borrower_assistance_plan",       # 30 Borrower Assistance Plan
    "current_period_modification_costs",  # 31 Current Period Modification Costs
    "current_interest_bearing_upb",   # 32 Current Interest Bearing UPB
    "mi_cancellation_flag",           # 33 Mortgage Insurance Cancellation Indicator
    "servicer_name",                  # 34 Servicer Name
    "bankruptcy_cramdown_costs",      # 35 Bankruptcy Cramdown Costs
]

# --- Coded values needed for the label and economics (from the General User Guide) ----
#
# Current Loan Delinquency Status is the number of 30-day cycles delinquent, as a string:
#   "00" = current / <30d, "01" = 30-59d, "02" = 60-89d, ... "06" = 180-209d, capped "99".
#   "RA" = REO Acquisition.  "XX" = Not Available.  Blank = missing.
# 180+ days delinquent therefore means the numeric status is >= 6.
DELINQUENCY_DEFAULT_THRESHOLD = 6          # 6 cycles * 30 days = 180+ DPD
REO_ACQUISITION_STATUS = "RA"
DELINQUENCY_NOT_AVAILABLE = "XX"

# Zero Balance Code: reason the loan balance went to zero.
#   01 = Prepaid or Matured (Voluntary Payoff)   <- competing-risk prepayment, dropped
#   02 = Third Party Sale
#   03 = Short Sale or Charge Off                 <- default termination
#   09 = REO Disposition                          <- default termination
#   15 = Whole Loan sales
#   16 = Reperforming loan securitizations
#   96 = Confirmed Underwriting/Servicing Defect prior to credit event (repurchase)
DEFAULT_ZERO_BALANCE_CODES = {"03", "09"}  # short sale/charge-off, REO disposition
PREPAY_ZERO_BALANCE_CODES = {"01"}         # voluntary payoff (competing risk)

# Fixed observation window for the label (PLAN.md section 3).
OBSERVATION_WINDOW_MONTHS = 24


def _assert_layout_integrity() -> None:
    """Guard against an accidental edit that drops or duplicates a column."""
    assert len(ORIGINATION_LAYOUT) == 31, f"orig layout has {len(ORIGINATION_LAYOUT)} cols, expected 31"
    assert len(PERFORMANCE_LAYOUT) == 35, f"perf layout has {len(PERFORMANCE_LAYOUT)} cols, expected 35"
    assert len(set(ORIGINATION_LAYOUT)) == 31, "duplicate column name in ORIGINATION_LAYOUT"
    assert len(set(PERFORMANCE_LAYOUT)) == 35, "duplicate column name in PERFORMANCE_LAYOUT"


_assert_layout_integrity()
