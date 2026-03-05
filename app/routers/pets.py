from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.database import get_db
from app.models import Pet
from app.schemas import PetCreate, PetUpdate, PetRead

router = APIRouter(tags=["pets"])

# ---------------- Utility & Filtering Endpoints ----------------

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
        stmt = stmt.where(Pet.species == _normalize_species(species))

    rows = db.execute(stmt).scalars().all()
    return sorted([b for b in rows if b])

@router.get("/pets/summary")
def pets_summary(db: Session = Depends(get_db)):

    total = db.query(Pet).count()

    species_rows = db.execute(select(Pet.species)).scalars().all()
    species_summary = {}
    for s in species_rows:
        if s:
            species_summary[s] = species_summary.get(s, 0) + 1

    ages = db.execute(select(Pet.age_months)).scalars().all()
    age_values = [a for a in ages if isinstance(a, int)]

    return {
        "total_pets": total,
        "species_counts": species_summary,
        "average_age_months": (
            sum(age_values) / len(age_values) if age_values else None
        )
    }

# ---------- Helpers ----------

def _normalize_species(v: Optional[str]) -> Optional[str]:
    if not v:
        return v
    v = v.strip().title()
    if v in {"Dog", "Cat"}:
        return v
    return "Other"

def _pet_to_read(p: Pet) -> PetRead:
    # Pydantic orm_mode=True in PetRead lets us return p directly,
    # but building explicitly keeps it clear and future-proof.
    return PetRead(
        id=p.id,
        external_id=p.external_id,
        species=p.species,
        breed_name_raw=p.breed_name_raw,
        breed_id=p.breed_id,
        sex_upon_outcome=p.sex_upon_outcome,
        age_months=p.age_months,
        color=p.color,
        outcome_type=p.outcome_type,
        outcome_datetime=p.outcome_datetime,
        shelter_id=p.shelter_id,
    )

# ---------- CRUD ----------

@router.post("/pets", response_model=PetRead, status_code=status.HTTP_201_CREATED)
def create_pet(payload: PetCreate, db: Session = Depends(get_db)):
    # Optional: enforce external_id uniqueness to avoid duplicates
    exists = db.execute(select(Pet).where(Pet.external_id == payload.external_id)).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pet with external_id '{payload.external_id}' already exists."
        )

    species = _normalize_species(payload.species)

    pet = Pet(
        external_id=payload.external_id.strip(),
        species=species or "Other",
        breed_name_raw=payload.breed_name_raw,
        breed_id=payload.breed_id,
        sex_upon_outcome=payload.sex_upon_outcome,
        age_months=payload.age_months,
        color=payload.color,
        outcome_type=payload.outcome_type,
        outcome_datetime=payload.outcome_datetime,
        shelter_id=payload.shelter_id,
    )
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return _pet_to_read(pet)

@router.get("/pets/{pet_id}", response_model=PetRead)
def get_pet(pet_id: int, db: Session = Depends(get_db)):
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")
    return _pet_to_read(pet)

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
        filters.append(Pet.species == _normalize_species(species))
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
    return [_pet_to_read(p) for p in rows]

@router.put("/pets/{pet_id}", response_model=PetRead)
def update_pet(pet_id: int, payload: PetUpdate, db: Session = Depends(get_db)):
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")

    # Apply updates only if provided
    if payload.species is not None:
        pet.species = _normalize_species(payload.species) or pet.species
    if payload.breed_name_raw is not None:
        pet.breed_name_raw = payload.breed_name_raw
    if payload.breed_id is not None:
        pet.breed_id = payload.breed_id
    if payload.sex_upon_outcome is not None:
        pet.sex_upon_outcome = payload.sex_upon_outcome
    if payload.age_months is not None:
        pet.age_months = payload.age_months
    if payload.color is not None:
        pet.color = payload.color
    if payload.outcome_type is not None:
        pet.outcome_type = payload.outcome_type
    if payload.outcome_datetime is not None:
        pet.outcome_datetime = payload.outcome_datetime
    if payload.shelter_id is not None:
        pet.shelter_id = payload.shelter_id

    db.add(pet)
    db.commit()
    db.refresh(pet)
    return _pet_to_read(pet)

@router.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(pet_id: int, db: Session = Depends(get_db)):
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found."
        )
    db.delete(pet)
    db.commit()
    return None