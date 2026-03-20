from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.params import Security
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Pet
from app.schemas_errors import ErrorResponse
from app.security import require_analytics_api_key
from app.services.return_risk import return_risk_for_pet
from app.services.welfare import welfare_for_pet

# --------- Pydantic response models (strongly-typed OpenAPI) ---------
class Component(BaseModel):
    name: str = Field(..., description="Feature or rule contributing to the score")
    weight: int = Field(..., description="Positive for risk/weight increase; negative for decrease")

class ReturnRiskResponse(BaseModel):
    pet_id: int = Field(..., description="Internal ID of the pet")
    external_id: Optional[str] = Field(None, description="External ID if looked-up by external reference")
    risk_score: int = Field(..., ge=0, le=100, description="Heuristic return-risk score (0–100)")
    components: List[Component] = Field(..., description="Breakdown of contributing components")
    explanation: Optional[str] = Field(None, description="Human-readable summary of the score rationale")

class WelfareResponse(BaseModel):
    pet_id: int = Field(..., description="Internal ID of the pet")
    external_id: Optional[str] = Field(None, description="External ID if looked-up by external reference")
    welfare_score: int = Field(..., ge=0, le=100, description="Heuristic welfare/behavior score (0–100)")
    components: List[Component] = Field(..., description="Breakdown of contributing components")
    advisory: List[str] = Field(default_factory=list, description="Actionable suggestions")
    explanation: Optional[str] = Field(None, description="Human-readable summary of the score rationale")

router = APIRouter(
    tags=["pets.analytics"],  # Matches openapi_tags in app.main
    dependencies=[Security(require_analytics_api_key)],  # Swagger will now send X-API-Key
)

