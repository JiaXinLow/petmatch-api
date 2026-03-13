from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Pet
from app.schemas import PetCreate, PetUpdate, PetRead
from app.schemas_errors import ErrorResponse
from app.utils.pet_helpers import normalize_species, pet_to_read

router = APIRouter(tags=["pets.manage"])

@router.post(
    "/pets",
    response_model=PetRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
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
        409: {
            "model": ErrorResponse,
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
)

def create_pet(payload: PetCreate, response: Response, db: Session = Depends(get_db)):
    exists = db.execute(select(Pet).where(Pet.external_id == payload.external_id)).scalar_one_or_none()
    if exists:
        raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail={
                                    "message": "Pet already exists",
                                    "external_id": payload.external_id,
                                    "pet_id": exists.id
                                }
                            )
    species = normalize_species(payload.species)
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

    response.headers["Location"] = f"/api/v1/pets/{pet.id}"

    return pet_to_read(pet)

@router.get("/pets/{pet_id}", response_model=PetRead)
def get_pet(pet_id: int, db: Session = Depends(get_db)):
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")
    return pet_to_read(pet)

@router.patch("/pets/{pet_id}", response_model=PetRead)
def patch_pet(pet_id: int, payload: PetUpdate, db: Session = Depends(get_db)):
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found.")

    updates = payload.model_dump(exclude_none=True)
    if "species" in updates:
        updates["species"] = normalize_species(updates["species"]) or "Other"
    for field, value in updates.items():
        setattr(pet, field, value)

    db.commit()
    db.refresh(pet)
    return pet_to_read(pet)

@router.put("/pets/{pet_id}", response_model=PetRead)
def update_pet(pet_id: int, payload: PetUpdate, db: Session = Depends(get_db)):
    """
    Note: In this API, PUT performs a *partial* update (same as PATCH).
    """
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")

    if payload.species is not None:
        pet.species = normalize_species(payload.species) or pet.species
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
    return pet_to_read(pet)

@router.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(pet_id: int, db: Session = Depends(get_db)):
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")
    db.delete(pet)
    db.commit()
    return None