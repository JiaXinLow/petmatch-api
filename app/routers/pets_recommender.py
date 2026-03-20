from __future__ import annotations

from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import json
from pathlib import Path
import logging
import os
from collections import defaultdict, Counter
from pydantic import BaseModel, Field  # <- for debug response schema

from app.database import get_db
from app.schemas import PetRead
from app.services.recommender import (
    recommend_pets,
    group_score,
    age_similarity,
    is_sterilized,
    get_group_rates,
)
from app.utils.pet_helpers import normalize_species, pet_to_read
from app.utils.breed_utils import normalize_breed_key, split_breed_tokens

router = APIRouter(tags=["pets.recommend"])

# -------------------------------
# Logger
# -------------------------------
logger = logging.getLogger("petmatch.pets_recommender")

# -------------------------------
# Paths
# -------------------------------
BREED_FILE = Path(os.getenv("DOGBREEDS_JSON", "data/raw/dogbreeds.json")).resolve()

# -------------------------------
# Helpers for format detection
# -------------------------------

GROUP_LABELS = {
    "herding", "sporting", "toy", "hound", "terrier", "working", "non-sporting",
}
GROUP_LABELS_CANON = {g: g for g in GROUP_LABELS}

def looks_like_group_label(s: str) -> bool:
    return s.strip().lower() in GROUP_LABELS_CANON

