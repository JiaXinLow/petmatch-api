import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("petmatch")

from fastapi import FastAPI

from app.database import engine
from app.models import Base

# Routers
from app.routers.health import router as health_router
from app.routers.pets_crud import router as pets_crud_router
from app.routers.pets_filters import router as pets_filters_router
from app.routers.pets_stats_reco import router as pets_stats_reco_router
from app.routers.analytics import router as analytics_router
from app.routers.pets_recommender import router as pets_recommender_router
from app.routers import admin  # <-- import the admin router module

openapi_tags = [
    {"name": "system", "description": "Root metadata and health check endpoints."},
    {"name": "pets.browse", "description": "Browse pets, species, outcomes, and breeds with optional filters."},
    {"name": "pets.summary", "description": "Dataset-level statistics such as counts and averages."},
    {"name": "pets.recommend", "description": "Content-based recommendation engine for suitable pets."},
    {"name": "pets.manage", "description": "Create, read, update, and delete pet records."},
    {"name": "pets.analytics", "description": "Advanced Return-Risk and Welfare/Stress analytics."}
]

# 1) Create the FastAPI app first
app = FastAPI(title="PetMatch API", version="0.1.0", openapi_tags=openapi_tags)

# 2) Register routers
app.include_router(health_router, prefix="/api")
app.include_router(pets_filters_router, prefix="/api")
app.include_router(pets_stats_reco_router, prefix="/api")
app.include_router(pets_recommender_router, prefix="/api")
app.include_router(pets_crud_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")

# 3) Register the admin router (the one that triggers ETL)
app.include_router(admin.router, prefix="/admin", tags=["admin"])

@app.get("/")
def root():
    return {"name": "PetMatch API", "version": "0.1.0"}

@app.on_event("startup")
def on_startup():
    # Skip DB creation if running tests
    if os.getenv("TESTING") == "1":
        logger.info("TESTING mode detected, skipping DB creation on startup")
        return

    # Ensure data directory exists for SQLite
    os.makedirs("/app/data", exist_ok=True)

    # Create DB tables safely
    Base.metadata.create_all(bind=engine)

    ana = os.getenv("ANALYTICS_API_KEY")
    wrt = os.getenv("WRITE_API_KEY")

    def mask(val: str | None):
        if not val:
            return None
        return f"{val[:2]}*** (len={len(val)})"

    logger.info(
        "PetMatch API starting... ready to serve requests. Analytics key set: %s | Write key set: %s",
        bool(ana), bool(wrt)
    )
    if ana:
        logger.info("Analytics key (masked preview): %s", mask(ana))
    if wrt:
        logger.info("Write key (masked preview): %s", mask(wrt))