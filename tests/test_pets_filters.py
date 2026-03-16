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

    # --- Species list ---
    r = client.get("/api/pets/species")
    assert r.status_code == 200
    species_vals = r.json()
    assert "Dog" in species_vals
    assert "Cat" in species_vals

    # --- Outcomes list ---
    r = client.get("/api/pets/outcomes")
    assert r.status_code == 200
    outcomes_vals = r.json()
    assert "Adoption" in outcomes_vals
    assert "Transfer" in outcomes_vals

    # --- Breeds for Dogs (Title Case) ---
    r = client.get("/api/pets/breeds?species=Dog")
    assert r.status_code == 200
    assert "Beagle" in r.json()

    # --- Summary ---
    r = client.get("/api/pets/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total_pets"] >= 2
    assert data["species_counts"]["Dog"] >= 1
    assert data["species_counts"]["Cat"] >= 1

    # --- NEW: Case-insensitive species filter ---
    r_title = client.get("/api/pets", params={"species": "Dog", "limit": 50})
    r_lower = client.get("/api/pets", params={"species": "dog", "limit": 50})
    assert r_title.status_code == 200 and r_lower.status_code == 200
    assert r_title.json() == r_lower.json()

    # --- NEW: Case-insensitive outcome_type filter ---
    r_title = client.get("/api/pets", params={"outcome_type": "Transfer", "limit": 50})
    r_lower = client.get("/api/pets", params={"outcome_type": "transfer", "limit": 50})
    assert r_title.status_code == 200 and r_lower.status_code == 200
    assert r_title.json() == r_lower.json()

    # --- NEW: Combined case-insensitive filter (should match the seeded Cat/Transfer) ---
    r = client.get("/api/pets", params={
        "species": "cat",              # lower
        "outcome_type": "transfer",    # lower
        "limit": 10,
        "offset": 0
    })
    assert r.status_code == 200
    rows = r.json()
    assert any(p["species"] == "Cat" and p["outcome_type"] == "Transfer" for p in rows)

    # --- NEW: Breeds endpoint accepts lowercase species too ---
    r = client.get("/api/pets/breeds", params={"species": "dog"})
    assert r.status_code == 200
    assert "Beagle" in r.json()