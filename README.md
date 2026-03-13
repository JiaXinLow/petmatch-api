# 🐾 PetMatch API

A small **SQL-backed CRUD Web API** that manages pets and provides filtering, summaries, recommendations, and higher-level analytics insights such as **Return-Risk** and **Welfare/Behavior scoring**.

Built with **FastAPI, SQLAlchemy, and SQLite**.

**Coursework context:**  
COMP3011 — Coursework 1 (Individual)

This README contains **install/run instructions, feature overview, documentation links, and testing notes** required by the brief.

---

# ✨ Features

## 🧱 Core API (CRUD)

### Pet Management

Create / Read / Update / Delete Pets

```
POST   /pets
GET    /pets/{pet_id}
GET    /pets
PUT    /pets/{pet_id}      (partial semantics)
PATCH  /pets/{pet_id}
DELETE /pets/{pet_id}
```

---

### Filtering & Utilities

List distinct values:

```
GET /pets/species
GET /pets/breeds
GET /pets/outcomes
```

SQL-backed summary:

```
GET /pets/summary
```

Uses SQL aggregation for efficiency:

- `COUNT`
- `GROUP BY`
- `AVG`

---

### Health Check

```
GET /health
```

Quick service smoke test.

---

### Validation

- **Pydantic v2**
- Type-safe query parameters
- Non-negative age validation
- Correct HTTP status codes

| Code | Meaning |
|-----|------|
| 201 | Created |
| 204 | Deleted |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |

---

# 🤖 Recommendations

```
GET /pets/recommend
```

Light-weight **content-based recommendation scoring** using:

- Species match
- Size / Energy preference *(optional)*
- Age proximity
- Adoption-likely outcome bonus

Uses **tunable weighted scoring** to rank suitable pets.

---

# 🔍 Advanced Analytics

PetMatch provides two **real-world-inspired analytics endpoints** to support operational decisions for shelters.

---

# 1️⃣ Return-Risk  
### Heuristic Post-Adoption Risk Estimate

Estimates how likely a pet is to be **returned after adoption** using a transparent heuristic based on:

- Age
- Breed group
- Species
- Documentation clarity
- Dark coat visibility
- Cohort adoption rate

---

### Endpoints

```
GET /api/analytics/return-risk/{pet_id}
GET /api/analytics/return-risk/by-external-id/{external_id}
```

Second endpoint is **staff-friendly** for shelters using external IDs.

---

### Example Response

```json
{
  "pet_id": 118,
  "risk_score": 68,
  "components": [
    {"name": "species_other_penalty", "weight": 12},
    {"name": "unknown_sex_penalty", "weight": 8},
    {"name": "dark_coat_penalty", "weight": 5},
    {"name": "mixed_breed_unclassified_penalty", "weight": 4},
    {"name": "low_cohort_adoption_rate_penalty", "weight": 6}
  ],
  "explanation": "Heuristic risk score for potential post-adoption returns."
}
```

---

### Use Cases

- Adoption counselling
- Improving adopter–pet matching
- Identifying pets needing follow-up support

---

# 2️⃣ Welfare / Behavior Score  
### Heuristic Shelter-Stress Estimate

Estimates the **current welfare/stress level** of a pet inside the shelter.

Uses evidence-based signals such as:

- Breed group *(Herding/Sporting have high stimulation needs)*
- Age vulnerability *(senior & puppy welfare)*
- Species enrichment fit
- Documentation quality *(unknown sex)*
- Coat visibility *(minor factor)*

---

### Endpoints

```
GET /api/analytics/welfare/{pet_id}
GET /api/analytics/welfare/by-external-id/{external_id}
```

---

### Example Response

```json
{
  "pet_id": 201,
  "welfare_score": 62,
  "components": [
    {"name": "herding_group_weight", "weight": 12},
    {"name": "senior_age_penalty", "weight": 10}
  ],
  "advisory": [
    "Increase enrichment activities (Herding/Sporting traits).",
    "Provide extra comfort and rest areas for senior animals."
  ],
  "explanation": "Heuristic assessment of possible shelter-stress and welfare needs."
}
```

---

### Use Cases

- Welfare auditing
- Enrichment planning
- Identifying vulnerable animals
- Improving in-shelter animal experience

---

# 🧪 Testing

Run all tests:

```bash
pytest -q
```

Coverage includes:

### Core API

- CRUD operations
- Filtering
- Summary endpoint
- Error pathways (404, 409, 422)

### Recommendation Engine

- Ranking logic
- Edge cases

### Analytics

- Return-Risk  
  - Unit tests
  - Integration tests

- Welfare Score  
  - Unit tests
  - Integration tests

- External-ID lookup variants

---

### Test Setup

Tests use:

