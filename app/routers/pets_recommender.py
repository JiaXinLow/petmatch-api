from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import json
from pathlib import Path
import logging
import os

from app.database import get_db
from app.schemas import PetRead
from app.services.recommender import (
    recommend_pets,
    compute_score,
    group_score,
    age_similarity,
    is_sterilized,
    get_group_rates
)
from app.utils.pet_helpers import normalize_species, pet_to_read

router = APIRouter(tags=["pets.recommend"])

# -------------------------------
# Logger
# -------------------------------
logger = logging.getLogger("petmatch.pets_recommender")

# -------------------------------
# Correct path to project root
# -------------------------------
BREED_FILE = Path(os.getenv("DOGBREEDS_JSON", "data/raw/dogbreeds.json")).resolve()

BREED_GROUPS = {}
if BREED_FILE.exists():
    try:
        with open(BREED_FILE, "r", encoding="utf-8") as f:
            BREED_GROUPS = json.load(f)
        logger.info("Loaded breed groups from %s", BREED_FILE)
    except json.JSONDecodeError as e:
        logger.warning("Could not parse %s: %s", BREED_FILE, e)
else:
    logger.warning("Breed file %s not found, using empty BREED_GROUPS", BREED_FILE)

# -------------------------------
# Main recommendation endpoint
# -------------------------------
@router.get("/pets/recommend", response_model=List[PetRead])
def recommend(
    species: str = Query(..., description="Target species (Dog|Cat|Other)"),
    target_age: Optional[int] = Query(None, ge=0, description="Target age in months"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # Normalize species
    species_norm = normalize_species(species) or "Other"

    # Apply breed group scoring only for dogs
    breed_groups = BREED_GROUPS if species_norm == "Dog" else {}

    # Get recommended pets
    pets = recommend_pets(
        db=db,
        species=species_norm,
        target_age=target_age,
        breed_groups=breed_groups,
        limit=limit,
    )

    # Convert to read schema
    return [pet_to_read(p) for p in pets]

# -------------------------------
# Debug endpoint showing scoring breakdown
# -------------------------------
@router.get("/pets/recommend-debug")
def recommend_debug(
    species: str = Query(..., description="Target species (Dog|Cat|Other)"),
    target_age: Optional[int] = Query(None, ge=0, description="Target age in months"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Returns recommended pets along with detailed score breakdown:
    - age_score
    - sterilization_score
    - group_score
    - total_score
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

    group_rates = {}  # Fetch group rates for debug calculations
    if breed_groups:
        from app.services.recommender import get_group_rates
        group_rates = get_group_rates(db, breed_groups)

    results = []
    for pet in pets:
        age_score = age_similarity(pet.age_months, target_age)
        sterilization_score = is_sterilized(pet.sex_upon_outcome)
        group_s = group_score(pet, breed_groups, group_rates)
        total_score = (
            70 * age_score + 10 * (10 if sterilization_score else 0) + 30 * group_s
        )

        results.append({
            "pet": pet_to_read(pet),
            "score_breakdown": {
                "age_score": age_score,
                "sterilization_score": sterilization_score,
                "group_score": group_s,
                "total_score": total_score
            }
        })

    return results