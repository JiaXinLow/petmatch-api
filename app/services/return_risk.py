from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Pet

DEFAULT_WEIGHTS: Dict[str, int] = {
    "species_other": 12,
    "unknown_sex": 8,
    "dark_coat": 5,
    "mix_unclassified": 4,
    "low_cohort_adoption": 6,
}

DARK_TOKENS = {"black", "dark"}

def _normalize_species(v: Optional[str]) -> Optional[str]:
    if not v:
        return v
    v = v.strip().title()
    if v in {"Dog", "Cat"}:
        return v
    return "Other"

def _tokenize_color(color: Optional[str]) -> List[str]:
    if not color:
        return []
    s = color.replace("-", "/")
    return [t.strip().lower() for t in s.split("/") if t.strip()]

def is_dark_coat(color: Optional[str]) -> bool:
    tokens = _tokenize_color(color)
    return any(t in DARK_TOKENS for t in tokens)

def _cohort_adoption_rate(
    db: Session, species: str, window_days: int
) -> float:
    """Return adoptions / total for this species within the time window.
    If no timestamps exist, we fall back to all-time counts (so we never divide by zero)."""
    since = datetime.utcnow() - timedelta(days=window_days)

    # Prefer time-bounded counts when outcome_datetime is present; fallback otherwise.
    total_q = db.query(func.count(Pet.id)).filter(Pet.species == species)
    adpt_q  = db.query(func.count(Pet.id)).filter(
        Pet.species == species, Pet.outcome_type == "Adoption"
    )

    # If we have any timestamps in DB, apply the window filter.
    any_ts = db.query(func.count(Pet.id)).filter(Pet.outcome_datetime.isnot(None)).scalar() or 0
    if any_ts:
        total_q = total_q.filter(Pet.outcome_datetime >= since)
        adpt_q  = adpt_q.filter(Pet.outcome_datetime >= since)

    total = total_q.scalar() or 0
    adpt  = adpt_q.scalar() or 0
    return (adpt / total) if total > 0 else 0.0

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def clamp100(x: int) -> int:
    return max(0, min(100, x))

def return_risk_for_pet(
    db: Session,
    pet_id: int,
    window_days: int = 180,
    weights: Dict[str, int] = DEFAULT_WEIGHTS,
) -> Tuple[Optional[Dict], Optional[str]]:
    """Compute a transparent, heuristic 'return risk' for post-adoption.
    Returns (result_dict, error) where error is 'not_found' if pet missing."""
    pet = db.get(Pet, pet_id)
    if not pet:
        return None, "not_found"

    components: List[Dict[str, int]] = []
    score = 0

    species = _normalize_species(pet.species) or "Other"

    if species not in {"Dog", "Cat"}:
        score += weights["species_other"]
        components.append({"name": "species_other_penalty", "weight": weights["species_other"]})

    if not pet.sex_upon_outcome or pet.sex_upon_outcome.strip().lower() == "unknown":
        score += weights["unknown_sex"]
        components.append({"name": "unknown_sex_penalty", "weight": weights["unknown_sex"]})

    if is_dark_coat(pet.color):
        score += weights["dark_coat"]
        components.append({"name": "dark_coat_penalty", "weight": weights["dark_coat"]})

    if (pet.breed_id is None) and (pet.breed_name_raw and "mix" in pet.breed_name_raw.lower()):
        score += weights["mix_unclassified"]
        components.append({"name": "mixed_breed_unclassified_penalty", "weight": weights["mix_unclassified"]})

    rate = _cohort_adoption_rate(db, species, window_days)
    if rate < 0.30:
        score += weights["low_cohort_adoption"]
        components.append({"name": "low_cohort_adoption_rate_penalty", "weight": weights["low_cohort_adoption"]})

    result = {
        "risk_score": clamp100(score),
        "components": components,
        "explanation": (
            "Heuristic risk score for potential post-adoption returns. "
            "Use for operational prioritization (transparent reasons attached); "
            "not a label of the animal’s worth."
        ),
    }
    return result, None