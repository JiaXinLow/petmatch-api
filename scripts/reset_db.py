"""
Reset the local database to a clean state.

Usage:
  python -m scripts.reset_db
  python -m scripts.reset_db --yes
  python -m scripts.reset_db --seed
  python -m scripts.reset_db --force --yes  # allow non-SQLite with extra safety

Behavior:
- Defaults to DATABASE_URL or sqlite:///./petmatch.sqlite
- If SQLite file exists, delete it; else, drop & recreate tables.
- For non-SQLite URLs, requires --force to proceed (double confirmation by default).
- With --seed, runs scripts/seed.py after reset.
"""

import argparse
import os
import sys
from pathlib import Path
from subprocess import run

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Import your models & metadata
from app.models import Base

DEFAULT_URL = os.getenv("DATABASE_URL", "sqlite:///./petmatch.sqlite")


def is_sqlite(url: str) -> bool:
    return url.startswith("sqlite:///")

def sqlite_path_from_url(url: str) -> Path:
    # sqlite:///./file.sqlite -> ./file.sqlite
    # sqlite:////absolute/path.sqlite -> /absolute/path.sqlite
    raw = url.removeprefix("sqlite:///")
    return Path(raw)

def confirm(prompt: str) -> bool:
    try:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return ans in {"y", "yes"}

def drop_and_recreate(url: str) -> None:
    engine: Engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )
    # Drop & recreate metadata (works across engines)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def main():
    parser = argparse.ArgumentParser(description="Reset the database to a clean state.")
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation.")
    parser.add_argument("--seed", action="store_true", help="Seed after reset.")
    parser.add_argument(
        "--seed-mode",
        choices=["demo", "etl"],
        default="demo",
        help="Which seeder to run when --seed is provided: 'demo' (scripts/seed.py) or 'etl' (scripts/run_etl.py).",
    )
    parser.add_argument("--force", action="store_true", help="Allow non-SQLite URLs (with extra caution).")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"DB URL to reset (default: {DEFAULT_URL})")
    args = parser.parse_args()


    url = args.url
    print(f"[reset] Target DATABASE_URL: {url}")

    # Safety for non-SQLite
    if not is_sqlite(url):
        if not args.force:
            print("[reset] Refusing to operate on non-SQLite DB without --force.")
            sys.exit(2)
        # Double confirmation by default (unless --yes)
        if not args.yes:
            print("[reset] WARNING: This is NOT a SQLite URL. You are about to DROP ALL TABLES.")
            if not confirm("Proceed anyway?"):
                print("[reset] Aborted.")
                sys.exit(1)

        print("[reset] Dropping all tables on non-SQLite target...")
        drop_and_recreate(url)
        print("[reset] Done.")
    else:
        # SQLite: delete the file if present
        db_path = sqlite_path_from_url(url)
        # For sqlite:////absolute/... we may get leading slashes, normalize:
        db_path = Path(str(db_path))

        # Confirm unless --yes
        if not args.yes:
            msg = f"You are about to DELETE SQLite file: {db_path.resolve()}"
            print(f"[reset] {msg}")
            if not confirm("Proceed?"):
                print("[reset] Aborted.")
                sys.exit(1)

        if db_path.exists():
            try:
                db_path.unlink()
                print(f"[reset] Deleted file: {db_path}")
            except Exception as e:
                print(f"[reset] Failed to delete file: {e}")
                print("[reset] Falling back to drop & recreate tables.")
                drop_and_recreate(url)
        else:
            print(f"[reset] File does not exist, will drop & recreate metadata instead.")
            drop_and_recreate(url)

        # Ensure fresh schema exists for next run
        drop_and_recreate(url)
        print("[reset] Fresh schema created.")

    # Optional: seed
    if args.seed:
        print(f"[reset] Seeding mode: {args.seed_mode}")
        env = os.environ.copy()
        env["DATABASE_URL"] = url

        if args.seed_mode == "demo":
            print("[reset] Running demo seeder (scripts/seed.py)…")
            result = run([sys.executable, "-m", "scripts.seed"], env=env)
        else:
            print("[reset] Running ETL pipeline (scripts/run_etl.py)…")
            # This calls outcomes.run -> breeds.run -> app.etl.seed.run(cfg)
            result = run([sys.executable, "scripts/run_etl.py"], env=env)

        if result.returncode != 0:
            print("[reset] Seeding failed.")
            sys.exit(result.returncode)

        print("[reset] Seed complete.")

    print("[reset] Done.")


if __name__ == "__main__":
    main()