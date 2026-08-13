# Downloading the Freddie Mac data (human-only)

The raw data is **not** in this repo. The Freddie Mac licence prohibits redistribution, so
`data/` is gitignored. You download it yourself; the pipeline reads it locally.

## Steps

1. Register at **Clarity Data Intelligence** and accept the Single-Family Loan-Level Dataset
   terms. Start at `https://capitalmarkets.freddiemac.com/clarity`, then follow
   **Access Historical Data** → the SFLLD Data Download page.
2. Download the **Sample Dataset** — a random 50,000-loan sample per origination year with
   matching monthly performance (~1.4M loans, ~75M performance rows across 1999–2026). Do
   **not** download the full ~56M-loan Standard/Non-Standard files; they will not fit on a
   laptop and are not needed.
3. From the SFLLD page sidebar, also grab the layout docs (the **"Effective July 2026"**
   set, which matches the current sample release):
   - **File Layout – Effective July 2026** (`.xlsx`) — authoritative column spec; `src/layouts.py`
     is transcribed from it.
   - **General User Guide – Effective July 2026** (`.pdf`) — coded values (delinquency status,
     zero-balance codes) used by the label logic.
   - **File Headers – Effective July 2026** (`.zip`) — header rows, used to cross-check order.

## What the files look like

The sample arrives as one zip per year, `sample_YYYY.zip`, each containing two
pipe-delimited files with **no header row**:

| File | Contents | Layout |
|---|---|---|
| `sample_orig_YYYY.txt` | Origination records, one row per loan | 31 columns |
| `sample_perf_YYYY.txt` | Monthly performance, many rows per loan | 35 columns |

## Unpack into `data/raw/` (all gitignored)

```bash
for z in ~/Downloads/sample_*.zip; do unzip -o "$z" -d data/raw/; done
```

Then build the parquet:

```bash
python -m src.ingest          # all vintages -> data/processed/{origination,performance}/vintage=YYYY/
```

Resulting local layout:

```
data/
├── raw/         # sample_orig_YYYY.txt / sample_perf_YYYY.txt  (~8 GB)
└── processed/   # hive-partitioned parquet written by src/ingest.py  (~730 MB)
```

## Vintages

The sample covers **1999–2026**. This project uses:
- **Modern regime:** 2010–2021 (headline metrics, Experiment A)
- **Crisis regime:** 1999–2009 (stress-test story, Experiment B)
