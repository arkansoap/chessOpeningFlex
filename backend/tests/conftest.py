"""Pytest configuration and fixtures."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.models import Account, Base
from app.main import app
from app.services.games.ingest import import_pgn_text


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    def override_get_db():
        yield db_session

    # The app's own startup would migrate the real database file.
    monkeypatch.setattr("app.main.run_migrations", lambda: None)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def pgn(white: str, black: str, result: str, moves: str, date: str = "2026.10.01",
        time_control: str = "600", white_elo: int = 1500, black_elo: int = 1500) -> str:
    return (
        f'[Event "Rated game"]\n[White "{white}"]\n[Black "{black}"]\n[Result "{result}"]\n'
        f'[Date "{date}"]\n[TimeControl "{time_control}"]\n'
        f'[WhiteElo "{white_elo}"]\n[BlackElo "{black_elo}"]\n\n{moves} {result}\n\n'
    )


# Four games of "me". A and C reach the same position by different move orders.
SAMPLE_PGN = (
    pgn("me", "ann", "1-0", "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6", date="2026.10.01")
    + pgn("me", "bob", "0-1", "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5", date="2026.10.02",
          time_control="180", black_elo=1700)
    + pgn("me", "cat", "1/2-1/2", "1. Nf3 Nc6 2. e4 e5 3. Bb5 Nf6", date="2026.10.03")
    + pgn("dan", "me", "0-1", "1. e4 c5 2. Nf3 d6", date="2026.10.04")
)


@pytest.fixture()
def sample_games(db_session):
    """Database holding my account and the four sample games."""
    db_session.add(Account(platform="chesscom", username="Me"))
    db_session.commit()
    import_pgn_text(db_session, SAMPLE_PGN)
    return db_session
