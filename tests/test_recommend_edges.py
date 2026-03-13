from app.models import Pet

def test_recommend_returns_empty_when_no_matching_species(client, session_factory):
    # Seed only Cats
    with session_factory() as db:
        db.add(Pet(external_id="C-ONLY", species="Cat", age_months=12))
        db.commit()

    # Ask for Dog
    r = client.get("/api/pets/recommend?species=Dog&limit=5")
    assert r.status_code == 200
    assert r.json() == []  # empty list is expected