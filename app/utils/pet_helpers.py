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
    # Normalize outcome string
    ot_str = normalize_outcome_type(p.outcome_type) if p.outcome_type else None
    
    # Convert to enum if valid, otherwise fallback to a default (e.g., 'Adoption')
    if ot_str in [e.value for e in OutcomeType]:
        ot_enum = OutcomeType(ot_str)
    else:
        ot_enum = OutcomeType.adoption  # fallback to a safe default

    return PetRead(
        id=p.id,
        external_id=p.external_id,
        species=p.species,
        breed_name_raw=p.breed_name_raw,
        breed_id=getattr(p, "breed_id", None),
        sex_upon_outcome=p.sex_upon_outcome,
        age_months=p.age_months,
        color=getattr(p, "color", None),
        outcome_type=ot_enum,
        outcome_datetime=getattr(p, "outcome_datetime", None),
        shelter_id=getattr(p, "shelter_id", None),
    )