- **In-memory SQLite**
- **StaticPool** for shared connection
- **FastAPI dependency override**
- Isolated DB sessions

---

# 🧱 Tech Stack

| Layer | Technology |
|-----|-----|
| Language | Python 3.10+ |
| Framework | FastAPI |
| ORM | SQLAlchemy |
| Validation | Pydantic v2 |
| Database | SQLite |
| Testing | pytest + FastAPI TestClient |
| Dev Tools | uvicorn, dependency injection |

---

# 🚀 Quickstart

## 1️⃣ Clone & Setup

```bash
git clone https://github.com/JiaXinLow/petmatch-api.git
cd petmatch-api

python -m venv .venv
```

Activate environment:

### Windows PowerShell

```bash
. .venv/Scripts/Activate.ps1
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 2️⃣ Run the API

```bash
uvicorn app.main:app --reload
```

Open interactive docs:

```
http://127.0.0.1:8000/docs
```

---

## 3️⃣ Run Tests

```bash
pytest -q
```
---

## 📦 Data Ingestion & ETL (Austin Outcomes)

### Pipeline overview
**Raw inputs**
- `data/raw/Austin_Animal_Center_Outcomes.csv` — pet outcomes dataset  
- `data/raw/dogbreeds.json` — dog breed groups dataset  
**Processing** (via `scripts/run_etl.py`)
- `app/etl/outcomes.py` → cleans & normalizes outcomes → writes `data/processed/pets_clean.csv`
- `app/etl/breeds.py` → flattens dog breed groups → writes `data/processed/breeds_clean.csv`
- `app/etl/seed.py` → idempotent DB load of breeds + pets

---

## Duplicate handling (`external_id`)
- The Austin dataset can contain repeated rows for the same `external_id`.
- To respect the DB **UNIQUE constraint** (`pets.external_id`) and keep imports stable, two protection layers are used:

1️⃣ **ETL-level dedupe**
Implemented in `outcomes.run(...)`
- Drops duplicates by `external_id`
- Keeps the **first occurrence**
- Done before writing `pets_clean.csv`

2️⃣ **Loader-level guard**
Implemented in `app/etl/seed._load_pets(...)`
- Tracks `external_id`s already staged during a load
- Skips duplicates within the same session
- Also skips entries already present in the DB

**Result**
- ETL is **repeatable**
- No `UNIQUE constraint failed`
- Database remains the **single source of truth**

---

# ▶️ Run the full pipeline

```bash
# Windows PowerShell
$env:DATABASE_URL="sqlite:///./petmatch.sqlite"
python scripts/run_etl.py

# macOS / Linux / WSL
export DATABASE_URL="sqlite:///./petmatch.sqlite"
python scripts/run_etl.py
```
After this, the DB will be populated from the processed CSVs.

### Demo vs Full Dataset
You have two ways to get data into the DB:

1. Fast demo seed (3 records) — quick for slides & smoke tests
```bash
# Inserts DEMO-D1 / DEMO-C1 / DEMO-O1
python -m scripts.seed
```

2. Full ETL load — realistic dataset
```bash
python scripts/run_etl.py
```
Use the demo seed when you want instant data; use the ETL when you want the real Austin dataset.

### Resetting the Database (Clean State)
Use scripts/reset_db.py to wipe and rebuild your local DB safely.
#### Common flows
```bash
# Interactive reset (asks for confirmation)
python -m scripts.reset_db

# Non-interactive reset
python -m scripts.reset_db --yes
```

Reset + seed in one go
- Demo data (3 records)
```bash
python -m scripts.reset_db --yes --seed --seed-mode demo
```

- Full dataset via ETL
```bash
python -m scripts.reset_db --yes --seed --seed-mode etl
# Requires raw inputs under data/raw/ (or override paths via .env)
```

### Notes & safety
- Defaults to DATABASE_URL or sqlite:///./petmatch.sqlite.
- For non‑SQLite URLs, you must pass --force (and confirm) to avoid accidental data loss.
- The script deletes the SQLite file when possible; otherwise it drops & recreates tables.

### Configuration (.env)
You can override defaults via environment variables:
```bash
# Database URL (used by app, ETL, and tools)
DATABASE_URL=sqlite:///./petmatch.sqlite

# ETL inputs (defaults are under data/raw/)
OUTCOMES_CSV=data/raw/Austin_Animal_Center_Outcomes.csv
DOGBREEDS_JSON=data/raw/dogbreeds.json

