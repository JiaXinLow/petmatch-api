from fastapi import APIRouter
from app.schemas import HealthStatus

router = APIRouter()

@router.get("/health", response_model=HealthStatus)
def health():
    return {"status": "ok"}