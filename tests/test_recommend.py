from datetime import datetime
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas import PetRead, OutcomeType
from app.routers.pets_recommender import BREED_GROUPS

client = TestClient(app)

# ----------------------------
# Helper to create mock pets
# ----------------------------
def make_pet_read(
    id: int,
    name: str,
    species: str,
    breed_name_raw: str,
    outcome_type: str,
    age_months: int = 12,
    sex_upon_outcome: str = "Neutered Male",
    external_id: str = "EXT123",
    created_at: datetime = None,
    updated_at: datetime = None,
):
    return PetRead(
        id=id,
        name=name,
        species=species,
        breed_name_raw=breed_name_raw,
        age_months=age_months,
        sex_upon_outcome=sex_upon_outcome,
        outcome_type=outcome_type,
        external_id=external_id,
        created_at=created_at or datetime.utcnow(),
        updated_at=updated_at or datetime.utcnow()
    )

# ----------------------------
# Mock DB session
# ----------------------------
class MockSession:
    """Mock DB session returning PetRead objects."""
    def __init__(self, pets):
        self._pets = pets

    def execute(self, query):
        class Result:
            def __init__(self, pets):
                self._pets = pets

            def scalars(self):
                class Scalars:
                    def __init__(self, pets):
                        self._pets = pets
                    def all(self):
                        return self._pets
                return Scalars(self._pets)
        return Result(self._pets)

# ----------------------------
# Fixtures
# ----------------------------
@pytest.fixture
def db_dogs():
    pets = [
        make_pet_read(1, "Buddy", "Dog", "Beagle", "Adoption"),
        make_pet_read(2, "Max", "Dog", "Beagle", "Return to Owner"),
        make_pet_read(3, "Bella", "Dog", "Labrador", "Adoption"),
    ]
    return MockSession(pets)

@pytest.fixture
def db_cats():
    pets = [
        make_pet_read(10, "Whiskers", "Cat", "Siamese", "Adoption"),
        make_pet_read(11, "Mittens", "Cat", "Persian", "Return to Owner"),
    ]
    return MockSession(pets)

# ----------------------------
# Tests
# ----------------------------
ALLOWED_OUTCOMES = [v.value for v in OutcomeType]

def test_recommend_dog(monkeypatch, db_dogs):
    monkeypatch.setattr("app.routers.pets_recommender.get_db", lambda: db_dogs)

    response = client.get("/api/pets/recommend", params={"species": "Dog", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
    for pet in data:
        assert pet["species"] == "Dog"
        assert pet["external_id"] is not None
        assert pet["outcome_type"] in ALLOWED_OUTCOMES

def test_recommend_cat(monkeypatch, db_cats):
    monkeypatch.setattr("app.routers.pets_recommender.get_db", lambda: db_cats)

    response = client.get("/api/pets/recommend", params={"species": "Cat", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
    for pet in data:
        assert pet["species"] == "Cat"
        assert pet["external_id"] is not None
        assert pet["outcome_type"] in ALLOWED_OUTCOMES

def test_recommend_debug(monkeypatch, db_dogs):
    monkeypatch.setattr("app.routers.pets_recommender.get_db", lambda: db_dogs)

    response = client.get("/api/pets/recommend-debug", params={"species": "Dog", "limit": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2

    for item in data:
        pet = item["pet"]
        scores = item["score_breakdown"]

        assert "id" in pet
        assert "species" in pet
        assert "breed_name_raw" in pet
        assert pet["outcome_type"] in ALLOWED_OUTCOMES

        assert "age_score" in scores
        assert "sterilization_score" in scores
        assert "group_score" in scores
        assert "total_score" in scores