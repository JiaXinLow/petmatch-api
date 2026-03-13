# tests/test_dual_keys_matrix.py
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def new_external_id():
    return f"TEST-{uuid.uuid4()}"

def create_pet(client, headers=None, status=201):
    payload = {
        "external_id": new_external_id(),
        "species": "Dog",
        "breed_name_raw": "Mixed",
        "breed_id": None,
        "sex_upon_outcome": None,
        "age_months": 12,
        "color": None,
        "outcome_type": None,
        "outcome_datetime": None,
        "shelter_id": None,
    }
    r = client.post("/api/pets", json=payload, headers=headers or {})
    assert r.status_code == status, r.text
    return r.json() if r.status_code in (200, 201) else None

def read_pet(client, pet_id, headers=None, expected=200):
    r = client.get(f"/api/pets/{pet_id}", headers=headers or {})
    assert r.status_code == expected, r.text
    return r

def call_analytics(client, headers=None, expected=404):
    # Hit a non-existent resource to observe guard then 404
    r = client.get("/api/analytics/return-risk/999999", headers=headers or {})
    assert r.status_code == expected, r.text
    return r

def test_both_unset_open_everything(monkeypatch, client):
    monkeypatch.delenv("ANALYTICS_API_KEY", raising=False)
    monkeypatch.delenv("WRITE_API_KEY", raising=False)

    # Analytics open
    call_analytics(client, expected=404)

    # Writes open
    pet = create_pet(client, status=201)
    read_pet(client, pet["id"], expected=200)

def test_only_analytics_set(monkeypatch, client):
    monkeypatch.setenv("ANALYTICS_API_KEY", "asecret")
    monkeypatch.delenv("WRITE_API_KEY", raising=False)

    # Analytics requires asecret
    call_analytics(client, headers=None, expected=401)
    call_analytics(client, headers={"X-API-Key": "wrong"}, expected=401)
    call_analytics(client, headers={"X-API-Key": "asecret"}, expected=404)

    # Writes are still open (no write key set)
    pet = create_pet(client, headers=None, status=201)
    read_pet(client, pet["id"], expected=200)

def test_only_write_set(monkeypatch, client):
    monkeypatch.delenv("ANALYTICS_API_KEY", raising=False)
    monkeypatch.setenv("WRITE_API_KEY", "wsecret")

    # Analytics open
    call_analytics(client, expected=404)

    # Writes require wsecret
    create_pet(client, headers=None, status=401)
    create_pet(client, headers={"X-API-Key": "wrong"}, status=401)
    pet = create_pet(client, headers={"X-API-Key": "wsecret"}, status=201)

    # Non-mutating read remains open
    read_pet(client, pet["id"], expected=200)

def test_both_set_independent(monkeypatch, client):
    monkeypatch.setenv("ANALYTICS_API_KEY", "asecret")
    monkeypatch.setenv("WRITE_API_KEY", "wsecret")

    # Analytics accepts ONLY asecret
    call_analytics(client, headers=None, expected=401)
    call_analytics(client, headers={"X-API-Key": "wsecret"}, expected=401)  # wrong domain
    call_analytics(client, headers={"X-API-Key": "asecret"}, expected=404)

    # Writes accept ONLY wsecret
    create_pet(client, headers=None, status=401)
    create_pet(client, headers={"X-API-Key": "asecret"}, status=401)  # wrong domain
    pet = create_pet(client, headers={"X-API-Key": "wsecret"}, status=201)

    # Read remains open
    read_pet(client, pet["id"], expected=200)