# 🐾 PetMatch API
A lightweight **SQL-backed CRUD Web API** for managing shelter pets, performing filtering and summaries, and providing higher-level operational insights such as **Return‑Risk** and **Welfare/Behavior scoring**, built with **FastAPI, SQLAlchemy, and SQLite**.

---
# Table of Contents
- 1.0 Overview
- 2.0 Quickstart (Run the API Immediately)
- 3.0 Links to Documentation
  - 3.1 Interactive Swagger Docs
  - 3.2 API Documentation PDF
- 4.0 Installation (Full Instructions)
- 5.0 Feature Overview
  - 5.1 CRUD (Pets)
  - 5.2 Filtering (Pets)
  - 5.3 SQL Summary
  - 5.4 Recommendation Engine
  - 5.5 Advanced Analytics
  - 5.6 Health Check
- 6.0 Testing Information
  - 6.1 Run the full suite
  - 6.2 Run subsets (by marker, path, or keyword)
  - 6.3 What the tests cover (file-by-file)
  - 6.4 Expected coverage (functional areas)
  - 6.5 Test infrastructure & fixtures
  - 6.6 Useful pytest options
  - 6.7 CI (continuous integration)
- 7.0 Project Structure
- 8.0 Design Decisions
  - 8.1 Tech Stack
  - 8.2 Validation Approach
  - 8.3 Architecture Rationale
- 9.0 ETL Pipeline (Austin Animal Center Dataset)
- 10.0 Optional Security (API Keys)
- 11.0 References and Licensing
- 12.0 Additional Docs

---
# 1.0 Overview
PetMatch is a FastAPI-based service that supports:
- Full **CRUD** for pets  
- Filtering & summary endpoints  
- A **content‑based recommender**  
- Two advanced analytics models:  
  - Return‑Risk (post‑adoption risk estimate)  
  - Welfare/Stress score (in‑shelter wellbeing estimate)  
- Optional security guards for analytics & mutating requests  
- A complete ETL pipeline for the Austin Animal Center dataset 

---
# 2.0 Quickstart (Run the API Immediately)
You can deploy using the hosted version:
👉 Live Deployment: https://petmatch-api-mby0.onrender.com

Or run it locally:
```bash
git clone https://github.com/JiaXinLow/petmatch-api.git
cd petmatch-api

python -m venv .venv
# macOS & Linux
source .venv/bin/activate  
# Windows
.\.venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

```bash
Open Swagger UI: http://127.0.0.1:8000/docs
Open ReDoc: http://127.0.0.1:8000/redoc
```
---
# 3.0 Links to Documentation
## 3.1 Interactive Swagger Docs  
The API ships with auto-generated OpenAPI documentation.
- Swagger UI: http://127.0.0.1:8000/docs  
- ReDoc: http://127.0.0.1:8000/redoc  
These pages are available as soon as the server is running. 

## 3.2 API Documentation PDF  
A full, coursework-ready API documentation file (endpoints, request/response examples, status codes, and authentication notes) is provided here:

📄 `docs/PetMatch_API_Documentation.pdf`

---
# 4.0 Installation (Full Instructions)
1. Create and activate virtual environment
```bash
python -m venv .venv
source .venv/bin/activate       # macOS / Linux
. .venv/Scripts/Activate.ps1    # Windows PowerShell
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run server
```bash
uvicorn app.main:app --reload
```
--- 
# 5.0 Features Overview

## 5.1 CRUD (Pets)
### PURPOSE  
Create, read, update, and delete pet records in the PetMatch dataset.

### USE CASES  
- Intake workflows  
- Administrative data correction  
- Data import/export pipelines  
- Editing pet details before analytics or recommendations  

### INTERPRETATION  
- `POST` returns the created record (`201 Created`)  
- `GET` returns a pet or list of pets  
- `PATCH` applies partial updates  
- `DELETE` removes a pet (`204 No Content`)  
- Write operations require a **write API key**  

### Endpoints  
```bash
POST    /api/pets
GET     /api/pets/{id}
GET     /api/pets
PATCH   /api/pets/{id}
DELETE  /api/pets/{id}
```

## 5.2 Filtering (Pets)
### PURPOSE  
Expose distinct categorical values used throughout the dataset to support browsing, filtering, and UI dropdowns.

### USE CASES  
- Populate filter controls (species selector, breed list, outcome types)
- Validate user input against available categories
- Create dynamic search interfaces

