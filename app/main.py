import logging
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("petmatch")
logging.getLogger("petmatch.recommender").setLevel(logging.DEBUG)
logging.getLogger("petmatch.pets_recommender").setLevel(logging.DEBUG)

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.database import engine
from app.models import Base

# Routers
from app.routers.health import router as health_router
from app.routers.pets_crud import router as pets_crud_router
from app.routers.pets_filters import router as pets_filters_router
from app.routers.pets_stats_reco import router as pets_stats_reco_router
from app.routers.analytics import router as analytics_router
from app.routers.pets_recommender import router as pets_recommender_router

openapi_tags = [
    {"name": "system", "description": "Root metadata and health check endpoints."},
    {"name": "pets.browse", "description": "Browse pets, species, outcomes, and breeds with optional filters."},
    {"name": "pets.summary", "description": "Dataset-level statistics such as counts and averages."},
    {"name": "pets.recommend", "description": "Content-based recommendation engine for suitable pets."},
    {"name": "pets.manage", "description": "Create, read, update, and delete pet records."},
    {"name": "pets.analytics", "description": "Advanced Return-Risk and Welfare/Stress analytics."}
]

# 1) Create the FastAPI app first
app = FastAPI(
    title="PetMatch API",
    version="0.1.0",
    openapi_version="3.0.2",  # keeps classic ReDoc happy
    redoc_url="/redoc",
    redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
)

app.add_middleware(GZipMiddleware, minimum_size=500)

# 2) Register routers
app.include_router(health_router, prefix="/api")
app.include_router(pets_filters_router, prefix="/api")
app.include_router(pets_stats_reco_router, prefix="/api")
app.include_router(pets_recommender_router, prefix="/api")
app.include_router(pets_crud_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")

@app.get("/")
def root():
    return {"name": "PetMatch API", "version": "0.1.0"}

@app.on_event("startup")
def on_startup():
    if os.getenv("TESTING") == "1":
        logger.info("TESTING mode detected, skipping DB creation on startup")
        return

    # Pick base dir based on DATABASE_URL; support both repo-local and Render Disk
    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/petmatch.sqlite")
    base_dir = Path("/var/data") if db_url.startswith("sqlite:////var/data") else Path("data")
    base_dir.mkdir(parents=True, exist_ok=True)

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