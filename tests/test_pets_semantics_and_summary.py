from app.models import Pet

def test_patch_species_normalization(client):
    # Create a pet as Dog
    r = client.post("/api/pets", json={"external_id": "NORM-1", "species": "Dog"})
    assert r.status_code == 201
    pid = r.json()["id"]

    # Patch species with lowercase "cat" => should normalize to "Cat"
    r = client.patch(f"/api/pets/{pid}", json={"species": "cat"})
    assert r.status_code == 200
    assert r.json()["species"] == "Cat"

def test_summary_average_age_none_returns_null(client, session_factory):
    """
    Ensure that when all pets have age_months=None, the summary endpoint
    returns average_age_months as null.
    """
    # Seed only pets with age_months=None
    with session_factory() as db:
        db.add_all([
            Pet(external_id="S1", species="Dog", age_months=None),
            Pet(external_id="S2", species="Cat", age_months=None),
        ])
        db.commit()

    r = client.get("/api/pets/summary")
    assert r.status_code == 200
    data = r.json()

    # Should see exactly 2 pets
    assert data["total_pets"] == 2
    # Average should be None since all ages are None
    assert data["average_age_months"] is None