from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select
from collections import defaultdict
from datetime import datetime, timedelta
from app.models import Pet

# ---------------- WEIGHTS ----------------
DEFAULT_WEIGHTS: Dict[str, float] = {
    "age": 70.0,
    "sterilization": 10.0,
    "group": 30.0
}

# ---------------- OUTCOME NORMALIZATION ----------------
OUTCOME_MAPPING = {
    "Adoption": "Adopted",
    "Return to Owner": "Returned",
    "Rto-Adopt": "Adopted",
    "Transfer": "Transferred",
    "Relocate": "Relocated",
    "Euthanasia": "Euthanized",
    "Died": "Died",
    "Disposal": "Disposed",
    "Lost": "Lost",
    "Missing": "Missing",
    "Stolen": "Stolen",
}

RESOLVED_OUTCOMES = {"Adopted", "Euthanized", "Returned", "Transferred", "Relocated", "Died", "Disposed"}
POSITIVE_OUTCOMES = {"Adopted"}

def normalize_outcome(outcome: Optional[str]) -> str:
    if not outcome:
        return ""
    return OUTCOME_MAPPING.get(outcome, outcome)

# ---------------- CACHE ----------------
_GROUP_RATE_CACHE: Dict[str, float] = {}
_CACHE_LAST_UPDATED: Optional[datetime] = None
_CACHE_TTL = timedelta(minutes=30)   # recompute every 30 minutes

# ---------------- AGE SIMILARITY ----------------
def age_similarity(pet_age: Optional[int], target_age: Optional[int]) -> float:
    if pet_age is None or target_age is None:
        return 0.0
    diff = abs(pet_age - target_age)
    return 1.0 / (1.0 + float(diff))

# ---------------- STERILIZATION ----------------
def is_sterilized(sex_upon_outcome: Optional[str]) -> bool:
    if not sex_upon_outcome:
        return False
    s = sex_upon_outcome.lower()
    return ("neutered" in s) or ("spayed" in s)

# ---------------- GROUP SUCCESS RATES ----------------
def compute_group_success_rates(
    pets: List[Pet],
    breed_groups: Dict[str, List[str]],
    alpha: float = 1.0,
    beta: float = 2.0
) -> Dict[str, float]:

    group_total = defaultdict(int)
    group_success = defaultdict(int)

    for pet in pets:
        if not pet.breed_name_raw or not pet.outcome_type:
            continue

        # Normalize outcome
        outcome = normalize_outcome(pet.outcome_type.value if hasattr(pet.outcome_type, "value") else pet.outcome_type)
        if outcome not in RESOLVED_OUTCOMES:
            continue

        groups = breed_groups.get(pet.breed_name_raw)
        if not groups:
            continue

        for group in groups:
            group_total[group] += 1
            if outcome in POSITIVE_OUTCOMES:
                group_success[group] += 1

    group_rates = {}
    for g in group_total:
        success = group_success[g]
        total = group_total[g]
        group_rates[g] = (success + alpha) / (total + beta)

    return group_rates

# ---------------- CACHE WRAPPER ----------------
def get_group_rates(db: Session, breed_groups: Dict[str, List[str]]) -> Dict[str, float]:
    global _GROUP_RATE_CACHE, _CACHE_LAST_UPDATED

    now = datetime.utcnow()
    if _CACHE_LAST_UPDATED is None or now - _CACHE_LAST_UPDATED > _CACHE_TTL:
        pets = db.execute(select(Pet)).scalars().all()
        _GROUP_RATE_CACHE = compute_group_success_rates(pets, breed_groups)
        _CACHE_LAST_UPDATED = now

    return _GROUP_RATE_CACHE

# ---------------- GROUP SCORE ----------------
def group_score(pet: Pet, breed_groups: Dict[str, List[str]], group_rates: Dict[str, float]) -> float:
    if not pet.breed_name_raw:
        return 0.0
    groups = breed_groups.get(pet.breed_name_raw)
    if not groups:
        return 0.0
    scores = [group_rates.get(g, 0.0) for g in groups]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)

# ---------------- FINAL SCORING ----------------
def compute_score(
    pet: Pet,
    target_age: Optional[int],
    breed_groups: Dict[str, List[str]],
    group_rates: Dict[str, float],
    w: Dict[str, float] = DEFAULT_WEIGHTS
) -> float:

    score = 0.0
    score += w["age"] * age_similarity(pet.age_months, target_age)
    if is_sterilized(pet.sex_upon_outcome):
        score += w["sterilization"]
    score += w["group"] * group_score(pet, breed_groups, group_rates)
    return score

# ---------------- MAIN RECOMMENDER ----------------
def recommend_pets(
    db: Session,
    species: str,
    target_age: Optional[int],
    breed_groups: Dict[str, List[str]],
    limit: int = 10
) -> List[Pet]:

    pets = db.execute(select(Pet).where(Pet.species == species)).scalars().all()
    group_rates = get_group_rates(db, breed_groups)

    scored = []
    for pet in pets:
        s = compute_score(pet, target_age, breed_groups, group_rates)
        scored.append((s, pet))

    scored.sort(key=lambda x: (x[0], x[1].id), reverse=True)
    return [p for (_, p) in scored[:limit]]