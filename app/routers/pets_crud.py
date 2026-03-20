from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response, Path, Body
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Pet
from app.schemas import PetCreate, PetUpdate, PetRead
from app.schemas_errors import ErrorResponse
from app.utils.pet_helpers import normalize_species, pet_to_read
from app.security import require_write_api_key

router = APIRouter(tags=["pets.manage"])

# ------------------------------ CREATE --------------------------------
@router.post(
    "/pets",
    summary="Create a pet record",
    description="""
### PURPOSE
Create a new **pet** resource in the system from client-provided attributes.

### USE CASES
- Ingesting pets from external shelter software or import pipelines  
- Manually adding a record during intake workflows  
- Pre-populating pets to run analytics/recommendations downstream  

### INTERPRETATION
- Returns **201 Created** with the created record  
- Sets **Location** response header to the canonical resource URL  
- Returns **409 Conflict** if a pet with the same `external_id` already exists  
- Write‑protected: requires a valid **X‑API‑Key** for write operations  
""",
    response_model=PetRead,
    response_description="The created pet resource",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Pet created",
            "headers": {
                "Location": {
                    "description": "Canonical URL of the created resource",
                    "schema": {"type": "string"},
                    "example": "/api/pets/1",
                }
            },
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
                        "shelter_id": None,
                    }
                }
            },
        },
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        409: {
            "description": "external_id already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "message": "Pet already exists",
                            "external_id": "AUS-1001",
                            "pet_id": 1,
                        }
                    }
                }
            },
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def create_pet(
    payload: PetCreate = Body(
        ...,
        examples={
            "minimal": {
                "summary": "Minimal dog",
                "value": {
                    "external_id": "AUS-1001",
                    "species": "Dog",
                    "age_months": 12
                }
            },
            "full": {
                "summary": "Full example",
                "value": {
                    "external_id": "AUS-1002",
                    "species": "Cat",
                    "age_months": 36,
                    "breed_name_raw": "Domestic Shorthair",
                    "breed_id": None,
                    "sex_upon_outcome": "Neutered Male",
                    "color": "Black/White",
                    "outcome_type": None,
                    "outcome_datetime": None,
                    "shelter_id": 10
                }
            }
        }
    ),
    response: Response = None,
    db: Session = Depends(get_db),
    _auth: None = Depends(require_write_api_key),
):
    exists = db.execute(select(Pet).where(Pet.external_id == payload.external_id)).scalar_one_or_none()
    if exists:
        # Structured detail (dict) to match tests
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Pet already exists",
                "external_id": payload.external_id,
                "pet_id": exists.id,
            },
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

    # NOTE: Router is mounted with prefix="/api" → /api/pets/{id}
    if response is not None:
        response.headers["Location"] = f"/api/pets/{pet.id}"

    return pet_to_read(pet)


# ------------------------------- READ ---------------------------------
@router.get(
    "/pets/{pet_id}",
    summary="Fetch a pet by ID",
    description="""
### PURPOSE
Retrieve a **single pet** by its internal identifier.

### USE CASES
- Display pet details in admin UI or client app views  
- Pull a record for edit, export, or auditing  
- Validate the existence of a pet before invoking analytics or recommendations  

### INTERPRETATION
- Returns **200 OK** with the current persisted representation  
- Returns **404 Not Found** if the pet does not exist  
- Safe and cacheable; consider setting `Cache-Control`/`ETag` headers upstream  
""",
    response_model=PetRead,
    response_description="The requested pet",
    responses={
        200: {
            "description": "Pet found",
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
            },
            "headers": {
                "Cache-Control": {"schema": {"type": "string"}, "description": "e.g., max-age=60"},
                "ETag": {"schema": {"type": "string"}, "description": "Entity tag for conditional GETs"},
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "Pet not found",
            "content": {"application/json": {"example": {"detail": "Pet not found."}}},
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def get_pet(
    pet_id: int = Path(..., description="Internal Pet ID", examples={"example": {"summary": "Example ID", "value": 1}}),
    db: Session = Depends(get_db),
):
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")
    return pet_to_read(pet)


# ------------------------------ UPDATE --------------------------------
@router.patch(
    "/pets/{pet_id}",
    summary="Partially update a pet (PATCH)",
    description="""
### PURPOSE
Apply a **partial update** to a pet’s attributes.

### USE CASES
- Correcting or enriching records over time (e.g., `sex_upon_outcome`, `breed_name_raw`)  
- Updating `outcome_type` and `outcome_datetime` when outcomes occur  
- Normalizing inconsistent species or color inputs  

### INTERPRETATION
- Returns **200 OK** with the updated resource  
- Returns **404 Not Found** if the pet does not exist  
- Write‑protected: requires a valid **X‑API‑Key** for write operations  
- Only fields provided in the request body are updated; others remain unchanged  
""",
    response_model=PetRead,
    response_description="The updated pet resource",
    responses={
        200: {
            "description": "Pet updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "external_id": "AUS-1001",
                        "species": "Dog",
                        "age_months": 13,
                        "breed_name_raw": "Mixed",
                        "breed_id": None,
                        "sex_upon_outcome": "Neutered Male",
                        "color": "Black",
                        "outcome_type": None,
                        "outcome_datetime": None,
                        "shelter_id": None
                    }
                }
            }
        },
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        404: {
            "model": ErrorResponse,
            "description": "Pet not found",
            "content": {"application/json": {"example": {"detail": "Pet not found."}}},
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def patch_pet(
    pet_id: int = Path(..., description="Internal Pet ID", examples={"example": {"summary": "Example ID", "value": 1}}),
    payload: PetUpdate = Body(
        ...,
        examples={
            "update-age-and-sex": {
                "summary": "Update age and sex",
                "value": {"age_months": 13, "sex_upon_outcome": "Neutered Male"}
            },
            "set-outcome": {
                "summary": "Set adoption outcome",
                "value": {"outcome_type": "Adoption", "outcome_datetime": "2026-03-15T10:30:00Z"}
            }
        }
    ),
    db: Session = Depends(get_db),
    _auth: None = Depends(require_write_api_key),
):
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


# ------------------------------ DELETE --------------------------------
@router.delete(
    "/pets/{pet_id}",
    summary="Delete a pet",
    description="""
### PURPOSE
Remove the specified **pet** resource by ID.

### USE CASES
- Cleaning up erroneous or duplicate records  
- Complying with data retention or takedown policies  
- Removing test data from demo or staging environments  

### INTERPRETATION
- Returns **204 No Content** on success (no response body)  
- Returns **404 Not Found** if the pet does not exist  
- Write‑protected: requires a valid **X‑API‑Key** for write operations  
""",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Pet deleted (no content)"},
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        404: {
            "model": ErrorResponse,
            "description": "Pet not found",
            "content": {"application/json": {"example": {"detail": "Pet not found."}}},
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def delete_pet(
    pet_id: int = Path(..., description="Internal Pet ID", examples={"example": {"summary": "Example ID", "value": 1}}),
    db: Session = Depends(get_db),
    _auth: None = Depends(require_write_api_key),
):
    pet = db.get(Pet, pet_id)
    if not pet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found.")
    db.delete(pet)
    db.commit()
    return None