# ETL outputs (processed)
PETS_CLEAN_CSV=data/processed/pets_clean.csv
BREEDS_CLEAN_CSV=data/processed/breeds_clean.csv
```

### Troubleshooting ETL & Seeding
1. “UNIQUE constraint failed: pets.external_id” during ETL
- Cause: duplicated external_id in the raw file or within the same load session.
- Fix: pipeline already handles this in two places (ETL dedupe + loader skip). If you still see it:
  - Ensure you’re running the latest code with dedupe enabled.
  - Re-run a clean cycle:
```bash
python -m scripts.reset_db --yes
python scripts/run_etl.py
```

2. “ETL finished but tables look small/empty”
- Confirm the same DATABASE_URL is used for reset, ETL, and API run (don’t mix DB files).
- Check that the raw files exist under data/raw/ (or the override paths in .env are correct).
- Look for “Wrote pets_clean.csv” and “Pets loaded: N new” in the logs.

**“I want to demo quickly”**
Use:
```bash
python -m scripts.reset_db --yes --seed --seed-mode demo
uvicorn app.main:app --reload
```

### Security reminder (analytics only)
If you set ANALYTICS_API_KEY, all /api/analytics/* routes require:
```bash
X-API-Key: <your-key>
```
For loacl runs:
```bash
# Windows PowerShell
$env:ANALYTICS_API_KEY="demo"
uvicorn app.main:app --reload

# macOS / Linux / WSL
export ANALYTICS_API_KEY="demo"
uvicorn app.main:app --reload
```
Swagger → Authorize → enter the key → analytics calls will include the header automatically.

### Suggested “from zero to demo” commands
```bash
# 0) (optional) Use a known-clean DB + fast demo data
python -m scripts.reset_db --yes --seed --seed-mode demo

# 1) Start API
uvicorn app.main:app --reload

# 2) Try a few endpoints
# Species
curl http://127.0.0.1:8000/api/pets/species

# Summary
curl http://127.0.0.1:8000/api/pets/summary

# Recommend
curl "http://127.0.0.1:8000/api/pets/recommend?species=Dog&limit=3"

# Analytics (if key is set)
curl -H "X-API-Key: demo" \
  "http://127.0.0.1:8000/api/analytics/return-risk/5?window_days=180"
```

---

### 4) Seed demo data (optional, instant demo)

You can insert 3 predictable demo pets (Dog, Cat, Other) **without** running the full ETL:

```bash
# Default local SQLite DB
python scripts/seed.py

# Or target a specific DB:
Windows PowerShell
$env:DATABASE_URL="sqlite:///./petmatch.sqlite"; python -m scripts/seed.py

