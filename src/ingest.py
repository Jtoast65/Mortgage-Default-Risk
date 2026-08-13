"""Parse the raw pipe-delimited Freddie Mac files into parquet.

Per PLAN.md Phase 1: read origination and performance files using the column specs in
`layouts.py`, and write parquet to data/processed/. Acceptance: one vintage quarter parses,
row count matches the raw file, and five sample rows are eyeballed against the raw text.
"""
