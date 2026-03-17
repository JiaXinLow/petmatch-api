from datetime import datetime
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas import OutcomeType

client = TestClient(app)

# ----------------------------
# Minimal mock ORM object
# ----------------------------
class MockPet:
    """Mimics SQLAlchemy Pet ORM object for FastAPI serialization"""
    def __init__(
        self,
        id: int,
        name: str,
        species: str,
        breed_name_raw: str,
        outcome_type: str,
        external_id: str = "EXT123",
        age_months: int = 12,
        sex_upon_outcome: str = "Neutered Male",
    ):
        self.id = id
        self.name = name
        self.species = species
        self.breed_name_raw = breed_name_raw
        self.outcome_type = outcome_type  # lowercase canonical string
        self.external_id = external_id
        self.age_months = age_months
        self.sex_upon_outcome = sex_upon_outcome
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


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
# Fixtures
# ----------------------------
@pytest.fixture
def db_dogs():
    pets = [
        MockPet(1, "Buddy", "Dog", "Beagle", "adoption"),
        MockPet(2, "Max", "Dog", "Beagle", "return to owner"),
        MockPet(3, "Bella", "Dog", "Labrador", "adoption"),
    ]
    return MockSession(pets)


@pytest.fixture
def db_cats():
    pets = [
        MockPet(10, "Whiskers", "Cat", "Siamese", "adoption"),
        MockPet(11, "Mittens", "Cat", "Persian", "return to owner"),
    ]
    return MockSession(pets)


# ----------------------------
# Allowed outcomes
# ----------------------------
ALLOWED_OUTCOMES = [v.value for v in OutcomeType]


# ----------------------------
# Tests
# ----------------------------
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

        # Pet fields
        assert "id" in pet
        assert "species" in pet
        assert "breed_name_raw" in pet
        assert pet["outcome_type"] in ALLOWED_OUTCOMES

        # Score breakdown
        assert "age_score" in scores
        assert "sterilization_score" in scores
        assert "group_score" in scores
        assert "total_score" in scores