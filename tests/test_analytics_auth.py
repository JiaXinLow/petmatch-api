# tests/test_analytics_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.parametrize(
    "env_value, header_value, expected_status",
    [
        # Guard OFF (no env) -> falls through to handler -> 404 for missing pet
        (None, None, 404),
        (None, "anything", 404),

        # Guard ON -> require correct header
        ("secret", None, 401),
        ("secret", "wrong", 401),
        ("secret", "secret", 404),  # passes guard, still 404 (missing pet)
    ],
)
def test_analytics_api_key(monkeypatch, env_value, header_value, expected_status):
    if env_value is None:
        monkeypatch.delenv("ANALYTICS_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ANALYTICS_API_KEY", env_value)

    client = TestClient(app)
    headers = {}
    if header_value is not None:
        headers["X-API-Key"] = header_value

    r = client.get("/api/analytics/return-risk/9999", headers=headers)
    assert r.status_code == expected_status