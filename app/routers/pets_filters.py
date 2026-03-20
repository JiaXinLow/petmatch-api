from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Pet
from app.schemas import PetRead
from app.utils.pet_helpers import normalize_species, normalize_outcome_type, pet_to_read

router = APIRouter(tags=["pets.browse"])

# --------------------------- SPECIES LIST ------------------------------
@router.get(
    "/pets/species",
    summary="List available species",
    description="""
### PURPOSE
Return a **distinct list of species** present in the dataset.

### USE CASES
- Populate filters (dropdowns) in client UIs for species selection  
- Understand which species are currently represented in the database  
- Drive conditional UI (e.g., breed lists depending on species)  

### INTERPRETATION
- Returns a **sorted**, **unique** list of non-empty species strings  
- Values are the stored/normalized species names (e.g., `Dog`, `Cat`, `Other`)  
- If the dataset is empty or a species has no records, it will not appear  
""",
    response_model=List[str],
    response_description="Distinct, sorted species values",
    responses={
        200: {
            "description": "List of species",
            "content": {
                "application/json": {
                    "example": ["Cat", "Dog", "Other"]
                }
            }
        },
        422: {"description": "Validation error"},
    },
)
def list_species(db: Session = Depends(get_db)):
    rows = db.execute(select(Pet.species).distinct()).scalars().all()
    return sorted([s for s in rows if s])


# ------------------------ OUTCOME TYPES LIST ---------------------------
@router.get(
    "/pets/outcomes",
    summary="List available outcome types",
    description="""
### PURPOSE
Return a **distinct list of outcome types** present in the dataset.

### USE CASES
- Populate filters for browsing by outcome (e.g., `Adoption`, `Transfer`)  
- Drive analytics or dashboards that pivot by outcome type  
- Validate allowable outcome types for user workflows  

### INTERPRETATION
- Returns a **sorted**, **unique** list of non-empty outcome type strings  
- Values reflect what is stored in the database after normalization  
- If no outcomes are recorded yet, the list can be empty  
""",
    response_model=List[str],
    response_description="Distinct, sorted outcome type values",
    responses={
        200: {
            "description": "List of outcome types",
            "content": {
                "application/json": {
                    "example": ["Adoption", "Euthanasia", "Return to Owner", "Transfer"]
                }
            }
        },
        422: {"description": "Validation error"},
    },
)
def list_outcome_types(db: Session = Depends(get_db)):
    rows = db.execute(select(Pet.outcome_type).distinct()).scalars().all()
    return sorted([o for o in rows if o])


# ----------------------------- BREEDS LIST -----------------------------
@router.get(
    "/pets/breeds",
    summary="List available breeds (optionally filtered by species)",
    description="""
### PURPOSE
Return a **distinct list of breed names** observed in the dataset, with an optional
filter by species.

### USE CASES
- Populate a **breed picker** in the UI (optionally species-scoped)  
- Build autocomplete lists for search forms  
- Explore dataset coverage of breeds per species  

### INTERPRETATION
- Returns a **sorted**, **unique** list of non-empty raw breed names (`breed_name_raw`)  
- If `species` is provided, input is **case-insensitive** and normalized internally  
- The list reflects *stored* values; some may be generic (e.g., “Mixed”)  
""",
    response_model=List[str],
    response_description="Distinct, sorted breed names",
    responses={
        200: {
            "description": "List of breeds",
            "content": {
                "application/json": {
                    "examples": {
                        "all-breeds": {
                            "summary": "All breeds (no filter)",
                            "value": ["Mixed", "Domestic Shorthair", "Labrador Retriever"]
                        },
                        "dog-breeds": {
                            "summary": "Filtered by species=Dog",
                            "value": ["Labrador Retriever", "German Shepherd Dog", "Mixed"]
                        }
                    }
                }
            }
        },
        422: {"description": "Validation error"},
    },
)
def list_breeds(
    species: Optional[str] = Query(
        None,
        description="Optional species filter (case-insensitive). Typical values: Dog, Cat, Other.",
        examples={
            "dog": {"summary": "Filter dog breeds", "value": "dog"},
            "cat": {"summary": "Filter cat breeds", "value": "CAT"},
        },
    ),
    db: Session = Depends(get_db),
):
    stmt = select(Pet.breed_name_raw).distinct()
    if species:
        stmt = stmt.where(Pet.species == normalize_species(species))
    rows = db.execute(stmt).scalars().all()
    return sorted([b for b in rows if b])


