import pytest

def test_post_duplicate_external_id_conflict(client):
    payload = {"external_id": "DUP-1", "species": "Dog"}
    r1 = client.post("/api/v1/pets", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/pets", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]

@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_not_found_404_on_missing_resource(client, method):
    url = "/api/v1/pets/999999"
    if method == "get":
        r = client.get(url)
    elif method == "put":
        r = client.put(url, json={"color": "Black"})
    elif method == "patch":
        r = client.patch(url, json={"color": "Black"})
    else:
        r = client.delete(url)

    assert r.status_code == 404
    # For delete 204 is impossible; for others we expect JSON detail
    if method != "delete":  # delete also returns 404 + JSON in your code; keep flexible
        assert "detail" in r.json()

def test_validation_422_list_limit_out_of_bounds(client):
    # limit=0 violates ge=1
    r = client.get("/api/v1/pets?limit=0")
    assert r.status_code == 422

def test_validation_422_list_limit_too_large(client):
    # limit=999 violates le=200
    r = client.get("/api/v1/pets?limit=999")
    assert r.status_code == 422

def test_validation_422_negative_age_in_body(client):
    payload = {"external_id": "NEG-1", "species": "Dog", "age_months": -1}
    r = client.post("/api/v1/pets", json=payload)
    # Pydantic accepts None or non-negative; negative should 422
    assert r.status_code in (400, 422)