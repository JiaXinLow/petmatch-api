# --- PATH GUARD: ensure 'app' package is importable when running pytest from any CWD
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Pet, Breed
from app.services.recommender import (
    age_similarity,
    compute_score,
    recommend_pets,
    DEFAULT_WEIGHTS,
)

# -----------------------------------------------------------------------------
# Fixtures: in-memory SQLite per test (clean each run)
# -----------------------------------------------------------------------------
@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh in-memory DB for each test function.
    Uses StaticPool so the same connection is reused within the engine.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Unit tests: age_similarity
# -----------------------------------------------------------------------------
def test_age_similarity_none_values():
    assert age_similarity(None, 10) == 0.0
    assert age_similarity(10, None) == 0.0
    assert age_similarity(None, None) == 0.0


def test_age_similarity_same_age():
    # diff=0 => 1/(1+0) = 1.0
    assert age_similarity(24, 24) == 1.0


def test_age_similarity_distance_decay():
    # diff=36 => 1/(1+36) = 1/37
    assert age_similarity(60, 24) == pytest.approx(1.0 / 37.0, rel=1e-6)


# -----------------------------------------------------------------------------
# Unit tests: compute_score
# -----------------------------------------------------------------------------
def test_compute_score_full_match_with_adoption_bonus():
    pet = Pet(
        external_id="P1",
        species="Dog",
        breed_name_raw="Beagle",
        breed_id=1,
        sex_upon_outcome="Neutered Male",
        age_months=24,
        color="Black",
        outcome_type="Adoption",
        outcome_datetime=None,
        shelter_id=None,
    )
    breed = Breed(
        id=1,
        species="Dog",
        name="Beagle",
        size="Medium",
        energy_level="High",
    )

    w = DEFAULT_WEIGHTS
    expected = w["species"] + w["size"] + w["energy"] + w["age"] * 1.0 + w["adoptable"]

    score = compute_score(
        pet=pet,
        breed=breed,
        user_species="Dog",
        user_size="Medium",
        user_energy="High",
        target_age=24,
    )
    assert score == pytest.approx(expected, rel=1e-6)


def test_compute_score_case_insensitive_outcome_type():
    pet = Pet(
        external_id="P2",
        species="Dog",
        breed_name_raw="Bulldog",
        breed_id=2,
        sex_upon_outcome="Neutered Male",
        age_months=36,
        color="Brown",
        outcome_type="ADOPTION",  # uppercase, should still count
        outcome_datetime=None,
        shelter_id=None,
    )
    breed = Breed(
        id=2,
        species="Dog",
        name="Bulldog",
        size="Large",
        energy_level="Low",
    )

    score = compute_score(
        pet=pet,
        breed=breed,
        user_species="Dog",
        user_size="Large",
        user_energy="Low",
        target_age=36,
    )
    # At least adoptable weight must be present
    assert score >= DEFAULT_WEIGHTS["adoptable"]


def test_compute_score_missing_breed_skips_size_energy():
    pet = Pet(
        external_id="P3",
        species="Dog",
        breed_name_raw="Unknown",
        breed_id=None,  # no breed
        sex_upon_outcome="Spayed Female",
        age_months=12,
        color="White",
        outcome_type="Adoption",
        outcome_datetime=None,
        shelter_id=None,
    )

    score = compute_score(
        pet=pet,
        breed=None,  # explicitly no breed object
        user_species="Dog",
        user_size="Small",
        user_energy="High",
        target_age=12,
    )
    expected_min = (
        DEFAULT_WEIGHTS["species"]
        + DEFAULT_WEIGHTS["adoptable"]
        + DEFAULT_WEIGHTS["age"] * 1.0
    )
    assert score == pytest.approx(expected_min, rel=1e-6)


