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
from app.models import Base
from app.security import require_analytics_api_key

# ---------------------------------------------------
# In-memory database for testing
# ---------------------------------------------------
@pytest.fixture(scope="session")
def engine():
    """
    Create a new in-memory SQLite engine for tests.
    Tables are created once per test session.
    """
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables in the test database
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()

@pytest.fixture(scope="session")
def session_factory(engine):
    """
    Returns a session factory bound to the in-memory test database.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------
# FastAPI TestClient with dependency overrides
# ---------------------------------------------------
@pytest.fixture(scope="function")
def client(session_factory):
    """
    Provides a TestClient instance with DB and API key overrides.
    """
    # Override get_db to use in-memory test session
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    # Override any API key guard to do nothing
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_analytics_api_key] = lambda: None

    # Provide a TestClient
    with TestClient(app) as c:
        yield c

    # Clear overrides after each test function
    app.dependency_overrides.clear()