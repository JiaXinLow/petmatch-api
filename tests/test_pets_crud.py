import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models import Base

# --- test database (shared in-memory) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # share the same connection across sessions
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create schema once in the shared in-memory DB
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_pets_crud_flow():
    # ---- Create ----
    eid = f"TEST-{uuid.uuid4().hex[:8]}"  # ensure uniqueness per test run
    payload = {
        "external_id": eid,
        "species": "Dog",
        "breed_name_raw": "Labrador Retriever Mix",
        "breed_id": None,
        "sex_upon_outcome": "Neutered Male",
        "age_months": 24,
        "color": "Black",
        "outcome_type": "Adoption",
        "outcome_datetime": None,
        "shelter_id": None
    }
    r = client.post("/api/pets", json=payload)
    assert r.status_code == 201, r.text
    pet = r.json()
    pid = pet["id"]
    assert pet["external_id"] == eid
    assert pet["species"] == "Dog"

    # ---- Read ----
    r = client.get(f"/api/pets/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid
    
    # ---- Update (PATCH - partial update) ----
    r = client.patch(f"/api/pets/{pid}", json={"color": "Black/White"})
    assert r.status_code == 200, r.text
    assert r.json()["color"] == "Black/White"


    # ---- List ---- 
    r = client.get("/api/pets", params={"species": "Dog", "limit": 10, "offset": 0})
    assert r.status_code == 200
    assert any(row["id"] == pid for row in r.json())

    # ---- Delete ----
    r = client.delete(f"/api/pets/{pid}")
    assert r.status_code == 204

    # ---- Read-after-delete -> 404 ----
    r = client.get(f"/api/pets/{pid}")
    assert r.status_code == 404