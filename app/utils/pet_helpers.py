from typing import Optional
from app.models import Pet
from app.schemas import PetRead

def normalize_species(v: Optional[str]) -> Optional[str]:
    if not v:
        return v
    v = v.strip().title()
    if v in {"Dog", "Cat"}:
        return v
    return "Other"

def pet_to_read(p: Pet) -> PetRead:
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