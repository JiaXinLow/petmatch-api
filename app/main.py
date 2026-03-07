from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.routers.health import router as health_router
from app.routers.pets import router as pets_router

app = FastAPI(title="PetMatch API", version="0.1.0")

# --- Create tables (meets “SQL model” requirement for the brief) ---
Base.metadata.create_all(bind=engine)

app.include_router(health_router, prefix="/api/v1")
app.include_router(pets_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"name": "PetMatch API", "version": "0.1.0"}