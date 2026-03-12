from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Pet
from app.schemas import PetRead
from app.utils.pet_helpers import normalize_species, pet_to_read

router = APIRouter(tags=["pets:filters"])

@router.get("/pets/species", response_model=List[str])
def list_species(db: Session = Depends(get_db)):
    rows = db.execute(select(Pet.species).distinct()).scalars().all()
    return sorted([s for s in rows if s])

@router.get("/pets/outcomes", response_model=List[str])
def list_outcome_types(db: Session = Depends(get_db)):
    rows = db.execute(select(Pet.outcome_type).distinct()).scalars().all()
    return sorted([o for o in rows if o])

@router.get("/pets/breeds", response_model=List[str])
def list_breeds(
    species: Optional[str] = Query(None, description="Filter by species (Dog|Cat|Other)"),
    db: Session = Depends(get_db)
):
    stmt = select(Pet.breed_name_raw).distinct()
    if species:
        stmt = stmt.where(Pet.species == normalize_species(species))
    rows = db.execute(stmt).scalars().all()
    return sorted([b for b in rows if b])

@router.get("/pets", response_model=List[PetRead])
def list_pets(
    species: Optional[str] = Query(None, description="Dog|Cat|Other"),
    outcome_type: Optional[str] = Query(None),
    min_age_months: Optional[int] = Query(None, ge=0),
    max_age_months: Optional[int] = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    filters = []
    if species:
        filters.append(Pet.species == normalize_species(species))
    if outcome_type:
        filters.append(Pet.outcome_type == outcome_type)
    if min_age_months is not None:
        filters.append(Pet.age_months >= min_age_months)
    if max_age_months is not None:
        filters.append(Pet.age_months <= max_age_months)

    stmt = select(Pet)
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.offset(offset).limit(limit)

    rows = db.execute(stmt).scalars().all()
    return [pet_to_read(p) for p in rows]