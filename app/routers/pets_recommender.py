from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import json
from pathlib import Path
import logging

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
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BREED_FILE = PROJECT_ROOT / "data" / "dogbreed.json"

# -------------------------------
# Load BREED_GROUPS safely
# -------------------------------
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
    target_age: Optional[int] = Query(None, ge=0, description="Target age (Months)"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # Normalize species
    species_norm = normalize_species(species) or "Other"
    breed_groups = BREED_GROUPS if species_norm == "Dog" else {}

    # Get recommended pets
    pets = recommend_pets(
        db=db,
        species=species_norm,
        target_age=target_age,
        breed_groups=breed_groups,
        limit=limit,
    )

    # Get group rates once for scoring
    group_rates = get_group_rates(db, BREED_GROUPS)

    debug_list = []
    for pet in pets:
        # Compute component scores
        age_score = age_similarity(pet.age_months, target_age)
        sterilization_score = is_sterilized(pet.sex_upon_outcome)
        group_score_val = group_score(pet, breed_groups, group_rates)
        total_score = compute_score(pet, target_age, breed_groups, group_rates)

        debug_list.append({
            "pet": pet_to_read(pet),
            "score_breakdown": {
                "age_score": age_score,
                "sterilization_score": sterilization_score,
                "group_score": group_score_val,
                "total_score": total_score
            }
        })

    return debug_list