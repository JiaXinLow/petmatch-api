import logging
import json
import pandas as pd
from pathlib import Path
from .config import ETLConfig

log = logging.getLogger(__name__)

def run(config: ETLConfig) -> Path:
    log.info("Reading dogbreeds JSON: %s", config.dogbreeds_json)
    with open(config.dogbreeds_json, encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, dict):
        raise ValueError("dogbreeds.json must be a JSON object (mapping name -> list of groups).")

    rows = []
    for name, groups in raw.items():
        if not isinstance(name, str):
            continue
        if not isinstance(groups, list):
            groups = []

        clean_name = name.strip()
        group_str = "; ".join([str(g).strip() for g in groups if str(g).strip()])

        rows.append({
            "species": "Dog",
            "name": clean_name,
            "group": group_str or None,
        })

    df = pd.DataFrame(rows)
    df["__key__"] = df["species"].str.lower() + "|" + df["name"].str.lower()
    before = len(df)
    df = df.drop_duplicates(subset=["__key__"]).drop(columns=["__key__"])
    after = len(df)
    log.info("Breed rows: %s (deduped from %s)", after, before)

    config.breeds_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.breeds_clean_csv, index=False)
    log.info("Wrote breeds_clean.csv to %s", config.breeds_clean_csv)

    return config.breeds_clean_csv