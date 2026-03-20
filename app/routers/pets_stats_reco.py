# app/routers/pets_summary.py
from __future__ import annotations

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_

from app.database import get_db
from app.models import Pet
from app.schemas import (
    SummaryResponse,
    TopBreed,
    MonthlyOutcome,
    GroupOutcomeStat,
)
from app.utils.breed_utils import normalize_breed_key, split_breed_tokens

router = APIRouter(tags=["pets.summary"])

# ------------------------------
# Load breed→groups mapping once
# ------------------------------
DOGBREEDS_JSON = Path(os.getenv("DOGBREEDS_JSON", "data/raw/dogbreeds.json")).resolve()

GROUP_LABELS = {
    "herding",
    "sporting",
    "toy",
    "hound",
    "terrier",
    "working",
    "non-sporting",
}
GROUP_LABELS_CANON = {g: g for g in GROUP_LABELS}


def looks_like_group_label(s: str) -> bool:
    return isinstance(s, str) and s.strip().lower() in GROUP_LABELS_CANON


def detect_format(raw: Dict) -> str:
    if not raw:
        return "breed_to_groups"

    keys = list(raw.keys())
    key_is_group = sum(1 for k in keys[:200] if looks_like_group_label(k))
    if key_is_group >= max(3, len(keys[:200]) // 2):
        return "group_to_breeds"

    # Check values
    values: List[str] = []
    for v in list(raw.values())[:200]:
        if isinstance(v, list):
            values.extend([x for x in v if isinstance(x, str)])
    if values:
        val_is_group = sum(1 for x in values[:400] if looks_like_group_label(x))
        if val_is_group >= max(3, len(values[:400]) // 2):
            return "breed_to_groups"

    return "breed_to_groups"


def build_breed_to_groups(raw: Dict) -> Dict[str, List[str]]:
    mapping: Dict[str, set] = defaultdict(set)
    fmt = detect_format(raw)

    if fmt == "group_to_breeds":
        for group, breeds in raw.items():
            if not isinstance(group, str) or not isinstance(breeds, list):
                continue
            grp = group.strip()
            for breed in breeds:
                if not isinstance(breed, str):
                    continue
                for token in split_breed_tokens(breed):
                    mapping[token].add(grp)
    else:
        for breed, groups in raw.items():
            if not isinstance(breed, str) or not isinstance(groups, list):
                continue
            clean_groups = [g.strip() for g in groups if isinstance(g, str) and g.strip()]
            for token in split_breed_tokens(breed):
                for g in clean_groups:
                    mapping[token].add(g)

    return {b: sorted(gs) for b, gs in mapping.items() if gs}


def load_breed_groups() -> Dict[str, List[str]]:
    if not DOGBREEDS_JSON.exists():
        return {}
    try:
        with open(DOGBREEDS_JSON, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        return build_breed_to_groups(raw)
    except Exception:
        return {}


BREED_GROUPS = load_breed_groups()


# ----------------------------------------
# Single unified summary endpoint
# ----------------------------------------
@router.get(
    "/pets/summary",
    summary="Dataset summary: counts, rates, age buckets, top breeds, and group outcomes",
    description="""
### PURPOSE
Provide a **single payload of high-level summary statistics** for the current pets dataset,
including counts, rates, age distribution, top breeds, and AKC-style group outcome stats
(if the dog breed mapping is available).

### USE CASES
- Power **overview dashboards** and landing pages  
- Enable quick QA checks on data health (e.g., spikes in "Unknown" outcomes)  
- Support reporting and trend exploration without multiple round-trips  
- Feed downstream analytics that need basic aggregates and lookup tables  

### INTERPRETATION
- **Totals & averages**  
  - `total_pets`: total rows in the `Pet` table  
  - `average_age_months`: arithmetic mean of `age_months` (may be `null` if unknown)  
- **Counts**  
  - `species_counts`: counts per stored/normalized species (missing → `"Unknown"`)  
  - `outcome_counts`: counts per `outcome_type` (missing → `"Unknown"`)  
  - `outcome_counts_by_species`: nested counts per species × outcome  
- **Rates**  
  - `adoption_rate`: `Adoption / (all outcomes excluding "Unknown")`  
    *(This implementation counts only plain "Adoption" as positive; you can change to include "Rto-Adopt" if desired.)*  
  - `sterilization_rate`: share of rows with `sex_upon_outcome` containing **"spay"** or **"neuter"** (case-insensitive),
    over all rows where `sex_upon_outcome` is **not null**  
- **Age distribution**  
  - Buckets: `0–5`, `6–11`, `12–23`, `24–59`, `60+` months (inclusive ranges)  
- **Top breeds**  
  - Top 10 `breed_name_raw` values by count (nulls excluded; `"Unknown"` used for blank)  
- **Group outcomes (AKC-like)**  
  - Uses `DOGBREEDS_JSON` (if present) to map breed strings to **up to 2 groups**  
  - Aggregates outcomes per group and derives an `adoption_rate` per group using
    the same definition as above  
  - If the mapping is missing or a breed isn't recognized, that record contributes no group stats  
""",
    response_model=SummaryResponse,
    response_description="Aggregated summary statistics for the current dataset",
    responses={
        200: {
            "description": "Summary payload",
            "content": {
                "application/json": {
                    "examples": {
                        "typical": {
                            "summary": "Typical dataset",
                            "value": {
                                "total_pets": 12450,
                                "species_counts": {"Dog": 8000, "Cat": 4200, "Other": 250},
                                "average_age_months": 28.7,
                                "outcome_counts": {
                                    "Adoption": 7200,
                                    "Transfer": 1100,
                                    "Euthanasia": 120,
                                    "Return to Owner": 600,
                                    "Unknown": 50
                                },
                                "outcome_counts_by_species": {
                                    "Dog": {"Adoption": 5000, "Transfer": 700, "Return to Owner": 500, "Unknown": 30},
                                    "Cat": {"Adoption": 2100, "Transfer": 350, "Euthanasia": 100, "Unknown": 15},
                                    "Other": {"Adoption": 100, "Transfer": 50, "Unknown": 5}
                                },
                                "adoption_rate": 0.80,
                                "sterilization_rate": 0.76,
                                "age_buckets": {"0-5": 1800, "6-11": 2100, "12-23": 3000, "24-59": 3500, "60+": 2050},
                                "top_breeds": [
                                    {"breed_name_raw": "Mixed", "count": 2150},
                                    {"breed_name_raw": "Domestic Shorthair", "count": 900},
                                    {"breed_name_raw": "Labrador Retriever", "count": 650}
                                ],
                                "group_outcomes": [
                                    {
                                        "group": "Herding",
                                        "outcome_counts": {"Adoption": 850, "Transfer": 90, "Unknown": 5},
                                        "adoption_rate": 0.89
                                    },
                                    {
                                        "group": "Sporting",
                                        "outcome_counts": {"Adoption": 780, "Transfer": 120, "Unknown": 12},
                                        "adoption_rate": 0.82
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            "headers": {
                "Cache-Control": {
                    "schema": {"type": "string"},
                    "description": "Clients may cache summaries briefly; e.g., 'max-age=60'"
                },
                "ETag": {
                    "schema": {"type": "string"},
                    "description": "Entity tag for conditional requests if you add it upstream"
                },
            },
        },
        422: {"description": "Validation error"},
    },
)
def pets_summary(db: Session = Depends(get_db)):
    # ---------- Base totals ----------
    total = db.query(func.count(Pet.id)).scalar()

    avg_age = db.query(func.avg(Pet.age_months)).scalar()
    average_age_months = float(avg_age) if avg_age is not None else None

    species_counts_rows = (
        db.query(Pet.species, func.count())
        .group_by(Pet.species)
        .all()
    )
    species_counts = {s or "Unknown": c for s, c in species_counts_rows}

    # ---------- Outcomes ----------
    outcome_counts_rows = (
        db.query(Pet.outcome_type, func.count())
        .group_by(Pet.outcome_type)
        .all()
    )

    outcome_counts: Dict[str, int] = {}
    for otype, cnt in outcome_counts_rows:
        key = str(otype) if otype is not None else "Unknown"
        outcome_counts[key] = cnt

    rows_species_outcomes = (
        db.query(Pet.species, Pet.outcome_type, func.count())
        .group_by(Pet.species, Pet.outcome_type)
        .all()
    )
    outcome_counts_by_species: Dict[str, Dict[str, int]] = {}
    for species, otype, cnt in rows_species_outcomes:
        sp = species or "Unknown"
        oc = str(otype) if otype is not None else "Unknown"
        outcome_counts_by_species.setdefault(sp, {})
        outcome_counts_by_species[sp][oc] = cnt

    adopted = outcome_counts.get("Adoption", 0)
    rto_adopt = outcome_counts.get("Rto-Adopt", 0)  # currently not counted in rate below
    positive = adopted  # or: adopted + rto_adopt if you choose

    total_resolved = sum(outcome_counts.values()) - outcome_counts.get("Unknown", 0)
    adoption_rate: Optional[float] = positive / total_resolved if total_resolved > 0 else None

    # ---------- Sterilization rate ----------
    sterilized_count = (
        db.query(func.count())
        .filter(
            and_(
                Pet.sex_upon_outcome.isnot(None),
                func.lower(Pet.sex_upon_outcome).like("%spay%"),
            )
        )
        .scalar()
        +
        db.query(func.count())
        .filter(
            and_(
                Pet.sex_upon_outcome.isnot(None),
                func.lower(Pet.sex_upon_outcome).like("%neuter%"),
            )
        )
        .scalar()
    )
    denom = db.query(func.count()).filter(Pet.sex_upon_outcome.isnot(None)).scalar()
    sterilization_rate = sterilized_count / denom if denom else None

    # ---------- Age buckets ----------
    age_row = db.query(
        func.sum(case((Pet.age_months.between(0, 5), 1), else_=0)),
        func.sum(case((Pet.age_months.between(6, 11), 1), else_=0)),
        func.sum(case((Pet.age_months.between(12, 23), 1), else_=0)),
        func.sum(case((Pet.age_months.between(24, 59), 1), else_=0)),
        func.sum(case((Pet.age_months >= 60, 1), else_=0)),
    ).one()

    age_buckets = {
        "0-5": int(age_row[0] or 0),
        "6-11": int(age_row[1] or 0),
        "12-23": int(age_row[2] or 0),
        "24-59": int(age_row[3] or 0),
        "60+": int(age_row[4] or 0),
    }

    # ---------- Top breeds ----------
    breeds_rows = (
        db.query(Pet.breed_name_raw, func.count())
        .filter(Pet.breed_name_raw.isnot(None))
        .group_by(Pet.breed_name_raw)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    )
    top_breeds: List[TopBreed] = [
        TopBreed(breed_name_raw=(b or "Unknown"), count=c)
        for b, c in breeds_rows
    ]

    # ---------- Per-group (AKC) outcome stats ----------
    group_outcome_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    pet_rows = (
        db.query(Pet.breed_name_raw, Pet.outcome_type)
        .filter(Pet.breed_name_raw.isnot(None), Pet.outcome_type.isnot(None))
        .all()
    )

    def breed_to_groups(breed: str) -> List[str]:
        full = normalize_breed_key(breed)
        groups = BREED_GROUPS.get(full)

        if not groups:
            for token in split_breed_tokens(breed):
                if token == full:
                    continue
                g = BREED_GROUPS.get(token)
                if g:
                    groups = g
                    break

        return groups[:2] if groups else []

    for breed_name_raw, otype in pet_rows:
        groups = breed_to_groups(breed_name_raw)
        if not groups:
            continue

        outcome_key = str(otype) if otype is not None else "Unknown"

        for g in groups:
            group_outcome_counts[g][outcome_key] += 1

    group_outcomes: List[GroupOutcomeStat] = []
    for group_name, counts in sorted(group_outcome_counts.items()):
        adopted_g = counts.get("Adoption", 0)
        rto_adopt_g = counts.get("Rto-Adopt", 0)  # currently not counted in rate below
        positive_g = adopted_g  # or: adopted_g + rto_adopt_g

        total_resolved_g = sum(counts.values()) - counts.get("Unknown", 0)
        rate_g = positive_g / total_resolved_g if total_resolved_g > 0 else None

        group_outcomes.append(
            GroupOutcomeStat(
                group=group_name,
                outcome_counts=dict(counts),
                adoption_rate=rate_g,
            )
        )

    return SummaryResponse(
        total_pets=int(total or 0),
        species_counts=species_counts,
        average_age_months=average_age_months,
        outcome_counts=outcome_counts,
        outcome_counts_by_species=outcome_counts_by_species,
        adoption_rate=adoption_rate,
        sterilization_rate=sterilization_rate,
        age_buckets=age_buckets,
        top_breeds=top_breeds,
        group_outcomes=group_outcomes,
    )