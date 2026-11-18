"""Database session and engine setup."""
from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

IS_SQLITE = settings.database_url.startswith("sqlite")

# check_same_thread=False is required for SQLite when used with FastAPI's
# threaded request handling and with the background import/analysis jobs.
connect_args = {"check_same_thread": False, "timeout": 30} if IS_SQLITE else {}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)

if IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record) -> None:
        # WAL lets the pages keep reading while a background job writes.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    """Apply pending Alembic migrations to the configured database.

    Falls back to creating tables directly via Base.metadata.create_all when
    Alembic is not importable (e.g. stripped-down environments). This keeps the
    app runnable in both production (migrations) and minimal dev setups.
    """
    try:
        from alembic import command
        from alembic.config import Config

        # Locate alembic.ini next to the backend package root.
        cfg_path = Path(__file__).resolve().parents[2] / "alembic.ini"
        if not cfg_path.exists():
            raise FileNotFoundError(cfg_path)
        cfg = Config(str(cfg_path))
        cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(cfg, "head")
        logger.info("Alembic migrations applied to head")
    except Exception as exc:  # pragma: no cover - env dependent
        logger.warning("Alembic migration failed (%s); using create_all fallback", exc)
        from app.core.models import Base

        Base.metadata.create_all(bind=engine)