def test_compute_score_ignores_size_energy_when_user_pref_none():
    pet = Pet(
        external_id="P4",
        species="Dog",
        breed_name_raw="Beagle",
        breed_id=1,
        sex_upon_outcome="Neutered Male",
        age_months=24,
        color="Black",
        outcome_type="Adoption",
        outcome_datetime=None,
        shelter_id=None,
    )
    breed = Breed(id=1, species="Dog", name="Beagle", size="Medium", energy_level="High")

    score = compute_score(
        pet=pet,
        breed=breed,
        user_species="Dog",
        user_size=None,
        user_energy=None,
        target_age=24,
    )
    expected = (
        DEFAULT_WEIGHTS["species"]
        + DEFAULT_WEIGHTS["age"] * 1.0
        + DEFAULT_WEIGHTS["adoptable"]
    )
    assert score == pytest.approx(expected, rel=1e-6)


# -----------------------------------------------------------------------------
# Integration-like tests: recommend_pets with a real DB session
# -----------------------------------------------------------------------------
def test_recommend_pets_orders_and_limit(db_session):
    # Seed breeds (add required species)
    beagle = Breed(species="Dog", name="Beagle", size="Medium", energy_level="High")
    bulldog = Breed(species="Dog", name="Bulldog", size="Large", energy_level="Low")
    siamese = Breed(species="Cat", name="Siamese", size="Small", energy_level="High")
    db_session.add_all([beagle, bulldog, siamese])
    db_session.commit()

    # Seed pets (2 dogs, 1 cat)
    dog_match = Pet(
        external_id="D1",
        species="Dog",
        breed_name_raw="Beagle",
        breed_id=beagle.id,
        sex_upon_outcome="Neutered Male",
        age_months=24,
        color="Black",
        outcome_type="Adoption",
        outcome_datetime=None,
        shelter_id=None,
    )
    dog_less_match = Pet(
        external_id="D2",
        species="Dog",
        breed_name_raw="Bulldog",
        breed_id=bulldog.id,
        sex_upon_outcome="Neutered Male",
        age_months=60,
        color="Brown",
        outcome_type="Transfer",
        outcome_datetime=None,
        shelter_id=None,
    )
    cat_other = Pet(
        external_id="C1",
        species="Cat",
        breed_name_raw="Siamese",
        breed_id=siamese.id,
        sex_upon_outcome="Spayed Female",
        age_months=12,
        color="Brown",
        outcome_type="Adoption",
        outcome_datetime=None,
        shelter_id=None,
    )
    db_session.add_all([dog_match, dog_less_match, cat_other])
    db_session.commit()

    results = recommend_pets(
        db=db_session,
        species="Dog",
        size="Medium",
        energy="High",
        target_age=24,
        limit=10,
    )
    # Only dogs, ordered by score descending
    assert [p.external_id for p in results] == ["D1", "D2"]

    top1 = recommend_pets(
        db=db_session,
        species="Dog",
        size="Medium",
        energy="High",
        target_age=24,
        limit=1,
    )
    assert len(top1) == 1
    assert top1[0].external_id == "D1"


def test_recommend_pets_handles_missing_breed(db_session):
    # Seed one dog breed (required species)
    beagle = Breed(species="Dog", name="Beagle", size="Medium", energy_level="High")
    db_session.add(beagle)
    db_session.commit()

    with_breed = Pet(
        external_id="D3",
        species="Dog",
        breed_name_raw="Beagle",
        breed_id=beagle.id,
        sex_upon_outcome="Neutered Male",
        age_months=24,
        color="Black",
        outcome_type="Adoption",
        outcome_datetime=None,
        shelter_id=None,
    )
    no_breed = Pet(
        external_id="D4",
        species="Dog",
        breed_name_raw="Unknown",
        breed_id=None,
        sex_upon_outcome="Spayed Female",
        age_months=24,
        color="White",
        outcome_type="Adoption",
        outcome_datetime=None,
        shelter_id=None,
    )
    db_session.add_all([with_breed, no_breed])
    db_session.commit()

    results = recommend_pets(
        db=db_session,
        species="Dog",
        size="Medium",
        energy="High",
        target_age=24,
        limit=10,
    )
    # Should not crash; with breed (matching size/energy) should rank first
    assert [p.external_id for p in results] == ["D3", "D4"]