import sys
import os
import logging
from pathlib import Path
import argparse

# ------------------------
# Add project root to sys.path
# ------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ------------------------
# Imports
# ------------------------
from app.etl.config import ETLConfig, DB_PATH
from app.etl.outcomes import run as outcomes_run
from app.etl.breeds import run as breeds_run
from app.etl.seed import run as seed_run

# ------------------------
# Logging
# ------------------------
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s"
    )

# ------------------------
# Main ETL
# ------------------------
def main(force: bool = False):
    setup_logging()

    if DB_PATH.exists() and not force:
        logging.info(f"Database already exists at {DB_PATH}. Skipping ETL.")
        return

    logging.info(f"Running ETL. DB will be created at {DB_PATH}")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    cfg = ETLConfig()

    # Run ETL stages
    pets_csv = outcomes_run(cfg)
    breeds_csv = breeds_run(cfg)
    seed_run(cfg)

    logging.info("ETL completed successfully.")

# ------------------------
# Entry point
# ------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force ETL even if DB exists")
    args = parser.parse_args()

    main(force=args.force)