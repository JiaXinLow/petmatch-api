from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.routers.health import router as health_router
from app.routers.pets_crud import router as pets_crud_router
from app.routers.pets_filters import router as pets_filters_router
from app.routers.pets_stats_reco import router as pets_stats_reco_router
from app.routers.analytics import router as analytics_router

app = FastAPI(title="PetMatch API", version="0.1.0")

# --- Create tables (meets “SQL model” requirement for the brief) ---
Base.metadata.create_all(bind=engine)

app.include_router(health_router, prefix="/api/v1")

# Static routes and list endpoint FIRST
app.include_router(pets_filters_router, prefix="/api/v1")
app.include_router(pets_stats_reco_router, prefix="/api/v1")

# Dynamic /pets/{pet_id} LAST
app.include_router(pets_crud_router, prefix="/api/v1")

# Analytics (independent)
app.include_router(analytics_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"name": "PetMatch API", "version": "0.1.0"}