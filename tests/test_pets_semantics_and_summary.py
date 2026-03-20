# tests/test_pets_semantics_and_summary.py
import math
from typing import Dict

from app.models import Pet


def test_summary_empty_db(client):
    """
    When the DB is empty, the summary endpoint should:
    - return 200
    - include all required keys
    - have sensible empty defaults
    - NOT include 'monthly_outcomes' (since you removed it)
    """
    r = client.get("/api/pets/summary")
    assert r.status_code == 200, r.text
    data = r.json()

    # Required top-level keys
    for key in [
        "total_pets",
        "species_counts",
        "average_age_months",
        "outcome_counts",
        "outcome_counts_by_species",
        "adoption_rate",
        "sterilization_rate",
        "age_buckets",
        "top_breeds",
        "group_outcomes",
    ]:
        assert key in data, f"Missing key: {key}"

    # Removed field must not exist
    assert "monthly_outcomes" not in data

    # Empty defaults
    assert data["total_pets"] == 0
    assert data["species_counts"] == {}
    assert data["average_age_months"] is None

    # Types / shapes
    assert isinstance(data["outcome_counts"], dict)
    assert isinstance(data["outcome_counts_by_species"], dict)
    assert data["adoption_rate"] is None
    assert data["sterilization_rate"] is None
    assert isinstance(data["age_buckets"], dict)
    assert isinstance(data["top_breeds"], list)
    assert isinstance(data["group_outcomes"], list)

    # Age buckets present and non-negative ints
    for bucket in ["0-5", "6-11", "12-23", "24-59", "60+"]:
        assert bucket in data["age_buckets"]
        assert isinstance(data["age_buckets"][bucket], int)
        assert data["age_buckets"][bucket] >= 0


def test_summary_with_sample_data(client, session_factory):
    """
    Seed a small dataset to verify:
    - totals
    - species counts
    - average age
    - outcome counts & adoption rate
    - age buckets
    - top breeds
    - group_outcomes schema (without requiring breed mapping to be present)
    """
    with session_factory() as db:
        # 5 pets with varied ages & outcomes
        pets = [
            Pet(
                external_id="T-001",
                species="Dog",
                breed_name_raw="Beagle",
                age_months=3,                 # 0-5 bucket
                outcome_type="Adoption",
            ),
            Pet(
                external_id="T-002",
                species="Dog",
                breed_name_raw="Labrador Retriever",
                age_months=8,                 # 6-11 bucket
                outcome_type="Transfer",
            ),
            Pet(
                external_id="T-003",
                species="Cat",
                breed_name_raw="Siamese",
                age_months=15,                # 12-23 bucket
                outcome_type="Adoption",
            ),
            Pet(
                external_id="T-004",
                species="Dog",
                breed_name_raw="German Shepherd",
                age_months=30,                # 24-59 bucket
                outcome_type=None,            # Unknown outcome
            ),
            Pet(
                external_id="T-005",
                species="Dog",
                breed_name_raw="German Shepherd",
                age_months=72,                # 60+ bucket
                outcome_type="Adoption",
            ),
        ]
        db.add_all(pets)
        db.commit()

    r = client.get("/api/pets/summary")
    assert r.status_code == 200, r.text
    data = r.json()

    # Totals & species
    assert data["total_pets"] == 5
    assert data["species_counts"]["Dog"] == 4
    assert data["species_counts"]["Cat"] == 1

    # Average age
    # (3 + 8 + 15 + 30 + 72) / 5 = 128 / 5 = 25.6
    assert math.isclose(data["average_age_months"], 25.6, rel_tol=1e-6)

    # Outcome counts
    oc: Dict[str, int] = data["outcome_counts"]
    # 3 Adoptions, 1 Transfer, 1 Unknown (None outcome)
    assert oc.get("Adoption", 0) == 3
    assert oc.get("Transfer", 0) == 1
    assert oc.get("Unknown", 0) == 1

    # Adoption rate = positive / total_resolved = 3 / (5 - 1) = 3/4 = 0.75
    assert math.isclose(data["adoption_rate"], 0.75, rel_tol=1e-6)

    # Sterilization rate -> our sample has no 'spay/neuter' strings, so denom=0 => None
    assert data["sterilization_rate"] is None

    # Age buckets: each bucket should have exactly 1 in this synthetic set
    expected_buckets = {"0-5": 1, "6-11": 1, "12-23": 1, "24-59": 1, "60+": 1}
    assert data["age_buckets"] == expected_buckets

    # Top breeds: "German Shepherd" should appear with count=2
    top_breeds = {row["breed_name_raw"]: row["count"] for row in data["top_breeds"]}
    assert top_breeds.get("German Shepherd", 0) == 2

    # group_outcomes should be a list; may be empty if BREED_GROUPS is empty
    assert isinstance(data["group_outcomes"], list)
    if data["group_outcomes"]:
        # Validate schema for first item if present
        g0 = data["group_outcomes"][0]
        assert "group" in g0
        assert "outcome_counts" in g0
        assert "adoption_rate" in g0

    # Ensure monthly_outcomes is not present (removed by design)
    assert "monthly_outcomes" not in data