### INTERPRETATION  
- Each endpoint returns a sorted list of unique values
- Species and outcomes are normalized internally
- Useful as lightweight metadata endpoints

### Endpoints  
```bash
GET /api/pets/species
GET /api/pets/breeds
GET /api/pets/outcomes
```

## 5.3 SQL Summary (Aggregations)
### PURPOSE  
Return a single summary payload of dataset‑wide statistics, computed efficiently using SQL aggregations (COUNT, GROUP BY, AVG, filtered CASE logic).

### USE CASES  
- Power dashboards and admin panels
- Produce top‑level insights for BI and reporting
- Quickly assess data quality (e.g., spikes in "Unknown")
- Provide aggregates to frontend widgets

### INTERPRETATION  
- Includes totals, species counts, outcome counts, age buckets, top breeds
- Computes adoption & sterilization rates
- Includes AKC‑style group adoption stats if DOGBREEDS_JSON is present
- Extremely fast because results are computed database‑side

### Endpoints
```bash
GET /api/pets/summary
```

## 5.4 Recommendation Engine
### PURPOSE  
Return recommended pets using weighted ranking logic incorporating species match, age similarity, and (for dogs) breed‑group affinity signals.

### USE CASES  
- “Recommended for You” UI components
- Counselor‑assisted matchmaking
- Automated sorting for pet search pages
- Prioritized ordering of high‑match pets

### INTERPRETATION  
- For Dog, breed groups are loaded from DOGBREEDS_JSON
- Higher scores rank first
- target_age is optional but improves ranking precision
- /pets/recommend-debug provides full score breakdown

### Endpoints
```bash
GET /api/pets/recommend
GET /api/pets/recommend-debug
```

## 5.5 Advanced Analytics
PetMatch includes two real‑world‑inspired analytics endpoints to support shelter operational decisions.

1. Heuristic Post-Adoption Risk Estimate
### PURPOSE  
Predict which pets may have a higher likelihood of being returned post‑adoption, using transparent heuristic components.

### USE CASES  
- Adoption counselling
- Early intervention & follow‑up support
- Prioritizing pets needing better photos, descriptions, or enrichment
- Understanding risk factors for each pet

### INTERPRETATION  
- Returns a risk_score (0–100)
- Component breakdown reveals how features contributed
- External‑ID variant supports shelters that rely on external system IDs
- Heuristic: intended to assist, not replace human judgement

### Endpoints
```bash
GET /api/analytics/return-risk/{pet_id}
GET /api/analytics/return-risk/by-external-id/{external_id}
```

2. Heuristic Welfare / Stress Level Estimate
### PURPOSE  
Estimate the current stress or welfare risk for a pet inside the shelter using behavioral and breed‑based signals.

### USE CASES  
- Welfare audits
- Prioritizing enrichment
- Identifying vulnerable or stressed animals
- Daily kennel monitoring & welfare dashboards

### INTERPRETATION  
- Returns welfare_score (0–100)
- Includes evidence‑based advisory suggestions
- Accounts for breed group stimulation needs, age vulnerability, documentation clarity
- External‑ID lookup supported

### Endpoints
```bash
GET /api/analytics/welfare/{pet_id}
GET /api/analytics/welfare/by-external-id/{external_id}
```

## 5.6 Health Check
### PURPOSE  
Provide a lightweight check indicating the API is running and able to respond.

### USE CASES
- Load balancer health probes
- Uptime monitoring
- CI/CD smoke tests
- Developer sanity checks

### INTERPRETATION  
- Always returns { "status": "ok" }
- Does not test DB connectivity unless extended

### Endpoints
```bash
GET /health
```
---
# 6.0 Testing Information
## 6.1 Run the full suite
Run all tests:
```bash
pytest -q
```

## 6.2 Run subsets (by marker, path, or keyword)
```bash
# Only analytics tests
pytest -q tests/test_analytics_*.py

# Only CRUD tests
pytest -q -k "pets_crud or pets_semantics"

# Only security/authorization checks
pytest -q -k "auth or write_auth or dual_keys"

# Single test file
pytest -q tests/test_pets_crud.py
```

