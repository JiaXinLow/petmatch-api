from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Pet
from app.services.return_risk import _tokenize_color  # reuse helper


# ------------------------------
# Research-backed weights (validated)
# ------------------------------
DEFAULT_WEIGHTS: Dict[str, int] = {
    # Breed groups (Nature 2021)
    "herding": 12,
    "sporting": 10,
    "working": 8,
    "hound": 6,
    "terrier": 4,
    "toy": -4,

    # Breed unknown (Cambridge Animal Welfare)
    "unclassified_breed": 5,

    # Age (Nature 2021 + Cambridge AW)
    "senior": 10,
    "older_adult": 6,
    "puppy": 3,

    # Species "Other" (Nature + BMC Vet Research)
    "species_other": 8,

    # Documentation ambiguity (Cambridge AW)
    "unknown_sex": 4,

    # Dark coat (BMC 2021 minor predictor)
    "dark_coat": 2,
}

DARK_TOKENS = {"black", "dark"}


# ------------------------------
# Breed group loading
# ------------------------------

import json
from pathlib import Path

def load_breed_groups() -> Dict[str, List[str]]:
    """
    Load dogbreeds.json once and cache it.
    Keys = breed name, Value = list of groups.
    """
    path = Path("data/dogbreeds.json")
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

BREED_GROUPS = load_breed_groups()


def infer_breed_groups(breed_name_raw: Optional[str]) -> List[str]:
    """
    Given a raw breed name ("Beagle Mix", "German Shepherd/Akita"),
    try to find all matching breed groups.
    """
    if not breed_name_raw:
        return []

    name = breed_name_raw.lower().strip()

    matches = []
    for key, groups in BREED_GROUPS.items():
        key_l = key.lower()
        if key_l in name:
            matches.extend(groups)

    return matches


# ------------------------------
# Helper functions
# ------------------------------

def is_dark_coat(color: Optional[str]) -> bool:
    tokens = _tokenize_color(color)
    return any(t in DARK_TOKENS for t in tokens)

def clamp100(x: int) -> int:
    return max(0, min(100, x))


# ------------------------------
# Welfare scoring
# ------------------------------

def welfare_for_pet(
    db: Session,
    pet_id: int,
    weights: Dict[str, int] = DEFAULT_WEIGHTS,
) -> Tuple[Optional[Dict], Optional[str]]:
    pet = db.get(Pet, pet_id)
    if not pet:
        return None, "not_found"

    components = []
    score = 0

    # --------------------------
    # Species-based welfare
    # --------------------------
    species = (pet.species or "").title()
    if species not in {"Dog", "Cat"}:
        score += weights["species_other"]
        components.append({"name": "species_other_penalty", "weight": weights["species_other"]})

    # --------------------------
    # Breed group stress rules
    # --------------------------
    groups = infer_breed_groups(pet.breed_name_raw)

    if groups:
        # Assign highest relevant weight
        gmap = {
            "Herding": "herding",
            "Sporting": "sporting",
            "Working": "working",
            "Hound": "hound",
            "Terrier": "terrier",
            "Toy": "toy",
        }
        applied = False
        for g in groups:
            if g in gmap:
                w = weights[gmap[g]]
                score += w
                components.append({"name": f"{g.lower()}_group_weight", "weight": w})
                applied = True
        if not applied:
            # group exists but not mapped above
            score += weights["unclassified_breed"]
            components.append({"name": "unclassified_breed_penalty", "weight": weights["unclassified_breed"]})
    else:
        # No groups → ambiguous breed
        score += weights["unclassified_breed"]
        components.append({"name": "unclassified_breed_penalty", "weight": weights["unclassified_breed"]})

    # --------------------------
    # Age welfare rules
    # --------------------------
    if pet.age_months is not None:
        age = pet.age_months
        if age >= 96:
            score += weights["senior"]
            components.append({"name": "senior_age_penalty", "weight": weights["senior"]})
        elif age >= 60:
            score += weights["older_adult"]
            components.append({"name": "older_adult_penalty", "weight": weights["older_adult"]})
        elif age <= 6:
            score += weights["puppy"]
            components.append({"name": "puppy_penalty", "weight": weights["puppy"]})

    # --------------------------
    # Documentation ambiguity
    # --------------------------
    sex = (pet.sex_upon_outcome or "").strip().lower()
    if not sex or sex == "unknown":
        score += weights["unknown_sex"]
        components.append({"name": "unknown_sex_penalty", "weight": weights["unknown_sex"]})

    # --------------------------
    # Coat visibility (lightweight factor)
    # --------------------------
    if is_dark_coat(pet.color):
        score += weights["dark_coat"]
        components.append({"name": "dark_coat_penalty", "weight": weights["dark_coat"]})

    # --------------------------
    # Build advisory
    # --------------------------
    advisory = []

    if groups and any(g in groups for g in ["Herding", "Sporting"]):
        advisory.append("Increase enrichment activities (Herding/Sporting traits).")

    if pet.age_months is not None and pet.age_months >= 96:
        advisory.append("Provide extra comfort and rest areas for senior animals.")

    if not sex or sex == "unknown":
        advisory.append("Clarify sex/medical details to reduce adopter uncertainty.")

    if is_dark_coat(pet.color):
        advisory.append("Improve lighting or retake photos to improve visibility.")

    # --------------------------
    # Return
    # --------------------------
    return {
        "welfare_score": clamp100(score),
        "components": components,
        "advisory": advisory,
        "explanation": (
            "Heuristic assessment of possible shelter-stress and welfare needs. "
            "This is not a clinical diagnosis. Reasons shown above."
        )
    }, None