macOS/Linux
export DATABASE_URL="sqlite:///./petmatch.sqlite"; python -m scripts/seed.py
```

---

# 📄 Documentation

Interactive API documentation:

Swagger UI  
```
http://127.0.0.1:8000/docs
```

ReDoc  
```
http://127.0.0.1:8000/redoc
```

Coursework API documentation PDF:

```
docs/PetMatch_API_Documentation.pdf
```

*(Add the exported PDF here before submission.)*

---

## 🔐 Security (Optional API Key for Analytics)

### Overview
Analytics endpoints expose higher-level, operational insights (e.g., return-risk and welfare scores). These routes can be protected with a simple API key. Protection is **optional** and **disabled by default**, making the API easy to run for local development and marking.

### What is protected
Only the analytics routes require the API key when protection is enabled:

- `GET /api/analytics/return-risk/{pet_id}`
- `GET /api/analytics/return-risk/by-external-id/{external_id}`
- `GET /api/analytics/welfare/{pet_id}`
- `GET /api/analytics/welfare/by-external-id/{external_id}`

All other endpoints (health, browsing/filters, CRUD, summary, recommender) remain open for ease of testing and demos.

---

### How it works
When the environment variable `ANALYTICS_API_KEY` is set, all `/api/analytics/*` requests must include the header:

X-API-Key: <your-key>

- If the header is missing or does not match `ANALYTICS_API_KEY`, the server returns:

```json
401 Unauthorized
{"detail": "Invalid or missing API key"}

If ANALYTICS_API_KEY is not set, analytics endpoints are open (no key required).

### Enable protection

Windows PowerShell:
``` bash
$env:ANALYTICS_API_KEY="demo"
uvicorn app.main:app --reload
```

macOS / Linux / WSL:
```bash
export ANALYTICS_API_KEY="demo"
uvicorn app.main:app --reload
Call analytics with the key
```

cURL:
```bash
curl -H "X-API-Key: demo" \
  "http://127.0.0.1:8000/api/analytics/return-risk/5?window_days=180"
```

Swagger UI:
1. Open http://127.0.0.1:8000/docs
2. Click Authorize
3. Enter your key in the X-API-Key field (e.g., demo)
4. Execute any ```bash /api/analytics/* ``` request

### Notes about Swagger “Authorize”
- The Authorize dialog is a client-side convenience; it stores the header for requests.
- Validity is determined by the server when a request is made (200/404 on success, 401 if key is wrong/missing).
- If the environment key changes, restart the server and re-authorize in Swagger.

### Troubleshooting
1. I keep getting 401
- Ensure ANALYTICS_API_KEY is set in the same shell/session that starts uvicorn.
- Restart the server after setting the variable.
- Re-enter the key in Swagger or send the header correctly with cURL: -H "X-API-Key: <your-key>".

2. Swagger shows “Authorized” but I still get 401
- “Authorized” only attaches the header; the server validates it.
- Re-enter the exact key and try again.

3. Confirm protection is active
- Start server with ANALYTICS_API_KEY set, call any analytics endpoint without the header → expect 401.
- Call again with X-API-Key: <your-key> → expect normal response (200 or 404 depending on data).

### Why only analytics are protected
- Analytics endpoints encapsulate internal heuristics and higher-level operational insights; typically staff-only in real deployments.
- CRUD, browsing, recommendations, and summary endpoints remain open for marking and demos.
- Demonstrates least-privilege design and layered security without adding friction to core endpoints.

### Testing
- A minimal test is included to verify guard behavior:
  - Guard off → endpoints open
  - Guard on → 401 without key
  - Guard on → pass with key

Run:
```bash
pytest -q -k analytics_auth
```

### Design summary
- Simple header-based key: X-API-Key
- Optional by environment toggle: ANALYTICS_API_KEY
- Applied only to /api/analytics/* for least-privilege and low demo friction
- Fully documented in Swagger (Authorize button, 401 responses)

---

## 🔐 Security: Optional API Keys for Analytics & Writes

This API supports **two independent, optional API-key guards** using the same header name (`X-API-Key`), designed to keep **reads open** for demos while protecting **analytics** and **mutating** operations when desired.

### Why this design?
- **Local/classroom demos**: Reads remain open → minimal friction.
- **Least‑privilege**: Protect expensive/sensitive endpoints (analytics) and data‑changing endpoints (writes) when needed.
- **Toggle via env vars**: No code changes to enable/disable.

---

### 🧭 Behavior Summary

- **Header used**: `X-API-Key`
- **Analytics guard** (`ANALYTICS_API_KEY`)
  - **Unset** → guard **OFF** (analytics open)
  - **Set** → requests to `/api/analytics/*` must include `X-API-Key: <ANALYTICS_API_KEY>`
- **Write guard** (`WRITE_API_KEY`)
  - **Unset** → guard **OFF** (writes open)
  - **Set** → `POST/PUT/PATCH/DELETE /api/pets/*` must include `X-API-Key: <WRITE_API_KEY>`
- **Reads** (e.g., `GET /api/pets/{id}`) are **always open**.

Both guards are **independent**. Keys do **not** cross‑work.

---

### 🔧 Environment Variables

Set these before starting the app to enable guards:

```bash
# PowerShell (Windows)
$env:ANALYTICS_API_KEY = "asecret"   # protects /api/analytics/*
$env:WRITE_API_KEY     = "wsecret"   # protects POST/PUT/PATCH/DELETE /api/pets/*

# Start server
uvicorn app.main:app --reload
``

Turn guards off (demo mode):
```bash
# PowerShell (Windows)
Remove-Item Env:ANALYTICS_API_KEY -ErrorAction Ignore
Remove-Item Env:WRITE_API_KEY -ErrorAction Ignore
uvicorn app.main:app --reload
```
On startup, the app logs whether each key is set (masked preview) and which protections are active.

---

# 🗂 Project Structure

```
app/
  main.py
  database.py
  models.py
  schemas.py

  routers/
    pets.py
    health.py
    analytics.py

  services/
    recommender.py
    return_risk.py
    welfare.py

tests/
  test_health.py
  test_pets_crud.py
  test_pets_filter.py
  test_pets_errors.py
  test_pets_semantics_and_summary.py
  test_recommend.py
  test_recommend_edges.py
  test_analytics_return_risk.py
  test_analytics_welfare.py

docs/
  PetMatch_API_Documentation.pdf
```

---

# 🔧 Design Decisions

Key architectural decisions:

- **FastAPI + SQLAlchemy** chosen for performance, readability, and ecosystem support
- **PUT implemented as partial update** (explicitly documented)
- **SQL-based aggregation** for scalable summaries
- **Rule-based analytics** for transparency and explainability
- **Test-driven structure** to ensure business-logic reliability

---

# 📚 References & Licensing
All code written for:
**COMP3011 Coursework**

Datasets:
- **Austin Animal Outcomes Dataset (public)**  
  - Cleaned and preprocessed internally
- **Dog breed groups**
  - Locally supplied dictionary  
  - Non-commercial academic use only