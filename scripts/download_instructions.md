# Downloading the Freddie Mac data (human-only)

The raw data is **not** in this repo. The Freddie Mac licence prohibits redistribution, so
`data/` is gitignored. You download it yourself; the pipeline reads it locally.

## Steps

1. Register at **Clarity Data Intelligence** and accept the Single-Family Loan-Level licence:
   `https://claritydownload.fmapps.freddiemac.com/CRT/#/sflld`
2. Download the **official sample dataset** — a random 50,000-loan sample per origination
   year with matching monthly performance records (~1.3M loans across history). Do **not**
   download the full ~55M-loan files; they will not fit on a laptop and are not needed.
3. Also download the **file-layout PDF**. `src/layouts.py` is transcribed from it — column
   positions are never guessed.
4. Unzip into `data/raw/` so you have, per vintage quarter:
   - `historical_data_YYYYQN.txt` — origination records
   - `historical_data_time_YYYYQN.txt` — monthly performance

## Vintages to pull

- **Modern regime:** 2010–2021 (headline metrics, Experiment A)
- **Crisis regime:** 1999–2009 (stress-test story, Experiment B)

## Expected local layout (all gitignored)

```
data/
├── raw/         # unzipped .txt files, as downloaded
└── processed/   # parquet written by src/ingest.py
```
