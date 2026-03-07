from pydantic import BaseModel, ConfigDict, NonNegativeInt
from typing import Optional
from datetime import datetime

# ----------------- BREED -----------------
class BreedBase(BaseModel):
    species: str
    name: str
    size: Optional[str] = None
    group: Optional[str] = None
    energy_level: Optional[str] = None

class BreedRead(BreedBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ----------------- SHELTER -----------------
class ShelterBase(BaseModel):
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "USA"

class ShelterRead(ShelterBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ----------------- PET -----------------
class PetBase(BaseModel):
    external_id: str
    species: str
    breed_name_raw: Optional[str] = None
    breed_id: Optional[int] = None
    sex_upon_outcome: Optional[str] = None
    age_months: Optional[NonNegativeInt] = None
    color: Optional[str] = None
    outcome_type: Optional[str] = None
    outcome_datetime: Optional[datetime] = None
    shelter_id: Optional[int] = None

class PetCreate(PetBase):
    # Minimal example to improve Swagger/PDF readability
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "external_id": "AUS-2001",
                "species": "Dog",
                "age_months": 6,
                "breed_name_raw": "Beagle"
            }
        }
    )

class PetUpdate(BaseModel):
    species: Optional[str] = None
    breed_name_raw: Optional[str] = None
    breed_id: Optional[int] = None
    sex_upon_outcome: Optional[str] = None
    age_months: Optional[NonNegativeInt] = None
    color: Optional[str] = None
    outcome_type: Optional[str] = None
    outcome_datetime: Optional[datetime] = None
    shelter_id: Optional[int] = None

class PetRead(PetBase):
    id: int
    model_config = ConfigDict(from_attributes=True)