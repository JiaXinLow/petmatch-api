from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import Pet
from app.schemas_errors import ErrorResponse
from app.services.return_risk import return_risk_for_pet
from app.services.welfare import welfare_for_pet

router = APIRouter(tags=["analytics"])

@router.get(
    "/analytics/return-risk/{pet_id}",
    responses={
        200: {
                "description": "Return risk (heuristic) with component reasons.",
                "content": {
                    "application/json": {
                        "example": {
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
                    }
                },
            },
            404: {
                "model": ErrorResponse,
                "description": "Pet not found",
                "content": {
                    "application/json": {
                        "example": {"detail": "Pet not found"}
                    }
                }
            }
        }
)

def get_return_risk(
    pet_id: int,
    window_days: int = Query(180, ge=7, le=3650, description="Cohort window (days) for adoption-rate context"),
    db: Session = Depends(get_db),
) -> Dict:
    result, err = return_risk_for_pet(db, pet_id, window_days=window_days)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Pet not found")
    return {"pet_id": pet_id, **result}


@router.get("/analytics/return-risk/by-external-id/{external_id}")
def get_return_risk_by_external_id(
    external_id: str,
    window_days: int = Query(180, ge=7, le=3650),
    db: Session = Depends(get_db),
) -> Dict:
    pet = db.execute(select(Pet).where(Pet.external_id == external_id)).scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    result, err = return_risk_for_pet(db, pet.id, window_days=window_days)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Pet not found")
    return {"external_id": external_id, "pet_id": pet.id, **result}


@router.get(
    "/analytics/welfare/{pet_id}",
    responses={
            200: {
                "description": "Welfare/behavior heuristic score.",
                "content": {
                    "application/json": {
                        "example": {
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
                },
            },
            404: {
                "model": ErrorResponse,
                "description": "Pet not found",
                "content": {"application/json": {"example": {"detail": "Pet not found"}}}
            }
        }
)

def get_welfare_score(
    pet_id: int,
    db: Session = Depends(get_db),
):
    result, err = welfare_for_pet(db, pet_id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Pet not found")
    return {"pet_id": pet_id, **result}

@router.get(
    "/analytics/welfare/by-external-id/{external_id}",
    responses={
        200: {
                "description": "Welfare/behavior score using external_id lookup.",
                "content": {
                    "application/json": {
                        "example": {
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
            },
            404: {
                "model": ErrorResponse,
                "description": "Pet not found",
                "content": {
                    "application/json": {
                        "example": {"detail": "Pet not found"}
                    }
                }
            }
        }
)
def get_welfare_by_external_id(
    external_id: str,
    db: Session = Depends(get_db),
):
    pet = db.execute(select(Pet).where(Pet.external_id == external_id)).scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    result, err = welfare_for_pet(db, pet.id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Pet not found")

    return {"external_id": external_id, "pet_id": pet.id, **result}