from fastapi import APIRouter
from app.schemas import HealthStatus

router = APIRouter(tags=["system"])

@router.get("/health", response_model=HealthStatus)
def health():
    return {"status": "ok"}