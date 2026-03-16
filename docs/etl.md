# 🗂 ETL Pipeline Documentation
This document explains the **ETL pipeline**, **data-processing workflow**, **duplicate handling**, **configuration**, and **common troubleshooting steps** used for loading the Austin Animal Center dataset into the PetMatch database.

---
# 1.0 Overview
The ETL pipeline loads and cleans real shelter outcome records and dog breed metadata into the SQLite database used by the API.

It processes:
- `data/raw/Austin_Animal_Center_Outcomes.csv`
- `data/raw/dogbreeds.json`

The pipeline is **idempotent**, meaning it can safely be re-run without corrupting or duplicating database records.

---
# 2.0 ETL Flow (End to End)
**Raw → Processed → Database**

## 2.1 Pipeline Overview
**Raw inputs**
- `data/raw/Austin_Animal_Center_Outcomes.csv` — pet outcomes dataset  
- `data/raw/dogbreeds.json` — dog breed groups dataset 

**Processing** (via `scripts/run_etl.py`)
- `app/etl/outcomes.py` → cleans & normalizes outcomes → writes `data/processed/pets_clean.csv`
- `app/etl/breeds.py` → flattens dog breed groups → writes `data/processed/breeds_clean.csv`
- `app/etl/seed.py` → idempotent DB load of breeds + pets

## 2.2 Pipeline Steps
1. **Outcomes cleaning (`etl/outcomes.py`)**
   - Drops rows missing key fields  
   - Normalizes species, sex, outcome type  
   - Normalizes age (converts units → years)  
   - Enforces consistent external_id format  
   - Writes to `data/processed/pets_clean.csv`

2. **Breed group flattening (`etl/breeds.py`)**
   - Loads local JSON breed dictionary  
   - Ensures each breed maps to a consistent group  
   - Writes to `data/processed/breeds_clean.csv`

3. **Database seeding (`etl/seed.py`)**
   - Loads breeds first  
   - Loads pets after ensuring referential correctness  
   - Tracks `external_id` to avoid duplicates  
   - Inserts cleaned + validated rows

## 2.3 Duplicate Handling (`external_id`)
The Austin dataset sometimes has repeated `external_id` entries.  
PetMatch uses **two layers** of protection:

1. ETL-Level Dedupe  
Performed in `outcomes.run(...)`
- Drops duplicate rows by `external_id`
- Keeps the **first occurrence**
- Ensures `pets_clean.csv` contains no duplicates

2. Loader-Level Guard  
Inside `seed._load_pets(...)`:
- Maintains a Python `set()` of seen IDs during a single load session  
- Skips duplicates already in the DB  
- Skips duplicates appearing within the same ETL run  

Result  
✔ No `UNIQUE constraint failed` errors  
✔ Pipeline is re-runnable  
✔ DB remains stable & predictable  

## 2.4  Running the Pipeline
```bash
# Windows PowerShell
$env:DATABASE_URL="sqlite:///./petmatch.sqlite"
python scripts/run_etl.py

# macOS / Linux / WSL
export DATABASE_URL="sqlite:///./petmatch.sqlite"
python scripts/run_etl.py
```
After this, the DB will be populated from the processed CSVs.

## 2.5 Check results
After completion:
- Breeds table filled
- Pets table filled
- Output CSVs generated under data/processed/
---
# 3.0 Demo Mode (Fast 3-Pet Dataset)
For quick presentations & smoke tests:
```bash
python -m scripts.seed
```

Inserts predictable sample pets:
- DEMO-D1 (Dog)
- DEMO-C1 (Cat)
- DEMO-O1 (Other)
---
# 4.0 Resetting the Database
1. Safe DB Reset
```bash
python -m scripts.reset_db --yes
```

2. Reset + seed demo (Fast demo seed - 3 records)
```bash
python -m scripts.reset_db --yes --seed --seed-mode demo
```

3. Reset + full ETL (Full Dataset)
```bash
python -m scripts.reset_db --yes --seed --seed-mode etl
```
---
# 5.0 Environment Variables
You may override inputs/outputs:
```bash
DATABASE_URL=sqlite:///./petmatch.sqlite

OUTCOMES_CSV=data/raw/Austin_Animal_Center_Outcomes.csv
DOGBREEDS_JSON=data/raw/dogbreeds.json

PETS_CLEAN_CSV=data/processed/pets_clean.csv
BREEDS_CLEAN_CSV=data/processed/breeds_clean.csv
```
---
# 6.0 Troubleshooting
## 6.1 “UNIQUE constraint failed: pets.external_id”
Cause: repeated external_id.

Fix:
- Ensure dedupe enabled
- Reset DB + re-run ETL:

```bash
python -m scripts.reset_db --yes
python scripts/run_etl.py
```

## 6.2 “ETL finished but tables are empty”
- Ensure environment variable DATABASE_URL is identical across reset + ETL
- Verify raw files exist
- Look for messages:
    - Wrote pets_clean.csv
    - Pets loaded: N new

## 6.3 “Output CSVs not generated”
Check:
- Write permissions
- Correct file paths
- Correct .env overrides
---
# 7.0 Notes & Safety
- Defaults to DATABASE_URL or sqlite:///./petmatch.sqlite.
- For non‑SQLite URLs, you must pass --force (and confirm) to avoid accidental data loss.
- The script deletes the SQLite file when possible; otherwise it drops & recreates tables.
---
# 8.0 Summary
The ETL pipeline is:
- Reliable
- Idempotent
- Protects against duplicates
- Supports both quick demo mode and real dataset mode
- Fully configurable
This ensures PetMatch can be demonstrated instantly and supports a realistic dataset for analysis work.
---