# ---------------------------- PETS LIST --------------------------------
@router.get(
    "/pets",
    summary="List pets (filterable & paginated)",
    description="""
### PURPOSE
List **pets** with optional filtering by species, outcome type, and age range, with
basic pagination controls via `limit` and `offset`.

### USE CASES
- Build browse pages and search results in client apps  
- Export filtered subsets (e.g., all `Dog` pets adopted in the last period)  
- Power admin dashboards and quick QA checks on data integrity  

### INTERPRETATION
- Filters are **case-insensitive** for `species` and `outcome_type` (normalized internally)  
- `min_age_months` and `max_age_months` filter inclusive ranges  
- Results are ordered by **`id` descending** for stable pagination  
- Returns up to `limit` items, skipping the first `offset` items  
- For large datasets, consider adding total counts or keyset pagination in the future  
""",
    response_model=List[PetRead],
    response_description="List of pets matching the filters (ordered by id desc)",
    responses={
        200: {
            "description": "List of pets",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 2451,
                            "external_id": "AUS-1005",
                            "species": "Dog",
                            "age_months": 12,
                            "breed_name_raw": "Mixed",
                            "breed_id": None,
                            "sex_upon_outcome": "Neutered Male",
                            "color": "Black/White",
                            "outcome_type": "Adoption",
                            "outcome_datetime": "2026-03-10T11:20:00Z",
                            "shelter_id": 10
                        },
                        {
                            "id": 2442,
                            "external_id": "AUS-0999",
                            "species": "Cat",
                            "age_months": 6,
                            "breed_name_raw": "Domestic Shorthair",
                            "breed_id": None,
                            "sex_upon_outcome": None,
                            "color": "Tabby",
                            "outcome_type": None,
                            "outcome_datetime": None,
                            "shelter_id": 11
                        }
                    ]
                }
            },
            "headers": {
                "Cache-Control": {"schema": {"type": "string"}, "description": "e.g., max-age=60"},
            },
        },
        422: {"description": "Validation error"},
    },
)
def list_pets(
    species: Optional[str] = Query(
        None,
        description="Optional species filter (case-insensitive). Typical values: Dog, Cat, Other.",
        examples={
            "dog": {"summary": "Filter dogs", "value": "dog"},
            "other": {"summary": "Filter other species", "value": "OTHER"},
        },
    ),
    outcome_type: Optional[str] = Query(
        None,
        description="Optional outcome filter (case-insensitive). Examples: Adoption, Transfer.",
        examples={
            "adopted": {"summary": "Filter by adoption outcome", "value": "adoption"},
            "transfer": {"summary": "Filter by transfer outcome", "value": "TRANSFER"},
        },
    ),
    min_age_months: Optional[int] = Query(
        None,
        ge=0,
        description="Minimum age (months), inclusive.",
        examples={"min0": {"summary": "No lower bound", "value": None}, "min6": {"summary": "At least 6 months", "value": 6}},
    ),
    max_age_months: Optional[int] = Query(
        None,
        ge=0,
        description="Maximum age (months), inclusive.",
        examples={"maxNone": {"summary": "No upper bound", "value": None}, "max24": {"summary": "At most 24 months", "value": 24}},
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Max number of records to return (1–200). Default 50.",
        examples={"default": {"summary": "Default limit", "value": 50}, "max": {"summary": "Max limit", "value": 200}},
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of records to skip (for pagination).",
        examples={"first": {"summary": "First page", "value": 0}, "second": {"summary": "Second page (50 offset)", "value": 50}},
    ),
    db: Session = Depends(get_db),
):
    filters = []
    if species:
        filters.append(Pet.species == normalize_species(species))
    if outcome_type:
        filters.append(Pet.outcome_type == normalize_outcome_type(outcome_type))
    if min_age_months is not None:
        filters.append(Pet.age_months >= min_age_months)
    if max_age_months is not None:
        filters.append(Pet.age_months <= max_age_months)

    stmt = select(Pet)
    if filters:
        stmt = stmt.where(and_(*filters))

    # ✅ Deterministic ordering so pagination is stable
    stmt = stmt.order_by(Pet.id.desc()).offset(offset).limit(limit)

    rows = db.execute(stmt).scalars().all()
    return [pet_to_read(p) for p in rows]