## 6.3 What the tests cover (file-by-file)
- **tests/test_health.py** — service liveness via GET /health; asserts 200 response and payload shape.
- **tests/test_pets_crud.py** — CRUD lifecycle for /api/pets (POST/GET/PATCH/DELETE), including 201/200/204 codes and schema validation.
- **tests/test_pets_filter.py** — filter/browse endpoints (/api/pets/species, /breeds, /outcomes) return distinct, stable value sets.
- **tests/test_pets_errors.py** — negative paths & error semantics (404 not found, 409 conflict on uniqueness, 422 validation).
- **tests/test_pets_semantics_and_summary.py** — SQL aggregations for /api/pets/summary (COUNT / GROUP BY / AVG) and business semantics (e.g., age handling).
- **tests/test_recommend.py** — tests the recommendation engine’s happy paths, ensuring correct species filtering, scoring logic (age, breed‑group, sterilization bonus), limit handling, and full debug score breakdown using mock database sessions.
- **tests/test_recommend_edges.py** — edge cases (empty results, ties, limits, invalid params) for /api/pets/recommend.
- **tests/test_return_risk_unit.py** — unit tests for heuristic Return‑Risk scoring components and weight combinations.
- **tests/test_welfare_unit.py** — unit tests for Welfare/Stress scoring components, advisories, and thresholds.
- **tests/test_analytics_return_risk.py** — integration tests for /api/analytics/return-risk/{id} and .../by-external-id/{external_id} (payload shape + HTTP codes).
- **tests/test_analytics_welfare.py** — integration tests for /api/analytics/welfare/{id} and .../by-external-id/{external_id} (payload shape + advisories).
- **tests/test_analytics_auth.py** — analytics guard behavior: open when ANALYTICS_API_KEY unset; 401 when set without key; success with correct X-API-Key.
- **tests/test_write_auth.py** — write guard behavior for POST/PUT/PATCH/DELETE when WRITE_API_KEY is set (401 without key, pass with valid key).
- **tests/test_dual_keys_matrix.py** — combined matrix of ANALYTICS_API_KEY and WRITE_API_KEY states to ensure independence and no cross‑leaks.

## 6.4 Expected coverage (functional areas)
- CRUD operations for pets
- Filtering & SQL summary
- Recommendation scoring (happy paths + edges)
- Analytics models (unit + integration)
- Optional API‑key security (analytics + writes)
- Robust error handling (404/409/422)

## 6.5 Test infrastructure & fixtures
- **Database**: in‑memory SQLite with StaticPool shared connection for consistent transactional state across requests.
- **Dependency overrides**: FastAPI TestClient + app overrides to inject the in‑memory session instead of file‑backed SQLite.
- **Isolation**: each test seeds only what it needs; teardown handled by fixture scopes.
- **Environment**: security tests set/unset ANALYTICS_API_KEY and WRITE_API_KEY per case to assert 401/200 behaviors.

Key fixtures live in **tests/conftest.py**:
  - **client** — FastAPI TestClient with dependency overrides.
  - **session** — shared in‑memory SQLAlchemy session bound to StaticPool.
  - Utility seeders for demo pets/breeds as needed.

## 6.6 Useful pytest options
```bash
# Verbose + show print/logs on failure
pytest -v -q

# Stop at first failure
pytest -x

# Filter by test name substring
pytest -k recommend

# Show 10 slowest tests
pytest --durations=10
```

## 6.7 CI (continuous integration)
The repository includes a minimal GitHub Actions workflow under **.github/workflows/ci.yml** that:
- Sets up Python & installs dependencies
- Runs pytest on every push / PR
- Surfaces failures inline for quick triage
---

# 7.0 Project Structure
```
app/
  __init__.py
  main.py
  database.py
  models.py
  schemas.py
  schemas_errors.py
  security.py

  routers/
    __init__.py
    analytics.py
    health.py
    pets_crud.py
    pets_filters.py
    pets_recommender.py
    pets_stats_reco.py

  services/
    __init__.py
    recommender.py
    return_risk.py
    welfare.py
  
  etl/
    __init__.py
    breeds.py
    config.py
    models.py
    outcomes.py
    seed.py
  
  utils/
    __init__.py
    pet_helpers.py
    breed_utils.py

tests/
  conftest.py
  test_health.py
  test_pets_crud.py
  test_pets_filter.py
  test_pets_errors.py
  test_pets_semantics_and_summary.py
  test_recommend.py
  test_recommend_edges.py
  test_return_risk_unit.py
  test_welfare_unit.py
  test_write_auth.py
  test_analytics_return_risk.py
  test_analytics_welfare.py
  test_analytics_auth.py
  test_dual_keys_matrix.py

docs/
  analytics.md
  etl.md
  security.md
  PetMatch_API_Documentation.pdf

.github/workflows/ci.yml

data/
  petmatch.sqlite
  processed/
    breeds_clean.csv
    pets_clean.csv
  raw/
    Austin_Animal_Center_Outcomes.csv
    dogbreeds.json

scripts/
  reset_db.py
  run_etl.py
  seed.py

.gitignore

README.md

render.yaml

requirements.txt
```
---
# 8.0 Design Decisions
## 8.1 Tech Stack

