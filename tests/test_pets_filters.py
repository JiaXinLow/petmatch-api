from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import get_db
from app.models import Base, Pet

# Shared in-memory DB
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


# Override dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def seed_sample():
    db = TestingSessionLocal()
    pets = [
        Pet(external_id="T1", species="Dog", breed_name_raw="Beagle", breed_id=None,
            sex_upon_outcome="Neutered Male", age_months=24, color="Black",
            outcome_type="Adoption", outcome_datetime=None, shelter_id=None),
        Pet(external_id="T2", species="Cat", breed_name_raw="Siamese", breed_id=None,
            sex_upon_outcome="Spayed Female", age_months=12, color="Brown",
            outcome_type="Transfer", outcome_datetime=None, shelter_id=None),
    ]
    for p in pets:
        db.add(p)
    db.commit()
    db.close()


def test_filters():
    seed_sample()

    # Species
    r = client.get("/api/v1/pets/species")
    print("DEBUG:", r.json())
    assert r.status_code == 200
    assert "Dog" in r.json()
    assert "Cat" in r.json()

    # Outcomes
    r = client.get("/api/v1/pets/outcomes")
    assert r.status_code == 200
    assert "Adoption" in r.json()
    assert "Transfer" in r.json()

    # Breeds for Dogs
    r = client.get("/api/v1/pets/breeds?species=Dog")
    assert r.status_code == 200
    assert "Beagle" in r.json()

    # Summary
    r = client.get("/api/v1/pets/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_pets"] >= 2
    assert data["species_counts"]["Dog"] >= 1
    assert data["species_counts"]["Cat"] >= 1