from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.database import get_db
from app.models import Pet
from app.schemas import PetCreate, PetUpdate, PetRead
from app.services.recommender import recommend_pets

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

    total = db.query(func.count(Pet.id)).scalar()

    # Species distribution via GROUP BY
    species_counts = (
        db.query(Pet.species, func.count())
          .group_by(Pet.species)
          .all()
    )
    species_summary = {species: count for species, count in species_counts}

    # Average age
    average_age = db.query(func.avg(Pet.age_months)).scalar()

    return {
        "total_pets": total,
        "species_counts": species_summary,
        "average_age_months": float(average_age) if average_age is not None else None
    }


@router.get("/pets/recommend", response_model=List[PetRead], tags=["pets"])
def recommend(
    species: str = Query(..., description="Target species (Dog|Cat|Other)"),
    size: Optional[str] = Query(
        None, description="Desired breed size (e.g., Small, Medium, Large)"
    ),
    energy: Optional[str] = Query(
        None, description="Desired energy level (e.g., Low, Medium, High)"
    ),
    target_age: Optional[int] = Query(
        None, ge=0, description="Target pet age in months (non-negative)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Max results to return"),
    db: Session = Depends(get_db),
):
    """
    Weighted hybrid recommendations.

    Scoring (high level):
    - Species match: strong weight
    - Size / Energy match: adds weight if provided
    - Age proximity: smooth 1/(1+|Δ|) similarity
    - 'Adoption' outcome: small bonus
    """
    species_norm = _normalize_species(species) or "Other"

    pets = recommend_pets(
        db=db,
        species=species_norm,
        size=size,
        energy=energy,
        target_age=target_age,
        limit=limit,
    )
    return [_pet_to_read(p) for p in pets]


# ---------- Helpers ----------

def _normalize_species(v: Optional[str]) -> Optional[str]:
    if not v:
        return v
    v = v.strip().title()
    if v in {"Dog", "Cat"}:
        return v
    return "Other"


def _pet_to_read(p: Pet) -> PetRead:
    # We construct PetRead explicitly for clarity and future-proofing.
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

@router.post(
    "/pets",
    response_model=PetRead,
    status_code=status.HTTP_201_CREATED,
    # Minimal OpenAPI example so Swagger/PDF looks clean
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "external_id": "AUS-1001",
                        "species": "Dog",
                        "age_months": 12,
                        "breed_name_raw": "Mixed"
                    }
                }
            }
        },
        "responses": {
            "201": {
                "description": "Pet created",
                "content": {
                    "application/json": {
                        "example": {
                            "id": 1,
                            "external_id": "AUS-1001",
                            "species": "Dog",
                            "age_months": 12,
                            "breed_name_raw": "Mixed",
                            "breed_id": None,
                            "sex_upon_outcome": None,
                            "color": None,
                            "outcome_type": None,
                            "outcome_datetime": None,
                            "shelter_id": None
                        }
                    }
                }
            },
            "409": {
                "description": "external_id already exists",
                "content": {
                    "application/json": {
                        "example": {
                            "detail": "Pet with external_id 'AUS-1001' already exists."
                        }
                    }
                }
            }
        }
    }
)
def create_pet(payload: PetCreate, db: Session = Depends(get_db)):
    # Enforce external_id uniqueness to avoid duplicates
    exists = db.execute(
        select(Pet).where(Pet.external_id == payload.external_id)
    ).scalar_one_or_none()
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


@router.patch("/pets/{pet_id}", response_model=PetRead)
def patch_pet(pet_id: int, payload: PetUpdate, db: Session = Depends(get_db)):
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found.")

    updates = payload.model_dump(exclude_none=True)
    if "species" in updates:
        updates["species"] = _normalize_species(updates["species"]) or "Other"

    for field, value in updates.items():
        setattr(pet, field, value)

    db.commit()
    db.refresh(pet)
    return _pet_to_read(pet)


@router.put("/pets/{pet_id}", response_model=PetRead)
def update_pet(pet_id: int, payload: PetUpdate, db: Session = Depends(get_db)):
    """
    Note: In this API, PUT performs a *partial* update (for convenience),
    the same as PATCH. This is documented in the API PDF.
    """
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