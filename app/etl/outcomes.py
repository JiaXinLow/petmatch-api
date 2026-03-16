import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from .models import PetRow
from .config import ETLConfig

log = logging.getLogger(__name__)

KEEP_MAP = {
    "Animal ID": "external_id",
    "Animal Type": "species",
    "Breed": "breed_name_raw",
    "Sex upon Outcome": "sex_upon_outcome",
    "Age upon Outcome": "age_upon_outcome",
    "Color": "color",
    "Outcome Type": "outcome_type",
    "DateTime": "outcome_datetime",
}

# add near top of outcomes.py
_OUTCOME_CANONICAL = {
    "adoption": "Adoption",
    "transfer": "Transfer",
    "return to owner": "Return to Owner",
    "rto-adopt": "Rto-Adopt",
    "euthanasia": "Euthanasia",
    "died": "Died",
    "disposal": "Disposal",
    "lost": "Lost",
    "missing": "Missing",
    "relocate": "Relocate",
    "stolen": "Stolen",
}

def _normalize_outcome_type(v: str | None) -> str | None:
    if v is None:
        return None
    key = str(v).strip().lower()
    return _OUTCOME_CANONICAL.get(key) or str(v).strip()

def _none_if_nan(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    s = str(v).strip()
    return s if s != "" else None

def _int_or_none(v):
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

def _age_to_months(v: str) -> int | None:
    if not isinstance(v, str):
        return None
    s = v.lower().strip()
    parts = s.split()
    if not parts or not parts[0].isdigit():
        return None
    n = int(parts[0])
    if "year" in s:
        return n * 12
    if "month" in s:
        return n
    if "week" in s:
        return max(1, round(n/4))
    if "day" in s:
        return 1
    return None

def _parse_dt(v: str) -> datetime | None:
    if not isinstance(v, str) or not v.strip():
        return None
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(v.strip(), fmt)
        except Exception:
            continue
    return None

def run(config: ETLConfig) -> Path:
    log.info("Reading outcomes CSV: %s", config.outcomes_csv)
    df = pd.read_csv(config.outcomes_csv)

    df = df[[c for c in KEEP_MAP if c in df.columns]].rename(columns=KEEP_MAP)
    df["age_months"] = df["age_upon_outcome"].apply(_age_to_months)
    df["outcome_datetime"] = df["outcome_datetime"].apply(_parse_dt)

    # NEW: normalize species and outcome_type to Title Case
    if "species" in df.columns:
        df["outcome_type"] = df["outcome_type"].apply(_normalize_outcome_type)
    if "outcome_type" in df.columns:
        df["outcome_type"] = df["outcome_type"].apply(_normalize_outcome_type)

    n_before = len(df)
    records, dropped = [], 0

    for rec in df.to_dict(orient="records"):
        if not rec.get("external_id"):
            dropped += 1
            continue
        try:
            validated = PetRow(
                external_id=str(rec["external_id"]).strip(),
                species=rec.get("species", ""),
                breed_name_raw=_none_if_nan(rec.get("breed_name_raw")),
                sex_upon_outcome=_none_if_nan(rec.get("sex_upon_outcome")),
                age_months=_int_or_none(rec.get("age_months")),
                color=_none_if_nan(rec.get("color")),
                outcome_type=_none_if_nan(rec.get("outcome_type")),
                outcome_datetime=rec.get("outcome_datetime"),
            )
            records.append(validated.model_dump())
        except Exception as e:
            dropped += 1
            log.warning("Dropped row for validation error: %s | %s", rec.get("external_id"), e)

    out_df = pd.DataFrame.from_records(records)

    # Enforce uniqueness by external_id (keep first)
    out_df = out_df.drop_duplicates(subset=["external_id"], keep="first")

    # Sort for determinism (species, then external_id)
    out_df = out_df.sort_values(by=["species", "external_id"], kind="stable")

    # NOTE: you had to_csv twice — keep it **once**
    config.pets_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(config.pets_clean_csv, index=False)

    log.info("Wrote pets_clean.csv: %s rows (dropped=%s of %s)", len(out_df), dropped, n_before)
    return config.pets_clean_csv