# ----------------------- Return Risk (by pet_id) -----------------------
@router.get(
    "/analytics/return-risk/{pet_id}",
    summary="Return risk (heuristic) with component reasons",
    description="""
### PURPOSE
Compute an estimated **return‑risk score** for a pet using its **internal ID**.  
The score is derived from heuristic components such as breed group, coat color,
cohort adoption trends, and demographic features.

### USE CASES
- Intake teams triaging pets needing extra medical, behavioral, or marketing attention  
- Identifying cohorts historically prone to higher return probability  
- Supporting adoption counseling and post‑adoption follow-up  
- Surfacing “hidden risk factors” not obvious from raw intake notes  

### INTERPRETATION
- Score ranges from **0–100** (higher = higher estimated return risk)  
- Components show how each factor influenced the score  
  - **Positive weight** → increases risk  
  - **Negative weight** → decreases risk  
- `window_days` supplies cohort adoption‑rate context for recent outcomes  
- Heuristic model — use it to **augment** professional judgment, not replace it  
""",
    response_model=ReturnRiskResponse,
    response_description="Return-risk score and component breakdown",
    status_code=200,
    responses={
        200: {
            "description": "Return risk (heuristic) with component reasons.",
            "content": {
                "application/json": {
                    "examples": {
                        "typical": {
                            "summary": "Typical dog with some penalties",
                            "value": {
                                "pet_id": 118,
                                "risk_score": 68,
                                "components": [
                                    {"name": "species_other_penalty", "weight": 12},
                                    {"name": "unknown_sex_penalty", "weight": 8},
                                    {"name": "dark_coat_penalty", "weight": 5},
                                    {"name": "mixed_breed_unclassified_penalty", "weight": 4},
                                    {"name": "low_cohort_adoption_rate_penalty", "weight": 6}
                                ],
                                "explanation": "Other-species and unknown sex increase risk; dark coat may reduce photo contrast. Recent cohort adoption rate is low."
                            }
                        },
                        "low-risk": {
                            "summary": "Low risk example",
                            "value": {
                                "pet_id": 42,
                                "risk_score": 15,
                                "components": [
                                    {"name": "puppy_bonus", "weight": -10},
                                    {"name": "high_cohort_adoption_rate_bonus", "weight": -5}
                                ],
                                "explanation": "Young age and strong cohort adoption rates reduce risk."
                            }
                        }
                    }
                }
            },
            "headers": {
                "Cache-Control": {"schema": {"type": "string"}, "description": "e.g., max-age=300"},
                "X-RateLimit-Remaining": {"schema": {"type": "integer"}, "description": "Requests remaining in this window"},
            },
        },
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        404: {
            "model": ErrorResponse,
            "description": "Pet not found",
            "content": {"application/json": {"example": {"detail": "Pet not found"}}},
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def get_return_risk(
    pet_id: int = Path(..., description="Internal Pet ID", examples={"example": {"summary": "Example ID", "value": 118}}),
    window_days: int = Query(
        180,
        ge=7,
        le=3650,
        description="Cohort window (days) for adoption-rate context",
        examples={
            "default": {"summary": "Default", "value": 180},
            "short": {"summary": "Short window", "value": 30},
            "long": {"summary": "Long window", "value": 365},
        },
    ),
    db: Session = Depends(get_db),
) -> ReturnRiskResponse:
    result, err = return_risk_for_pet(db, pet_id, window_days=window_days)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Pet not found")
    return ReturnRiskResponse(pet_id=pet_id, **result)


# -------------------- Return Risk (by external_id) ---------------------
@router.get(
    "/analytics/return-risk/by-external-id/{external_id}",
    summary="Return risk (by external_id lookup)",
    description="""
### PURPOSE
Compute the same **return‑risk score** as the `pet_id` version, but using an **external ID**
(e.g., PetPoint, ShelterLuv, or custom intake systems).

### USE CASES
- Integrate analytics with external shelter software pipelines  
- Let clients query analytics without knowing the internal database ID  
- Run bulk analytics on datasets keyed by external identifiers  

### INTERPRETATION
- Output mirrors the `pet_id` endpoint (score, components, explanation)  
- Includes both the provided **external_id** and the resolved **pet_id** for traceability  
- Returns **404** if the external_id does not map to a known pet  
- `window_days` behaves identically to the `pet_id` endpoint  
""",
    response_model=ReturnRiskResponse,
    response_description="Return-risk score and component breakdown",
    status_code=200,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        404: {
            "model": ErrorResponse,
            "description": "Pet not found",
            "content": {"application/json": {"example": {"detail": "Pet not found"}}},
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def get_return_risk_by_external_id(
    external_id: str = Path(..., description="External system ID of the pet"),
    window_days: int = Query(180, ge=7, le=3650, description="Cohort window (days) for adoption-rate context"),
    db: Session = Depends(get_db),
) -> ReturnRiskResponse:
    pet = db.execute(select(Pet).where(Pet.external_id == external_id)).scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    result, err = return_risk_for_pet(db, pet.id, window_days=window_days)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Pet not found")
    return ReturnRiskResponse(pet_id=pet.id, external_id=external_id, **result)


# -------------------------- Welfare (by pet_id) ------------------------
@router.get(
    "/analytics/welfare/{pet_id}",
    summary="Welfare/behavior heuristic score",
    description="""
### PURPOSE
Generate a **welfare/behavior heuristic score** for a pet using its **internal ID**, based on
features such as age, breed traits, coat color, and other indicators of stress or enrichment needs.

### USE CASES
- Behavior teams identifying pets needing enrichment, decompression, or special housing  
- Monitoring welfare changes over time by evaluating scores periodically  
- Prioritizing kennel enrichment resources or volunteer attention  
- Highlighting animals at higher risk for stress-related behavior changes  

### INTERPRETATION
- Score ranges from **0–100** (higher = potentially higher welfare concern)  
- Components indicate which traits contributed to the score  
- **Advisory** messages provide actionable suggestions to improve welfare  
- Heuristic tool — intended to **augment** behaviorist evaluation, not replace it  
""",
    response_model=WelfareResponse,
    response_description="Welfare score and advisory recommendations",
    status_code=200,
    responses={
        200: {
            "description": "Welfare/behavior heuristic score.",
            "content": {
                "application/json": {
                    "examples": {
                        "typical": {
                            "summary": "Typical welfare example",
                            "value": {
                                "pet_id": 201,
                                "welfare_score": 62,
                                "components": [
                                    {"name": "herding_group_weight", "weight": 12},
                                    {"name": "senior_age_penalty", "weight": 10}
                                ],
                                "advisory": [
                                    "Increase enrichment activities (Herding/Sporting traits).",
                                    "Provide extra comfort and rest areas for senior animals."
                                ],
                                "explanation": "Heuristic assessment of possible shelter-stress and welfare needs."
                            }
                        }
                    }
                }
            },
        },
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        404: {
            "model": ErrorResponse,
            "description": "Pet not found",
            "content": {"application/json": {"example": {"detail": "Pet not found"}}},
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def get_welfare_score(
    pet_id: int = Path(..., description="Internal Pet ID"),
    db: Session = Depends(get_db),
) -> WelfareResponse:
    result, err = welfare_for_pet(db, pet_id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Pet not found")
    return WelfareResponse(pet_id=pet_id, **result)


# ------------------- Welfare (by external_id) --------------------------
@router.get(
    "/analytics/welfare/by-external-id/{external_id}",
    summary="Welfare/behavior score via external_id lookup",
    description="""
### PURPOSE
Provide the same **welfare/behavior heuristic assessment** as the `pet_id` endpoint,
but accessible via an **external ID** instead of the internal database ID.

### USE CASES
- Integrating welfare analytics into external shelter‑management systems  
- Running welfare assessments on pets using third‑party intake identifiers  
- Automating welfare triage workflows based on external event streams  

### INTERPRETATION
- Results mirror the `pet_id` endpoint (score, components, advisory)  
- Includes both the provided **external_id** and the resolved **pet_id**  
- Returns **404** if the external_id does not correspond to any known pet  
""",
    response_model=WelfareResponse,
    response_description="Welfare score and advisory recommendations",
    status_code=200,
    responses={
        200: {
            "description": "Welfare/behavior score using external_id lookup.",
            "content": {
                "application/json": {
                    "examples": {
                        "senior-dark-coat": {
                            "summary": "Senior with dark coat",
                            "value": {
                                "external_id": "WFTEST-1",
                                "pet_id": 201,
                                "welfare_score": 62,
                                "components": [
                                    {"name": "senior_age_penalty", "weight": 10},
                                    {"name": "dark_coat_penalty", "weight": 2}
                                ],
                                "advisory": [
                                    "Provide extra comfort and rest areas for senior animals.",
                                    "Improve lighting or retake photos to improve visibility."
                                ],
                                "explanation": "Heuristic assessment of possible shelter-stress and welfare needs."
                            }
                        }
                    }
                }
            },
        },
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        404: {
            "model": ErrorResponse,
            "description": "Pet not found",
            "content": {"application/json": {"example": {"detail": "Pet not found"}}},
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
def get_welfare_by_external_id(
    external_id: str = Path(..., description="External system ID of the pet"),
    db: Session = Depends(get_db),
) -> WelfareResponse:
    pet = db.execute(select(Pet).where(Pet.external_id == external_id)).scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    result, err = welfare_for_pet(db, pet.id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Pet not found")

    return WelfareResponse(pet_id=pet.id, external_id=external_id, **result)