from __future__ import annotations

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select
from collections import defaultdict
from datetime import datetime, timedelta
import logging

from app.models import Pet
from app.utils.breed_utils import normalize_breed_key, split_breed_tokens

# ---------------- LOGGER ----------------
logger = logging.getLogger("petmatch.recommender")

# ---------------- WEIGHTS ----------------
DEFAULT_WEIGHTS: Dict[str, float] = {
    "age": 70.0,
    "sterilization": 10.0,
    "group": 30.0,
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

# ---------------- GROUP PRIORS ----------------
# If a breed maps to a group that has no historical outcomes, we can back off to a prior.
# The DEFAULT_GROUP_PRIOR is used only when a group's rate is missing.
DEFAULT_GROUP_PRIOR: float = 0.5

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
    alpha: Optional[float] = None,
    beta: Optional[float] = None,
    prior_strength: int = 50,
) -> Dict[str, float]:
    """
    Computes smoothed success rates per AKC group using historical outcomes.

    - Counts only pets with RESOLVED_OUTCOMES.
    - Only includes pets whose normalized breed key is present in breed_groups.
    - If alpha/beta are None, uses a data-driven prior:
        p0 = global_success / global_total
        alpha = p0 * prior_strength
        beta  = (1 - p0) * prior_strength
      This centers rates around your actual baseline rather than an arbitrary 0.5.
    - Returns: { group_name: smoothed_success_rate, ... }
    """

    group_total: Dict[str, int] = defaultdict(int)
    group_success: Dict[str, int] = defaultdict(int)

    # Global prior components (for auto alpha/beta)
    global_total = 0
    global_success = 0

    matched_breeds = 0
    unmatched_breeds = 0
    considered_pets = 0

    # -------- Pass 1: compute global baseline (for auto-prior) & group counts --------
    for pet in pets:
        if not pet.outcome_type:
            continue

        # Normalize and gate on resolved outcomes first
        outcome_raw = pet.outcome_type.value if hasattr(pet.outcome_type, "value") else pet.outcome_type
        outcome = normalize_outcome(outcome_raw)
        if outcome not in RESOLVED_OUTCOMES:
            continue

        # Update global baseline counts
        global_total += 1
        if outcome in POSITIVE_OUTCOMES:
            global_success += 1

        # For group counts, we also need a breed and matching key
        if not pet.breed_name_raw:
            continue

        considered_pets += 1
        key = normalize_breed_key(pet.breed_name_raw)
        groups = breed_groups.get(key)

        if not groups:
            unmatched_breeds += 1
            continue

        matched_breeds += 1
        for group in groups:
            group_total[group] += 1
            if outcome in POSITIVE_OUTCOMES:
                group_success[group] += 1

    # -------- Determine smoothing parameters (alpha/beta) --------
    used_alpha = alpha
    used_beta = beta
    auto_prior_used = False

    if used_alpha is None or used_beta is None:
        # Data-driven prior centered at the global positive rate
        p0 = (global_success / global_total) if global_total > 0 else 0.5
        used_alpha = p0 * prior_strength
        used_beta = (1.0 - p0) * prior_strength
        auto_prior_used = True
    # Guard against pathological zero
    if used_alpha is None:  # static type safety
        used_alpha = 1.0
    if used_beta is None:
        used_beta = 2.0

    # -------- Compute smoothed rates --------
    group_rates: Dict[str, float] = {}
    for g in group_total:
        success = group_success[g]
        total = group_total[g]
        group_rates[g] = (success + used_alpha) / (total + used_beta)

    # -------- Diagnostics --------
    logger.debug(
        "compute_group_success_rates: considered_pets=%d matched_breeds=%d unmatched_breeds=%d "
        "distinct_groups=%d global_total=%d global_success=%d "
        "alpha=%.4f beta=%.4f prior_strength=%d auto_prior=%s",
        considered_pets, matched_breeds, unmatched_breeds, len(group_rates),
        global_total, global_success, used_alpha, used_beta, prior_strength, auto_prior_used
    )

    # Raw counts per group (success/total) for quick inspection
    if group_total:
        raw_counts = {g: {"success": group_success[g], "total": group_total[g]}
                      for g in sorted(group_total)}
        logger.debug("compute_group_success_rates: group_raw_counts=%s", raw_counts)

    # Pretty-print rates (sorted & rounded) for easy scanning
    if group_rates:
        printable_rates = {g: round(r, 6) for g, r in sorted(group_rates.items())}
        logger.debug("compute_group_success_rates: group_rates=%s", printable_rates)
    else:
        if breed_groups:
            logger.warning(
                "compute_group_success_rates: no group_rates computed but breed_groups is non-empty (len=%d). "
                "Likely no pets matched breed_groups after normalization.",
                len(breed_groups)
            )

    return group_rates

