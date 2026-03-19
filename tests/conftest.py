import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# ---------------------------------------------------
# Ensure project root is importable
# ---------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------
# Disable API key guards for all tests
# ---------------------------------------------------
@pytest.fixture(autouse=True, scope="session")
def disable_api_keys():
    os.environ.pop("WRITE_API_KEY", None)
    os.environ.pop("ANALYTICS_API_KEY", None)

# ---------------------------------------------------
# Imports AFTER path setup
# ---------------------------------------------------
from app.main import app
from app.database import get_db
from app.models import Base, Pet  # Make sure Pet model is imported
from app.security import require_analytics_api_key

# ---------------------------------------------------
# Disable filesystem writes in tests
# ---------------------------------------------------
@pytest.fixture(autouse=True)
def disable_filesystem_writes(monkeypatch):
    monkeypatch.setattr("os.makedirs", lambda *args, **kwargs: None)

# ---------------------------------------------------
# In-memory test database engine
# ---------------------------------------------------
@pytest.fixture(scope="function")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    try:
        yield eng
    finally:
        eng.dispose()

# ---------------------------------------------------
# Session factory
# ---------------------------------------------------
@pytest.fixture(scope="function")
def session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------
# Seed test data
# ---------------------------------------------------
@pytest.fixture(scope="function")
def seed_pets(session_factory):
    db = session_factory()
    db.add_all([
        Pet(species="Dog", external_id="TEST-DOG-1", breed_name_raw="Labrador", age_months=24),
        Pet(species="Cat", external_id="TEST-CAT-1", breed_name_raw="Siamese", age_months=12),
    ])
    db.commit()
    db.close()
    return True

# ---------------------------------------------------
# FastAPI test client
# ---------------------------------------------------
@pytest.fixture(scope="function")
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_analytics_api_key] = lambda: None

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()