from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Pet, Breed

# Default weights (configurable)
DEFAULT_WEIGHTS = {
    "species": 40,
    "size": 25,
    "energy": 25,
    "age": 15,
    "adoptable": 10,
}

def age_similarity(pet_age: Optional[int], target_age: Optional[int]) -> float:
    if pet_age is None or target_age is None:
        return 0.0
    diff = abs(pet_age - target_age)
    return 1 / (1 + diff)

def compute_score(
    pet: Pet,
    breed: Optional[Breed],
    user_species: str,
    user_size: Optional[str],
    user_energy: Optional[str],
    target_age: Optional[int],
    w=DEFAULT_WEIGHTS
) -> float:

    score = 0.0

    # 1) Species match
    if pet.species == user_species:
        score += w["species"]

    # 2) Breed characteristics
    if breed:
        if user_size and breed.size == user_size:
            score += w["size"]
        if user_energy and breed.energy_level == user_energy:
            score += w["energy"]

    # 3) Age match
    score += w["age"] * age_similarity(pet.age_months, target_age)

    # 4) Adoptable bonus
    if pet.outcome_type and pet.outcome_type.lower() == "adoption":
        score += w["adoptable"]

    return score


def recommend_pets(
    db: Session,
    species: str,
    size: Optional[str],
    energy: Optional[str],
    target_age: Optional[int],
    limit: int = 10
) -> List[Pet]:

    stmt = select(Pet).where(Pet.species == species)
    pets = db.execute(stmt).scalars().all()

    # Preload breeds
    breeds = {b.id: b for b in db.execute(select(Breed)).scalars().all()}

    scored = []
    for pet in pets:
        breed = breeds.get(pet.breed_id)
        s = compute_score(
            pet,
            breed,
            user_species=species,
            user_size=size,
            user_energy=energy,
            target_age=target_age
        )
        scored.append((s, pet))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for (_, p) in scored[:limit]]