# ---------------- CACHE WRAPPER ----------------
def get_group_rates(db: Session, breed_groups: Dict[str, List[str]]) -> Dict[str, float]:
    """
    Returns (and caches) smoothed group success rates.

    - Recomputes if the cache is empty or expired (TTL).
    - Uses a data-driven prior by default (alpha/beta auto-calculated) for better
      separation than a flat 0.5 prior. To override, pass explicit alpha/beta
      inside compute_group_success_rates.
    - Emits detailed debug logs including the computed rates.
    """
    global _GROUP_RATE_CACHE, _CACHE_LAST_UPDATED

    now = datetime.utcnow()

    # Recompute if cache expired or missing
    if _CACHE_LAST_UPDATED is None or now - _CACHE_LAST_UPDATED > _CACHE_TTL:
        # Pull all pets once; compute rates with auto-prior
        pets = db.execute(select(Pet)).scalars().all()
        _GROUP_RATE_CACHE = compute_group_success_rates(
            pets=pets,
            breed_groups=breed_groups,
            alpha=None,   # auto: compute from global success rate
            beta=None     # auto: compute from global success rate
        )
        _CACHE_LAST_UPDATED = now

        # Summarize rates for logs
        length = len(_GROUP_RATE_CACHE)
        ttl_secs = int(_CACHE_TTL.total_seconds())
        # Show sorted rounded rates to help read logs
        printable = {g: round(r, 6) for g, r in sorted(_GROUP_RATE_CACHE.items())}

        logger.debug(
            "get_group_rates: recomputed rates len=%d (ttl=%ss, breed_groups_len=%d, empty_breed_groups=%s)",
            length, ttl_secs, len(breed_groups), not bool(breed_groups)
        )
        logger.debug("get_group_rates: group_rates=%s", printable)

        if not _GROUP_RATE_CACHE and breed_groups:
            logger.warning(
                "get_group_rates: computed empty rates despite non-empty breed_groups (len=%d). "
                "Check breed/key normalization and data coverage.",
                len(breed_groups)
            )

    return _GROUP_RATE_CACHE

# ---------------- GROUP SCORE ----------------
def group_score(pet: Pet, breed_groups: Dict[str, List[str]], group_rates: Dict[str, float]) -> float:
    """
    Compute a pet's group score by:
      1) Trying the exact normalized full key first
      2) If not found, trying the first matching token from split_breed_tokens
      3) Capping the number of groups used (to avoid dilution)
    """
    if not pet.breed_name_raw:
        return 0.0

    full_key = normalize_breed_key(pet.breed_name_raw)
    groups = breed_groups.get(full_key)

    if not groups:
        # Try a single fallback token (first that yields groups); do not union all tokens
        for token in split_breed_tokens(pet.breed_name_raw):
            if token == full_key:
                continue
            g = breed_groups.get(token)
            if g:
                groups = g
                break

    if not groups:
        return 0.0

    # Optional: avoid diluting by averaging too many groups
    MAX_GROUPS_PER_PET = 2
    groups = groups[:MAX_GROUPS_PER_PET]

    scores = [group_rates.get(g, DEFAULT_GROUP_PRIOR) for g in groups]
    return sum(scores) / len(scores) if scores else 0.0

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
    matched_group_count = 0  # diagnostics: how many pets got a >0 group score
    for pet in pets:
        g = group_score(pet, breed_groups, group_rates)
        if g > 0.0:
            matched_group_count += 1
        s = compute_score(pet, target_age, breed_groups, group_rates)
        scored.append((s, pet))

    scored.sort(key=lambda x: (x[0], x[1].id), reverse=True)
    top = [p for (_, p) in scored[:limit]]

    logger.debug(
        "recommend_pets: species=%s target_age=%s limit=%d total_candidates=%d "
        "breed_groups_len=%d group_rates_len=%d matched_group_count=%d breed_groups_empty=%s",
        species, target_age, limit, len(pets), len(breed_groups), len(group_rates),
        matched_group_count, not bool(breed_groups)
    )

    return top