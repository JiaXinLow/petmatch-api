from app.models import Pet

def test_recommend_returns_empty_when_no_matching_species(client, session_factory):
    """
    Ensure that when there are no pets of the requested species,
    the recommend endpoint returns an empty list.
    """
    # Seed only Cats
    with session_factory() as db:
        db.add(Pet(external_id="C-ONLY", species="Cat", age_months=12))
        db.commit()

    # Request Dogs (none exist)
    r = client.get("/api/pets/recommend?species=Dog&limit=5")
    assert r.status_code == 200
    assert r.json() == []  # Should return empty list