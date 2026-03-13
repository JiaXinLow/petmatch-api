# tests/test_write_auth.py
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

def make_pet_payload():
    return {
        "external_id": f"TEST-{uuid.uuid4()}",
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

@pytest.fixture
def client():
    return TestClient(app)

def test_writes_require_key_when_enabled(monkeypatch, client):
    # Enable write guard
    monkeypatch.setenv("WRITE_API_KEY", "wsecret")

    # --- Create with correct key -> 201 ---
    payload = make_pet_payload()
    r = client.post("/api/pets", json=payload, headers={"X-API-Key": "wsecret"})
    assert r.status_code == 201, r.text
    pet = r.json()
    pet_id = pet["id"]

    # --- PATCH without key -> 401 ---
    r = client.patch(f"/api/pets/{pet_id}", json={"color": "Brown"})
    assert r.status_code == 401

    # --- PATCH with wrong key -> 401 ---
    r = client.patch(f"/api/pets/{pet_id}", json={"color": "Brown"}, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401

    # --- PATCH with correct key -> 200 ---
    r = client.patch(f"/api/pets/{pet_id}", json={"color": "Brown"}, headers={"X-API-Key": "wsecret"})
    assert r.status_code == 200, r.text

def test_writes_open_when_guard_off(monkeypatch, client):
    # Disable write guard
    monkeypatch.delenv("WRITE_API_KEY", raising=False)

    # --- Create without key -> 201 ---
    payload = make_pet_payload()
    r = client.post("/api/pets", json=payload)
    assert r.status_code == 201, r.text
    pet_id = r.json()["id"]

    # --- PATCH without key -> 200 ---
    r = client.patch(f"/api/pets/{pet_id}", json={"color": "Black"})
    assert r.status_code == 200, r.text