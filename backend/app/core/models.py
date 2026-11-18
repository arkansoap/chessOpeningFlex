"""SQLAlchemy ORM models.

The app is built around positions rather than games or lines:

* every imported game is indexed ply by ply (`GamePly`), each ply carrying the
  key of the position it was played from, so that all games merge into one
  tree and transpositions meet;
* a repertoire is a map "position -> the move I play there"
  (`RepertoireEntry`). The opponent's replies are not stored: a reply is
  covered when the position it leads to has an entry.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()

WHITE = "white"
BLACK = "black"
COLORS = (WHITE, BLACK)


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Naive UTC timestamp: SQLite drops the timezone anyway."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Account(Base):
    """One of my accounts on a playing site; games are synced from it."""

    __tablename__ = "accounts"

    platform = Column(String, primary_key=True)  # "chesscom" | "lichess"
    username = Column(String, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    # Where the next sync resumes: last archive month for chess.com
    # ("YYYY/MM"), creation time in ms of the newest game for Lichess.
    sync_cursor = Column(String, nullable=True)


class Game(Base):
    """A game of mine, imported from chess.com, Lichess or a PGN file."""

    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_games_platform_external_id"),
        Index("ix_games_my_color_played_at", "my_color", "played_at"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    platform = Column(String, nullable=False)  # "chesscom" | "lichess" | "pgn"
    external_id = Column(String, nullable=False)
    url = Column(String, nullable=True)
    white = Column(String, nullable=False)
    black = Column(String, nullable=False)
    white_elo = Column(Integer, nullable=True)
    black_elo = Column(Integer, nullable=True)
    result = Column(String, nullable=False)  # "1-0" | "0-1" | "1/2-1/2" | "*"
    # Which side I played and how it went, None when I am not in the game.
    my_color = Column(String, nullable=True)
    my_result = Column(String, nullable=True)  # "win" | "draw" | "loss"
    opponent = Column(String, nullable=True)
    opponent_elo = Column(Integer, nullable=True)
    time_class = Column(String, nullable=True)  # bullet|blitz|rapid|classical|daily
    rated = Column(Boolean, nullable=True)
    played_at = Column(DateTime, nullable=True)
    eco = Column(String, nullable=True)
    opening_name = Column(String, nullable=True)
    moves_san = Column(Text, nullable=False, default="")
    ply_count = Column(Integer, nullable=False, default=0)
    imported_at = Column(DateTime, nullable=False, default=utcnow)

    plies = relationship("GamePly", back_populates="game", cascade="all, delete-orphan")


class GamePly(Base):
    """One of the first plies of a game, keyed by the position it starts from."""

    __tablename__ = "game_plies"
    __table_args__ = (Index("ix_game_plies_key_before", "key_before"),)

    game_id = Column(String, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True)
    ply = Column(Integer, primary_key=True)  # 0 = White's first move
    key_before = Column(String, nullable=False)
    key_after = Column(String, nullable=False)
    san = Column(String, nullable=False)
    uci = Column(String, nullable=False)

    game = relationship("Game", back_populates="plies")


class PositionEval(Base):
    """Cached engine evaluation of a position, from the side to move."""

    __tablename__ = "position_evals"

    key = Column(String, primary_key=True)
    depth = Column(Integer, nullable=False)
    cp = Column(Integer, nullable=True)
    mate = Column(Integer, nullable=True)
    best_uci = Column(String, nullable=True)
    best_san = Column(String, nullable=True)
    pv_san = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utcnow)


class Repertoire(Base):
    """My repertoire for one colour."""

    __tablename__ = "repertoires"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    color = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    entries = relationship(
        "RepertoireEntry", back_populates="repertoire", cascade="all, delete-orphan"
    )


class RepertoireEntry(Base):
    """The move I play in one position, with its spaced-repetition state."""

    __tablename__ = "repertoire_entries"
    __table_args__ = (
        UniqueConstraint("repertoire_id", "position_key", name="uq_entries_repertoire_position"),
        Index("ix_entries_due_at", "due_at"),
    )

    id = Column(String, primary_key=True, default=_uuid)
    repertoire_id = Column(
        String, ForeignKey("repertoires.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position_key = Column(String, nullable=False)
    fen = Column(String, nullable=False)
    # One move order reaching the position, for display and opening naming.
    line_san = Column(Text, nullable=False, default="")
    move_san = Column(String, nullable=False)
    move_uci = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    source = Column(String, nullable=False, default="manual")
    created_at = Column(DateTime, nullable=False, default=utcnow)

    # Spaced repetition. Level 0 = never learned (or just failed).
    srs_level = Column(Integer, nullable=False, default=0)
    due_at = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    reviews = Column(Integer, nullable=False, default=0)
    lapses = Column(Integer, nullable=False, default=0)

    repertoire = relationship("Repertoire", back_populates="entries")


class ReviewLog(Base):
    """One answer given in training, kept for the progress statistics."""

    __tablename__ = "review_logs"

    id = Column(String, primary_key=True, default=_uuid)
    entry_id = Column(String, nullable=False, index=True)
    color = Column(String, nullable=False)
    reviewed_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    correct = Column(Boolean, nullable=False)


class ExplorerCache(Base):
    """Cached response of the Lichess opening explorer."""

    __tablename__ = "explorer_cache"

    cache_key = Column(String, primary_key=True)
    payload = Column(Text, nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=utcnow)
