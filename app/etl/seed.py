import logging
import pandas as pd
import re
import math

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, select
from app.database import engine, SessionLocal
from app.models import Base, Shelter, Breed, Pet
from app.etl.config import ETLConfig, DB_PATH


log = logging.getLogger(__name__)

# -------------------- Setup engine & session --------------------
DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # ensure /data exists

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# -------------------- small helpers --------------------

def none_if_nan(v):
    """Convert NaN-like to None, leave strings as-is (trimmed)."""
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    s = str(v).strip()
    return s if s != "" else None

def int_or_none(v):
    """Convert numeric-like to int, NaN/blank -> None."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return int(v)
    except Exception:
        try:
            f = float(str(v))
            if pd.isna(f):
                return None
            return int(f)
        except Exception:
            return None

# -------------------- shelter + breeds --------------------

def _get_or_create_shelter(db: Session) -> Shelter:
    s = db.execute(
        select(Shelter).where(Shelter.name == "Austin Animal Center")
    ).scalar_one_or_none()
    if s:
        return s
    s = Shelter(name="Austin Animal Center", city="Austin", state="TX", country="USA")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def _load_breeds(db: Session, breeds_csv) -> int:
    """
    Load cleaned breeds CSV into the 'breeds' table idempotently.
    Expects columns: species, name, group
    """
    df = pd.read_csv(breeds_csv)
    count_new = 0

    for rec in df.to_dict(orient="records"):
        species = (rec.get("species") or "").strip()
        name = (rec.get("name") or "").strip()
        if not species or not name:
            continue

        exists = db.execute(
            select(Breed.id).where(Breed.species == species, Breed.name == name)
        ).scalar_one_or_none()
        if exists:
            continue

        b = Breed(
            species=species,
            name=name,
            group=(rec.get("group") or None),
        )
        db.add(b)
        count_new += 1

    db.commit()
    log.info("Breeds loaded: %s new", count_new)
    return count_new

# -------------------- pets --------------------

def _breed_id_lookup(db: Session) -> dict[tuple[str, str], int]:
    rows = db.execute(select(Breed.id, Breed.species, Breed.name)).all()
    return {(species, name.lower()): bid for (bid, species, name) in rows}

def _normalize_breed_name(raw: str) -> str:
    """
    Make an outcome 'Breed' string comparable to our breeds table.
    Keep it simple + explainable for coursework.
    """
    if not isinstance(raw, str):
        return ""
    name = raw.replace("Mix", "").replace("Dog", "").strip()
    name = name.split("/")[0].strip()
    name = re.sub(r"[^A-Za-z ]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def _load_pets(db: Session, pets_csv, shelter_id: int):
    df = pd.read_csv(pets_csv, parse_dates=["outcome_datetime"])
    breed_index = _breed_id_lookup(db)

    new_count = 0
    for rec in df.to_dict(orient="records"):
        external_id = (rec.get("external_id") or "").strip()
        if not external_id:
            continue

        # idempotency: skip if already inserted
        exists = db.execute(
            select(Pet).where(Pet.external_id == external_id)
        ).scalar_one_or_none()
        if exists:
            continue

        species = none_if_nan(rec.get("species")) or "Other"
        breed_name_raw = none_if_nan(rec.get("breed_name_raw"))

        normalized = (_normalize_breed_name(breed_name_raw or "") or "").strip()
        key = (species, normalized.lower())
        breed_id = breed_index.get(key)

        # normalize bad breed_id values to None
        if not isinstance(breed_id, int):
            breed_id = None

        sex_upon_outcome = none_if_nan(rec.get("sex_upon_outcome"))
        color = none_if_nan(rec.get("color"))
        outcome_type = none_if_nan(rec.get("outcome_type"))
        age_months = int_or_none(rec.get("age_months"))

        # pandas Timestamp/NaT -> Python datetime/None
        odt = rec.get("outcome_datetime")
        if isinstance(odt, pd.Timestamp):
            odt = None if pd.isna(odt) else odt.to_pydatetime()
        else:
            odt = None

        # (Optional) log the first few inserts for sanity during development
        if new_count < 3:
            log.info(
                "INSERT sample | ext=%s | species=%s | raw=%s | norm=%s | breed_id=%s | age=%s | dt=%s",
                external_id, species, breed_name_raw, normalized, breed_id, age_months, odt
            )

        pet = Pet(
            external_id=external_id,
            species=species,
            breed_name_raw=breed_name_raw,
            breed_id=breed_id,              # int or None
            sex_upon_outcome=sex_upon_outcome,
            age_months=age_months,          # int or None
            color=color,
            outcome_type=outcome_type,
            outcome_datetime=odt,           # cleaned datetime
            shelter_id=shelter_id,
        )
        db.add(pet)
        new_count += 1

    db.commit()
    log.info("Pets loaded: %s new", new_count)

# -------------------- entry point --------------------
def run(config: ETLConfig):
    db = SessionLocal()
    try:
        shelter = _get_or_create_shelter(db)
        _load_breeds(db, config.breeds_clean_csv)
        _load_pets(db, config.pets_clean_csv, shelter_id=shelter.id)
    finally:
        db.close()