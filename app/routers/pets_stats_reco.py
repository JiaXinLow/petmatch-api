from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Pet
from app.schemas import PetRead
from app.services.recommender import recommend_pets
from app.utils.pet_helpers import normalize_species, pet_to_read

router = APIRouter(tags=["pets"])

@router.get("/pets/summary")
def pets_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(Pet.id)).scalar()

    species_counts = (
        db.query(Pet.species, func.count())
          .group_by(Pet.species)
          .all()
    )
    species_summary = {species: count for species, count in species_counts}

    average_age = db.query(func.avg(Pet.age_months)).scalar()

    return {
        "total_pets": total,
        "species_counts": species_summary,
        "average_age_months": float(average_age) if average_age is not None else None
    }

@router.get("/pets/recommend", response_model=List[PetRead], tags=["pets"])
def recommend(
    species: str = Query(..., description="Target species (Dog|Cat|Other)"),
    size: Optional[str] = Query(None, description="Desired breed size (e.g., Small, Medium, Large)"),
    energy: Optional[str] = Query(None, description="Desired energy level (e.g., Low, Medium, High)"),
    target_age: Optional[int] = Query(None, ge=0, description="Target pet age in months (non-negative)"),
    limit: int = Query(10, ge=1, le=100, description="Max results to return"),
    db: Session = Depends(get_db),
):
    """
    Weighted hybrid recommendations:
    - Species match (strong weight)
    - Size / Energy match (if provided)
    - Age proximity (1/(1+|Δ|) similarity)
    - 'Adoption' outcome: small bonus
    """
    species_norm = normalize_species(species) or "Other"
    pets = recommend_pets(
        db=db, species=species_norm, size=size, energy=energy, target_age=target_age, limit=limit
    )
    return [pet_to_read(p) for p in pets]