from typing import Optional
from app.models import Pet
from app.schemas import PetRead, OutcomeType

_OUTCOME_CANONICAL = {
    "adoption": "Adoption",
    "transfer": "Transfer",
    "return to owner": "Return to Owner",
    "rto-adopt": "Rto-Adopt",
    "euthanasia": "Euthanasia",
    "died": "Died",
    "disposal": "Disposal",
    "lost": "Lost",
    "missing": "Missing",
    "relocate": "Relocate",
    "stolen": "Stolen",
}

def normalize_species(v: Optional[str]) -> Optional[str]:
    if not v:
        return v
    v = v.strip().title()
    if v in {"Dog", "Cat"}:
        return v
    return "Other"

def normalize_outcome_type(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    key = v.strip().lower()
    return _OUTCOME_CANONICAL.get(key) or v.strip()  # fallback to original if unknown

def pet_to_read(p: Pet) -> PetRead:
    # Normalize and convert to OutcomeType enum
    ot_str = normalize_outcome_type(p.outcome_type) if p.outcome_type else None
    ot_enum = OutcomeType(ot_str) if ot_str in OutcomeType.__members__.values() or ot_str in [e.value for e in OutcomeType] else None

    return PetRead(
        id=p.id,
        external_id=p.external_id,
        species=p.species,
        breed_name_raw=p.breed_name_raw,
        breed_id=p.breed_id,
        sex_upon_outcome=p.sex_upon_outcome,
        age_months=p.age_months,
        color=p.color,
        outcome_type=ot_enum,
        outcome_datetime=p.outcome_datetime,
        shelter_id=p.shelter_id,
    )