from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool  # <-- add this
from app.main import app
from app.database import get_db
from app.models import Base

# --- test database (shared in-memory) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # <-- critical: share the same connection
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create schema in the shared in-memory DB
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
    # Create
    payload = {
        "external_id": "TEST-001",
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
    r = client.post("/api/v1/pets", json=payload)
    assert r.status_code == 201, r.text
    pet = r.json()
    pid = pet["id"]
    assert pet["external_id"] == "TEST-001"
    assert pet["species"] == "Dog"

    # Read
    r = client.get(f"/api/v1/pets/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid

    # Update
    r = client.put(f"/api/v1/pets/{pid}", json={"color": "Black/White"})
    assert r.status_code == 200
    assert r.json()["color"] == "Black/White"

    # List
    r = client.get("/api/v1/pets?species=Dog&limit=10&offset=0")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    # Delete
    r = client.delete(f"/api/v1/pets/{pid}")
    assert r.status_code == 204

    # Read-after-delete
    r = client.get(f"/api/v1/pets/{pid}")
    assert r.status_code == 404