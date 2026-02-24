from pydantic import BaseModel
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
    class Config:
        orm_mode = True


# ----------------- SHELTER -----------------
class ShelterBase(BaseModel):
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "USA"

class ShelterRead(ShelterBase):
    id: int
    class Config:
        orm_mode = True


# ----------------- PET -----------------
class PetBase(BaseModel):
    external_id: str
    species: str
    breed_name_raw: Optional[str] = None
    breed_id: Optional[int] = None
    sex_upon_outcome: Optional[str] = None
    age_months: Optional[int] = None
    color: Optional[str] = None
    outcome_type: Optional[str] = None
    outcome_datetime: Optional[datetime] = None
    shelter_id: Optional[int] = None

class PetCreate(PetBase):
    pass

class PetUpdate(BaseModel):
    species: Optional[str] = None
    breed_name_raw: Optional[str] = None
    breed_id: Optional[int] = None
    sex_upon_outcome: Optional[str] = None
    age_months: Optional[int] = None
    color: Optional[str] = None
    outcome_type: Optional[str] = None
    outcome_datetime: Optional[datetime] = None
    shelter_id: Optional[int] = None

class PetRead(PetBase):
    id: int
    class Config:
        orm_mode = True