def detect_format(raw: Dict) -> str:
    """
    Return 'group_to_breeds' or 'breed_to_groups' using robust heuristics:
    - If a majority of keys look like group labels, it's group->breeds.
    - Else, inspect sample of values: if a majority of their elements look like group labels,
      it's breed->groups.
    - Fallback to breed->groups (safer for your use-case).
    """
    if not raw:
        return "breed_to_groups"

    keys = list(raw.keys())
    # Heuristic 1: check keys
    key_is_group = sum(1 for k in keys[:200] if isinstance(k, str) and looks_like_group_label(k))
    if key_is_group >= max(3, len(keys[:200]) // 2):  # majority of sample keys are group labels
        return "group_to_breeds"

    # Heuristic 2: inspect values' contents
    val_elems = []
    for v in list(raw.values())[:200]:
        if isinstance(v, list):
            val_elems.extend([x for x in v if isinstance(x, str)])
    if val_elems:
        elem_is_group = sum(1 for e in val_elems[:400] if looks_like_group_label(e))
        # if most value elements look like group labels, it's breed->groups
        if elem_is_group >= max(3, len(val_elems[:400]) // 2):
            return "breed_to_groups"

    # Default for safety
    return "breed_to_groups"

def build_breed_to_groups(raw: Dict) -> Dict[str, List[str]]:
    """
    Produces a normalized mapping: normalized_breed_key -> sorted list of group names.

    Accepts either:
      1) group -> [breeds, ...]
      2) breed -> [groups, ...]
    Expands multi-breed names so that both:
      - the full string key
      - each component token
    map to the union of groups for better matching coverage.
    """
    fmt = detect_format(raw)
    breed_to_groups: Dict[str, set] = defaultdict(set)

    if fmt == "group_to_breeds":
        # Example:
        # { "Herding": ["Australian Shepherd/Dalmatian", "German Shepherd", ...], ... }
        for group, breeds in raw.items():
            if not isinstance(group, str) or not isinstance(breeds, list):
                continue
            grp = group.strip()
            if not grp:
                continue
            for breed in breeds:
                if not isinstance(breed, str):
                    continue
                # Expand: full key + component tokens
                for token in split_breed_tokens(breed):
                    breed_to_groups[token].add(grp)
        detected = "group→breeds"
    else:
        # Example:
        # { "Australian Shepherd/Dalmatian": ["Non-Sporting","Herding"], ... }
        for breed, groups in raw.items():
            if not isinstance(breed, str) or not isinstance(groups, list):
                continue
            clean_groups = [g.strip() for g in groups if isinstance(g, str) and g.strip()]
            if not clean_groups:
                continue
            # Expand: full key + component tokens
            for token in split_breed_tokens(breed):
                for g in clean_groups:
                    breed_to_groups[token].add(g)
        detected = "breed→groups"

    # Convert sets to sorted lists
    out: Dict[str, List[str]] = {b: sorted(gs) for b, gs in breed_to_groups.items() if gs}

    # Diagnostics
    sample_keys = list(out.keys())[:5]
    group_counts = Counter(g for gs in out.values() for g in gs)
    logger.info(
        "build_breed_to_groups: detected format=%s | breeds_mapped=%d | distinct_groups=%d | sample_keys=%s",
        detected, len(out), len(group_counts), sample_keys
    )

    # Sanity warning if we ended up with very few entries
    if len(out) < 20:
        logger.warning(
            "BREED_GROUPS looks unusually small (len=%d). Check your dogbreeds.json and detection.",
            len(out)
        )

    return out

# -------------------------------
# Load breed groups once at startup
# -------------------------------
BREED_GROUPS: Dict[str, List[str]] = {}
if BREED_FILE.exists():
    try:
        with open(BREED_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raise ValueError("dogbreeds.json must be an object mapping.")
        BREED_GROUPS = build_breed_to_groups(raw)
        if not BREED_GROUPS:
            logger.warning("BREED_GROUPS ended up empty after normalization/inversion.")
    except json.JSONDecodeError as e:
        logger.warning("Could not parse %s: %s", BREED_FILE, e)
    except Exception as e:
        logger.exception("Error building BREED_GROUPS from %s: %s", BREED_FILE, e)
else:
    logger.warning("Breed file %s not found, using empty BREED_GROUPS", BREED_FILE)

# -------------------------------
# Response models (debug endpoint)
# -------------------------------
class ScoreBreakdown(BaseModel):
    age_score: float = Field(..., description="Age similarity score (0..1) used in ranking")
    sterilization_bonus: float = Field(..., description="Fixed bonus if sterilized")
    groups_found: List[str] = Field(default_factory=list, description="Detected breed groups for the pet")
    group_score: float = Field(..., description="Group affinity score (0..1) based on breed group match and rates")
    total_score: float = Field(..., description="Final composite score used for ranking")

class RecommendationDebugItem(BaseModel):
    pet: PetRead
    score_breakdown: ScoreBreakdown

# -------------------------------
# Main recommendation endpoint
# -------------------------------
@router.get(
    "/pets/recommend",
    summary="Recommend pets (ranked list)",
    description="""
### PURPOSE
Return a **ranked list of recommended pets** for a target species and (optionally) a target age.

### USE CASES
- Power “Recommended for you” carousels and shortlist results in client apps  
- Provide counselors with data‑driven suggestions aligned to age or breed group preferences  
- Build marketing modules that feature animals with higher expected suitability  

### INTERPRETATION
- `species` is **required** and case‑insensitive; it is normalized internally to `Dog`, `Cat`, or `Other`  
- `target_age` (months) is **optional**; if omitted, age similarity contributes less (or not at all) depending on implementation  
- For **Dog**, breed group signals are applied using `DOGBREEDS_JSON`; for non‑Dog species, group signals are omitted  
- Results are **ranked** by the recommender’s internal score (highest first)  
- This endpoint returns only the **Pet** data; for score details, use `/pets/recommend-debug`  
""",
    response_model=List[PetRead],
    response_description="Ranked list of pets (highest score first)",
    responses={
        200: {
            "description": "Recommended pets",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 2451,
                            "external_id": "AUS-1005",
                            "species": "Dog",
                            "age_months": 12,
                            "breed_name_raw": "Mixed",
                            "breed_id": None,
                            "sex_upon_outcome": "Neutered Male",
                            "color": "Black/White",
                            "outcome_type": "Adoption",
                            "outcome_datetime": "2026-03-10T11:20:00Z",
                            "shelter_id": 10
                        },
                        {
                            "id": 2442,
                            "external_id": "AUS-0999",
                            "species": "Dog",
                            "age_months": 10,
                            "breed_name_raw": "Labrador Retriever",
                            "breed_id": None,
                            "sex_upon_outcome": None,
                            "color": "Yellow",
                            "outcome_type": None,
                            "outcome_datetime": None,
                            "shelter_id": 11
                        }
                    ]
                }
            },
            "headers": {
                "Cache-Control": {"schema": {"type": "string"}, "description": "e.g., no-store or short TTL"},
            },
        },
        422: {"description": "Validation error (e.g., invalid limit bounds)"},
    },
)
def recommend(
    species: str = Query(
        ...,
        description="Target species (case-insensitive). Typical values: Dog, Cat, Other.",
        examples={"dog": {"summary": "Dog recommendations", "value": "dog"}},
    ),
    target_age: Optional[int] = Query(
        None,
        ge=0,
        description="Target age **in months** (optional).",
        examples={"one-year": {"summary": "Target 12 months", "value": 12}},
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of recommendations to return (1–100).",
        examples={"default": {"summary": "Default limit", "value": 10}, "max": {"summary": "Max", "value": 100}},
    ),
    db: Session = Depends(get_db),
):
    species_norm = normalize_species(species) or "Other"
    breed_groups = BREED_GROUPS if species_norm == "Dog" else {}

    pets = recommend_pets(
        db=db,
        species=species_norm,
        target_age=target_age,
        breed_groups=breed_groups,
        limit=limit,
    )
    return [pet_to_read(p) for p in pets]

