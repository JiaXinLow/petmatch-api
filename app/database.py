import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./data/petmatch.sqlite"

# If it's a local SQLite path, ensure the directory exists
if DATABASE_URL.startswith("sqlite:///"):
    local_path = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite-specific
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()