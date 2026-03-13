from datetime import datetime
from app.models import Pet

def test_welfare_happy_path(client, session_factory):
    with session_factory() as db:
        p = Pet(
            external_id="WF-1",
            species="Dog",
            breed_name_raw="German Shepherd Mix",
            breed_id=None,
            sex_upon_outcome="Unknown",
            age_months=120,
            color="Black/Yellow",
            outcome_type="Transfer",
            outcome_datetime=datetime.utcnow(),
        )
        db.add(p)
        db.commit()
        pid = p.id

    r = client.get(f"/api/analytics/welfare/{pid}")
    assert r.status_code == 200
    body = r.json()

    assert body["pet_id"] == pid
    assert "welfare_score" in body
    assert isinstance(body["components"], list)
    assert len(body["components"]) > 0
    assert "advisory" in body

def test_welfare_404(client):
    r = client.get("/api/analytics/welfare/999999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Pet not found"

def test_welfare_by_external_id(client, session_factory):
    from app.models import Pet

    # Create a test pet
    with session_factory() as db:
        p = Pet(
            external_id="WFTEST-EXT-1",
            species="Dog",
            age_months=120,
            breed_name_raw="Unknown",
            color="Black",
            sex_upon_outcome="Unknown",
            outcome_type="Transfer"
        )
        db.add(p)
        db.commit()
        pid = p.id

    r = client.get("/api/analytics/welfare/by-external-id/WFTEST-EXT-1")
    assert r.status_code == 200

    body = r.json()
    assert body["external_id"] == "WFTEST-EXT-1"
    assert body["pet_id"] == pid
    assert "welfare_score" in body

    # Advisory triggers for senior, unknown sex, dark coat
    advisories = body["advisory"]
    assert any("comfort" in a.lower() for a in advisories)
    assert any("clarify" in a.lower() for a in advisories)
    assert any("visibility" in a.lower() for a in advisories)