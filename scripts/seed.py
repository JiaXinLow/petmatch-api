"""
Lightweight demo seeder (no ETL required).

Purpose:
- Quickly insert 3 predictable pets (Dog, Cat, Other) for manual testing and demos.
- Works even if you haven't run the full ETL pipeline.
- Idempotent: re-running will not duplicate rows.

Usage:
    # Use default local SQLite file (petmatch.sqlite)
    python scripts/seed.py

    # Or, specify a DB URL explicitly
    # Windows PowerShell:
    #   $env:DATABASE_URL = "sqlite:///./petmatch.sqlite"; python scripts/seed.py
    # macOS/Linux:
    #   export DATABASE_URL="sqlite:///./petmatch.sqlite"; python scripts/seed.py
"""

import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import your app's ORM models and metadata
from app.models import Base, Pet

DEFAULT_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./petmatch.sqlite")


def main():
    # Create engine/session bound to the same DB URL your app uses
    engine = create_engine(
        DEFAULT_DB_URL,
        connect_args={"check_same_thread": False} if DEFAULT_DB_URL.startswith("sqlite") else {},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    demo_ids = {"DEMO-D1", "DEMO-C1", "DEMO-O1"}

    with SessionLocal() as db:
        # Idempotency: remove any previous demo rows
        db.query(Pet).filter(Pet.external_id.in_(demo_ids)).delete(synchronize_session=False)

        demo_pets = [
            Pet(
                external_id="DEMO-D1",
                species="Dog",
                breed_name_raw="Mixed",
                breed_id=None,
                sex_upon_outcome="Neutered Male",
                age_months=24,
                color="Black",
                outcome_type="Adoption",
                outcome_datetime=datetime.utcnow(),
                shelter_id=None,
            ),
            Pet(
                external_id="DEMO-C1",
                species="Cat",
                breed_name_raw="Siamese",
                breed_id=None,
                sex_upon_outcome="Spayed Female",
                age_months=12,
                color="Brown",
                outcome_type="Transfer",
                outcome_datetime=datetime.utcnow(),
                shelter_id=None,
            ),
            Pet(
                external_id="DEMO-O1",
                species="Other",
                breed_name_raw="Turtle Mix",
                breed_id=None,
                sex_upon_outcome="Unknown",
                age_months=6,
                color="Green",
                outcome_type="Transfer",
                outcome_datetime=datetime.utcnow(),
                shelter_id=None,
            ),
        ]

        db.add_all(demo_pets)
        db.commit()

        # Tiny feedback
        species = [s for (s,) in db.query(Pet.species).distinct().all() if s]
        print(f"[seed] DB: {DEFAULT_DB_URL}")
        print(f"[seed] Inserted demo pets: {[p.external_id for p in demo_pets]}")
        print(f"[seed] Species now present: {species}")


if __name__ == "__main__":
    main()