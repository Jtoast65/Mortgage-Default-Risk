"""Column specifications for the Freddie Mac Single-Family Loan-Level dataset.

Layouts change across eras. Per PLAN.md section 2, these specs are transcribed from the
official file-layout PDF -- NOT guessed -- and stored as versioned dicts so column
positions never leak into the code as magic numbers.

Two file types per vintage quarter (pipe-delimited, no header row):
    historical_data_YYYYQN.txt        origination records, one row per loan
    historical_data_time_YYYYQN.txt   monthly performance, many rows per loan

TODO(Phase 1): fill ORIGINATION_LAYOUT and PERFORMANCE_LAYOUT from the layout PDF.
"""

# Ordered column names as they appear in the pipe-delimited origination file.
# Populate from the official layout PDF in Phase 1.
ORIGINATION_LAYOUT: list[str] = []

# Ordered column names for the monthly performance file.
PERFORMANCE_LAYOUT: list[str] = []
