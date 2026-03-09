from datetime import datetime, timedelta
from app.models import Pet

def seed_species(db, species: str, n_total: int, n_adopted: int, days_ago: int = 30):
    """Seed n_total pets of a species within the time window; mark n_adopted as Adoption."""
    since_dt = datetime.utcnow() - timedelta(days=days_ago)
    count_adopt = 0
    for i in range(n_total):
        outcome_type = "Adoption" if count_adopt < n_adopted else "Transfer"
        p = Pet(
            external_id=f"S-{species}-{i}",
            species=species,
            breed_name_raw="Mixed",
            breed_id=None,
            sex_upon_outcome="Unknown" if i % 2 == 0 else "Neutered Male",
            age_months=12,
            color="Black/Gray" if i % 3 == 0 else "Brown",
            outcome_type=outcome_type,
            outcome_datetime=since_dt,
            shelter_id=None,
        )
        db.add(p)
        count_adopt += (1 if outcome_type == "Adoption" else 0)
    db.commit()


def test_return_risk_happy_path(client, session_factory):
    # Seed cohort: "Other" species with low adoption rate
    with session_factory() as db:
        seed_species(db, "Other", n_total=10, n_adopted=1, days_ago=10)
        # Create a specific pet we will query
        p = Pet(
            external_id="RR-1",
            species="Other",
            breed_name_raw="Turtle Mix",
            breed_id=None,
            sex_upon_outcome="Unknown",
            age_months=24,
            color="Black/Yellow",
            outcome_type="Transfer",
            outcome_datetime=datetime.utcnow(),
        )
        db.add(p)
        db.commit()
        pid = p.id

    r = client.get(f"/api/v1/analytics/return-risk/{pid}?window_days=180")
    assert r.status_code == 200
    body = r.json()
    assert body["pet_id"] == pid
    assert isinstance(body["risk_score"], int)
    names = [c["name"] for c in body["components"]]
    assert "species_other_penalty" in names
    assert "unknown_sex_penalty" in names
    assert "dark_coat_penalty" in names
    assert "low_cohort_adoption_rate_penalty" in names


def test_return_risk_404(client):
    r = client.get("/api/v1/analytics/return-risk/999999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Pet not found"


def test_return_risk_by_external_id(client, session_factory):
    # New test for the staff-friendly endpoint
    with session_factory() as db:
        p = Pet(external_id="A668305", species="Other", color="Black", outcome_type="Transfer")
        db.add(p)
        db.commit()
        pid = p.id

    r = client.get("/api/v1/analytics/return-risk/by-external-id/A668305")
    assert r.status_code == 200
    body = r.json()
    assert body["external_id"] == "A668305"
    assert body["pet_id"] == pid
    assert "risk_score" in body