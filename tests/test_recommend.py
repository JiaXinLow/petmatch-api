from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest

from app.main import app
from app.models import Pet
from app.routers.pets_recommender import BREED_GROUPS

client = TestClient(app)

# ----------------------------
# Helper to create mock pets
# ----------------------------
def make_pet(
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
    pet = Pet()
    pet.id = id
    pet.name = name
    pet.species = species
    pet.breed_name_raw = breed_name_raw
    pet.age_months = age_months
    pet.sex_upon_outcome = sex_upon_outcome
    pet.outcome_type = outcome_type  # Must match PetRead enum exactly
    pet.external_id = external_id
    pet.created_at = created_at or datetime.utcnow()
    pet.updated_at = updated_at or datetime.utcnow()
    return pet

# ----------------------------
# Mock DB session
# ----------------------------
class MockSession:
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
# Tests
# ----------------------------
@pytest.fixture
def db_dogs():
    pets = [
        make_pet(1, "Buddy", "Dog", "Beagle", "Adoption"),
        make_pet(2, "Max", "Dog", "Beagle", "Return to Owner"),
        make_pet(3, "Bella", "Dog", "Labrador", "Adoption"),
    ]
    return MockSession(pets)

@pytest.fixture
def db_cats():
    pets = [
        make_pet(10, "Whiskers", "Cat", "Siamese", "Adoption"),
        make_pet(11, "Mittens", "Cat", "Persian", "Return to Owner"),
    ]
    return MockSession(pets)

def test_recommend_dog(monkeypatch, db_dogs):
    # Patch the DB dependency to use mock
    monkeypatch.setattr("app.routers.pets_recommender.get_db", lambda: db_dogs)

    response = client.get("/api/pets/recommend", params={"species": "Dog", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
    for pet in data:
        assert pet["species"] == "Dog"
        assert pet["external_id"] is not None
        assert pet["outcome_type"] in [
            "Adoption", "Died", "Disposal", "Euthanasia", "Lost",
            "Missing", "Relocate", "Return to Owner", "Rto-Adopt",
            "Stolen", "Transfer"
        ]

def test_recommend_cat(monkeypatch, db_cats):
    monkeypatch.setattr("app.routers.pets_recommender.get_db", lambda: db_cats)

    response = client.get("/api/pets/recommend", params={"species": "Cat", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
    for pet in data:
        assert pet["species"] == "Cat"
        assert pet["external_id"] is not None
        assert pet["outcome_type"] in [
            "Adoption", "Died", "Disposal", "Euthanasia", "Lost",
            "Missing", "Relocate", "Return to Owner", "Rto-Adopt",
            "Stolen", "Transfer"
        ]

def test_recommend_debug(client):
    response = client.get("/api/pets/recommend-debug", params={"species": "Dog", "limit": 2})
    assert response.status_code == 200

    data = response.json()
    assert len(data) <= 2

    for item in data:
        pet = item["pet"]
        scores = item["score_breakdown"]

        # Check PetRead fields
        assert "id" in pet
        assert "species" in pet
        assert "breed_name_raw" in pet

        # Check score_breakdown fields
        assert "age_score" in scores
        assert "sterilization_score" in scores
        assert "group_score" in scores
        assert "total_score" in scores