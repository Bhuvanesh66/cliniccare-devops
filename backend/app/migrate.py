"""Apply database migrations (and optionally seed demo data), then exit.

Runs as the docker compose `migrate` service and as the Kubernetes init
container, so the API process itself never changes the schema. A PostgreSQL
advisory lock makes it safe when several backend pods start at the same time.

    python -m app.migrate
"""

import logging
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .config import settings
from .db import SessionLocal, engine
from .seed import seed_demo_data

log = logging.getLogger("cliniccare.migrate")

BACKEND_DIR = Path(__file__).resolve().parent.parent
MIGRATION_LOCK_ID = 20261015


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def wait_for_database(timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError as exc:
            if time.monotonic() >= deadline:
                raise
            log.info("database not reachable yet (%s), retrying in 2s", type(exc.orig).__name__)
            time.sleep(2)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    wait_for_database(settings.migration_wait_seconds)

    with engine.connect() as lock_connection:
        use_lock = engine.dialect.name == "postgresql"
        if use_lock:
            log.info("waiting for migration lock")
            lock_connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
        try:
            command.upgrade(alembic_config(), "head")
            if settings.seed_demo_data:
                with SessionLocal() as db:
                    seed_demo_data(db)
        finally:
            if use_lock:
                lock_connection.execute(
                    text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK_ID}
                )
    log.info("database is up to date")


if __name__ == "__main__":
    main()
