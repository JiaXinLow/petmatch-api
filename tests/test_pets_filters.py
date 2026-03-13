from app.models import Pet

def seed_sample(session_factory):
    # Seed through the SAME engine/connection the API uses (via the fixture override)
    with session_factory() as db:
        db.add_all([
            Pet(
                external_id="T1",
                species="Dog",
                breed_name_raw="Beagle",
                breed_id=None,
                sex_upon_outcome="Neutered Male",
                age_months=24,
                color="Black",
                outcome_type="Adoption",
                outcome_datetime=None,
                shelter_id=None,
            ),
            Pet(
                external_id="T2",
                species="Cat",
                breed_name_raw="Siamese",
                breed_id=None,
                sex_upon_outcome="Spayed Female",
                age_months=12,
                color="Brown",
                outcome_type="Transfer",
                outcome_datetime=None,
                shelter_id=None,
            ),
        ])
        db.commit()

def test_filters(client, session_factory):
    seed_sample(session_factory)

    # Species
    r = client.get("/api/pets/species")
    assert r.status_code == 200
    assert "Dog" in r.json()
    assert "Cat" in r.json()

    # Outcomes
    r = client.get("/api/pets/outcomes")
    assert r.status_code == 200
    assert "Adoption" in r.json()
    assert "Transfer" in r.json()

    # Breeds for Dogs
    r = client.get("/api/pets/breeds?species=Dog")
    assert r.status_code == 200
    assert "Beagle" in r.json()

    # Summary
    r = client.get("/api/pets/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_pets"] >= 2
    assert data["species_counts"]["Dog"] >= 1
    assert data["species_counts"]["Cat"] >= 1