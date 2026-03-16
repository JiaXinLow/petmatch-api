from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class PetRow(BaseModel):
    external_id: str
    species: str
    breed_name_raw: Optional[str] = None
    sex_upon_outcome: Optional[str] = None
    age_months: Optional[int] = Field(default=None, ge=0)
    color: Optional[str] = None
    outcome_type: Optional[str] = None
    outcome_datetime: Optional[datetime] = None

    @field_validator("species")
    @classmethod
    def normalize_species(cls, v: str) -> str:
        v = (v or "").strip().title()
        if v in {"Dog", "Cat"}:
            return v
        return "Other"

class BreedRow(BaseModel):
    species: str
    name: str
    group: Optional[str] = None