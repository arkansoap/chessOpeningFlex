"""Database session and engine setup."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# check_same_thread=False is required for SQLite when used with FastAPI's
# threaded request handling.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)

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
    import logging

    logger = logging.getLogger(__name__)
    try:
        from alembic import command
        from alembic.config import Config
        from pathlib import Path

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
