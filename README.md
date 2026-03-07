# PetMatch API

A small, SQL-backed CRUD Web API that manages pets and provides filtering, summaries, and a simple recommendation capability.  
Built with **FastAPI** + **SQLAlchemy** + **SQLite** for local execution.  

> **Coursework context:** COMP3011 — Coursework 1 (Individual). This README contains install/run instructions, docs links, and testing notes required by the brief.

---

## Features

- **CRUD for Pets**: `POST /pets`, `GET /pets/{id}`, `GET /pets`, `PUT /pets/{id}`, `PATCH /pets/{id}`, `DELETE /pets/{id}`  
- **Filtering & Utilities**:  
  - Distinct species/outcome types/breeds  
  - Summary with **SQL `COUNT/GROUP BY/AVG`** (`/pets/summary`)  
- **Recommendations**: `/pets/recommend` — weighted scoring using species, optional size/energy preferences, age proximity, and an adoption bonus  
- **Health**: `/health` for quick smoke checks  
- **Validation**: Pydantic v2 with non‑negative `age_months`, typed query params, and proper HTTP status codes (201/204/404/409/422)  
- **Tests**: Pytest suite with in‑memory SQLite (**StaticPool**) covering smoke, CRUD, filtering, summary, recommender logic, and error/edge cases

---

## Tech Stack

- **Language**: Python 3.10+  
- **Framework**: FastAPI  
- **ORM / DB**: SQLAlchemy + SQLite (local dev)  
- **Validation**: Pydantic v2  
- **Test**: pytest, FastAPI TestClient, in‑memory SQLite with dependency override

---

## Quickstart

### 1) Clone & set up

```bash
git clone https://github.com/JiaXinLow/petmatch-api.git
cd petmatch-api

python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt