from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.routers.health import router as health_router

app = FastAPI(title="PetMatch API", version="0.1.0")

app.include_router(health_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"name": "PetMatch API", "version": "0.1.0"}

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)