| Layer | Technology |
|-----|-----|
| Language | Python 3.10+ |
| Framework | FastAPI |
| ORM | SQLAlchemy |
| Validation | Pydantic v2 |
| Database | SQLite |
| Testing | pytest + FastAPI TestClient |
| Dev Tools | uvicorn, dependency injection |

## 8.2 Validation Approach
**Pydantic v2**
- Type-safe query parameters
- Non-negative age validation
- Correct HTTP status codes

| Code | Meaning |
|------|---------|
| 200  | OK — successful request |
| 201  | Created — resource successfully created |
| 204  | No Content — resource deleted successfully |
| 401  | Unauthorized — missing or invalid API key |
| 404  | Not Found — resource does not exist |
| 409  | Conflict — duplicate resource (e.g., external_id already exists) |
| 422  | Validation Error — invalid query/path/body input |
| 500  | Internal Server Error — unexpected backend failure |
| 503  | Service Unavailable — database or dependency unavailable |

## 8.3 Architecture Rationale
- **FastAPI + SQLAlchemy** chosen for clarity, async readiness, and clean schema structure
- **SQLite** used for simplicity and portability
- **PUT implemented as partial semantics** (explicitly documented in API PDF)
- **Analytics models are rule-based**: transparent and explainable
- **Testing-first approach** ensures correctness and stability
- **ETL** built to be idempotent (repeatable loads, duplicate protection)
- **Security** uses lightweight, toggleable API-key guards
---
# 9.0 ETL Pipeline (Austin Animal Center Dataset)
Raw inputs:
- data/raw/Austin_Animal_Center_Outcomes.csv
- data/raw/dogbreeds.json

Pipeline (scripts/run_etl.py):
- Clean outcomes → data/processed/pets_clean.csv
- Flatten breed groups → data/processed/breeds_clean.csv
- Load into SQLite DB (petmatch.sqlite)

1. Run the ETL
```bash
export DATABASE_URL="sqlite:///./petmatch.sqlite"
python scripts/run_etl.py
```

2. Demo Seed (Fast 3-Pet Example)
```bash
python -m scripts.seed
```

3. Reset Database
```bash
python -m scripts.reset_db --yes
```
Full ETL instructions and troubleshooting are in:
```bash
/docs/etl.md
```
---
# 10.0 Optional Security (API Keys)
Two independent guards using the same header:
**X-API-Key**

| Guard Type | Environment Variable   | Protects |
|-----------|--------------------------|----------|
| Analytics | `ANALYTICS_API_KEY`     | `/api/analytics/*` |
| Writes    | `WRITE_API_KEY`         | `POST / PUT / PATCH / DELETE /api/pets/*` |

Enable:
```bash
# Set keys for macOS / Linux / WSL (bash/zsh) only
export ANALYTICS_API_KEY="asecretkey"
export WRITE_API_KEY="wsecretkey"

# Set keys for Window PowerShell session only
$env:WRITE_API_KEY = "wsecretkey"
$env:ANALYTICS_API_KEY = "asecretkey"

# (Re)start the API from this same shell
uvicorn app.main:app --reload
```
Full explanation is in:
**/docs/security.md**

---
# 11.0 References and Licensing
Dataset sources:
- Austin Animal Center Outcomes (public dataset — academic use)
- Dog breed groups (local JSON file)

All code written for:
**COMP3011 Web Services & Web Data — Coursework 1**

---
# 12.0 Additional Documentation
These extra docs keep the README clean and meet best-practice expectations:
- /docs/PetMatch_API_Documentation.pdf
- /docs/etl.md
- /docs/security.md
- /docs/analytics.md 
Everything required by the brief is either in this README or linked here.
---
