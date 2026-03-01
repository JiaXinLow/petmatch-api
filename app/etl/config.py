from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

PROJ_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJ_ROOT / "data" / "raw"
DATA_PROCESSED = PROJ_ROOT / "data" / "processed"

class ETLConfig(BaseModel):
    outcomes_csv: Path = Path(os.getenv("OUTCOMES_CSV") or DATA_RAW / "Austin_Animal_Center_Outcomes.csv")
    dogbreeds_json: Path = Path(os.getenv("DOGBREEDS_JSON") or DATA_RAW / "dogbreeds.json")
    pets_clean_csv: Path = Path(os.getenv("PETS_CLEAN_CSV") or DATA_PROCESSED / "pets_clean.csv")
    breeds_clean_csv: Path = Path(os.getenv("BREEDS_CLEAN_CSV") or DATA_PROCESSED / "breeds_clean.csv")