# -------------------------------
# Debug endpoint
# -------------------------------
@router.get(
    "/pets/recommend-debug",
    summary="Recommend pets (debug: includes score breakdown)",
    description="""
### PURPOSE
Return **recommendations with detailed scoring diagnostics**, useful for debugging the
recommender, explaining results, and validating data inputs.

### USE CASES
- Inspect how **age similarity**, **sterilization bonus**, and **breed group** signals
  contribute to the final score  
- Validate breed group detection and group rates derived from the dataset  
- Troubleshoot surprising rankings or tie-breaks during development  

### INTERPRETATION
- Output includes the `pet` plus a `score_breakdown` with:  
  - `age_score` (0..1)  
  - `sterilization_bonus` (fixed additive bonus when sterilized)  
  - `groups_found` (detected breed groups for the pet)  
  - `group_score` (0..1)  
  - `total_score` (composite)  
- For **Dog**, breed group features come from `DOGBREEDS_JSON` if present; otherwise they’re omitted  
- Intended for development and troubleshooting; consider hiding in production or gating with auth  
""",
    response_model=List[RecommendationDebugItem],
    response_description="Ranked recommendations with score breakdown",
    responses={
        200: {
            "description": "Recommendations with score explanation",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "pet": {
                                "id": 2451,
                                "external_id": "AUS-1005",
                                "species": "Dog",
                                "age_months": 12,
                                "breed_name_raw": "Mixed",
                                "breed_id": None,
                                "sex_upon_outcome": "Neutered Male",
                                "color": "Black/White",
                                "outcome_type": "Adoption",
                                "outcome_datetime": "2026-03-10T11:20:00Z",
                                "shelter_id": 10
                            },
                            "score_breakdown": {
                                "age_score": 0.92,
                                "sterilization_bonus": 10.0,
                                "groups_found": ["Herding", "Non-Sporting"],
                                "group_score": 0.35,
                                "total_score": 74.5
                            }
                        }
                    ]
                }
            }
        },
        422: {"description": "Validation error (e.g., invalid limit bounds)"},
    },
)
def recommend_debug(
    species: str = Query(
        ...,
        description="Target species (case-insensitive). Typical values: Dog, Cat, Other.",
        examples={"dog": {"summary": "Dog recommendations", "value": "dog"}},
    ),
    target_age: Optional[int] = Query(
        None,
        ge=0,
        description="Target age **in months** (optional).",
        examples={"one-year": {"summary": "Target 12 months", "value": 12}},
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of recommendations to return (1–100).",
        examples={"default": {"summary": "Default limit", "value": 10}, "max": {"summary": "Max", "value": 100}},
    ),
    db: Session = Depends(get_db),
):
    """
    Returns recommended pets along with detailed score breakdown and diagnostics.
    """
    species_norm = normalize_species(species) or "Other"
    breed_groups = BREED_GROUPS if species_norm == "Dog" else {}

    pets = recommend_pets(
        db=db,
        species=species_norm,
        target_age=target_age,
        breed_groups=breed_groups,
        limit=limit,
    )

    group_rates = get_group_rates(db, breed_groups) if breed_groups else {}

    matched_groups = 0
    results = []
    for pet in pets:
        age_score = age_similarity(pet.age_months, target_age)
        sterilization_bonus = 10.0 if is_sterilized(pet.sex_upon_outcome) else 0.0

        # For transparency: show all groups we can find for this pet
        normalized_full = normalize_breed_key(pet.breed_name_raw)
        tokens = split_breed_tokens(pet.breed_name_raw or "")
        found_groups = set()
        for key in [normalized_full] + tokens:
            found_groups.update(breed_groups.get(key, []))

        g = group_score(pet, breed_groups, group_rates)
        if g > 0.0:
            matched_groups += 1

        total_score = 70 * age_score + sterilization_bonus + 30 * g

        results.append({
            "pet": pet_to_read(pet),
            "score_breakdown": {
                "age_score": age_score,
                "sterilization_bonus": sterilization_bonus,
                "groups_found": sorted(found_groups),
                "group_score": g,
                "total_score": total_score,
            }
        })

    logger.debug(
        "recommend-debug: species=%s target_age=%s limit=%d results=%d "
        "breed_groups_len=%d group_rates_len=%d matched_groups=%d breed_groups_empty=%s",
        species_norm, target_age, limit, len(results),
        len(breed_groups), len(group_rates), matched_groups, not bool(breed_groups)
    )

    return results