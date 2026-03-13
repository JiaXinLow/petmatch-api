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

Dog breed groups:

- Locally supplied dictionary  
- Non-commercial academic use only