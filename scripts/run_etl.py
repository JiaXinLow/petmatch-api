import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.etl.config import ETLConfig
from app.etl.outcomes import run as outcomes_run
from app.etl.breeds import run as breeds_run
from app.etl.seed import run as seed_run

import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s"
    )

def main():
    setup_logging()
    cfg = ETLConfig()

    pets_csv = outcomes_run(cfg)
    breeds_csv = breeds_run(cfg)

    seed_run(cfg)

if __name__ == "__main__":
    main()