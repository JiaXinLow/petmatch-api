from pydantic import BaseModel, ConfigDict, NonNegativeInt, validator
from typing import Dict, Optional, List
from datetime import datetime
from pydantic import Field
from enum import Enum

class Species(str, Enum):
    dog = "Dog"
    cat = "Cat"
    other = "Other"

class OutcomeType(str, Enum):
    adoption = "Adoption"
    died = "Died"
    disposal = "Disposal"
    euthanasia = "Euthanasia"
    lost = "Lost"
    missing = "Missing"
    relocate = "Relocate"
    return_to_owner = "Return to Owner"
    rto_adopt = "Rto-Adopt"
    stolen = "Stolen"
    transfer = "Transfer"

# ----------------- BREED -----------------
class BreedBase(BaseModel):
    species: Species
    name: str
    group: Optional[str] = None

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
    external_id: str = Field(..., min_length=1, max_length=50)
    species: Species
    breed_name_raw: Optional[str] = None
    breed_id: Optional[int] = None
    sex_upon_outcome: Optional[str] = None
    age_months: Optional[NonNegativeInt] = None
    color: Optional[str] = None
    outcome_type: Optional[OutcomeType] = None
    outcome_datetime: Optional[datetime] = None
    shelter_id: Optional[int] = None

class PetCreate(PetBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "external_id": "AUS-2001",       # required
                "species": "Dog",                # required (enum)
                "age_months": 6,                 # optional
                "breed_name_raw": "Beagle",      # optional
                "breed_id": 12,                  # optional
                "sex_upon_outcome": "Neutered Male", # optional
                "color": "Brown/White",          # optional
                "outcome_type": "Adoption",      # optional (enum)
                "outcome_datetime": "2026-03-13T10:00:00Z", # optional
                "shelter_id": 5                  # optional
            }
        }
    )

class PetUpdate(BaseModel):
    species: Optional[Species] = None

    @validator("species", pre=True)
    def normalize_species_enum(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
            mapping = {"dog": "Dog", "cat": "Cat", "other": "Other"}
            return mapping.get(v, v)
        return v
    breed_name_raw: Optional[str] = None
    breed_id: Optional[int] = None
    sex_upon_outcome: Optional[str] = None
    age_months: Optional[NonNegativeInt] = None
    color: Optional[str] = None
    outcome_type: Optional[OutcomeType] = None
    outcome_datetime: Optional[datetime] = None
    shelter_id: Optional[int] = None

class PetRead(PetBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ----------------- HEALTH -----------------
class HealthStatus(BaseModel):
    status: str = "ok"

# ----------------- SUMMARY -----------------

class SummaryResponse(BaseModel):
    total_pets: int
    species_counts: Dict[str, int]
    average_age_months: Optional[float] = None


# ----------------- ANALYTICS -----------------
class Component(BaseModel):
    name: str
    weight: int

class ReturnRiskResponse(BaseModel):
    pet_id: int
    risk_score: int
    components: List[Component]
    explanation: str

class ReturnRiskByExternalIdResponse(ReturnRiskResponse):
    external_id: str

class WelfareResponse(BaseModel):
    pet_id: int
    welfare_score: int
    components: List[Component]
    advisory: List[str]
    explanation: str

class WelfareByExternalIdResponse(WelfareResponse):
    external_id: str