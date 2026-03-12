from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Pet
from app.schemas import PetRead
from app.services.recommender import recommend_pets
from app.utils.pet_helpers import normalize_species, pet_to_read

router = APIRouter(tags=["pets:stats"])

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