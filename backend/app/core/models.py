"""SQLAlchemy ORM models for the chess repertoire application."""
from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


class Color(str, Enum):
    WHITE = "white"
    BLACK = "black"


class GameSource(str, Enum):
    CHESS_COM_API = "chess_com_api"
    PGN_UPLOAD = "pgn_upload"


class TrainingMode(str, Enum):
    RANDOM = "random"
    SEQUENTIAL = "sequential"
    FULL_VARIATION = "full_variation"


class ImportedGame(Base):
    """A game imported from chess.com API or a PGN upload."""

    __tablename__ = "imported_games"

    id = Column(String, primary_key=True, default=_uuid)
    source = Column(String, nullable=False)
    chesscom_username = Column(String, nullable=True)
    pgn_file_path = Column(String, nullable=True)
    game_id = Column(String, nullable=False, index=True)
    white_player = Column(String, nullable=False)
    black_player = Column(String, nullable=False)
    result = Column(String, nullable=False)
    date = Column(String, nullable=True)
    eco_code = Column(String, nullable=True, index=True)
    pgn_data = Column(Text, nullable=False)
    is_processed = Column(Boolean, default=False, nullable=False)

    variants = relationship(
        "GameVariant", back_populates="game", cascade="all, delete-orphan"
    )


class GameVariant(Base):
    """A variant (move sequence) extracted from an imported game."""

    __tablename__ = "game_variants"

    id = Column(String, primary_key=True, default=_uuid)
    game_id = Column(String, ForeignKey("imported_games.id"), nullable=False, index=True)
    moves = Column(Text, nullable=False)
    starting_position = Column(String, nullable=False)
    evaluation = Column(Float, nullable=True)
    is_valid = Column(Boolean, default=True, nullable=False)
    depth = Column(Integer, nullable=False, default=0)

    game = relationship("ImportedGame", back_populates="variants")
    repertoire_lines = relationship(
        "RepertoireLine",
        back_populates="variant",
        cascade="all, delete-orphan",
    )


class Repertoire(Base):
    """A repertoire (white or black) grouping multiple lines."""

    __tablename__ = "repertoires"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    color = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    lines = relationship(
        "RepertoireLine",
        back_populates="repertoire",
        cascade="all, delete-orphan",
    )


class RepertoireLine(Base):
    """A line selected and cleaned for inclusion in a repertoire."""

    __tablename__ = "repertoire_lines"

    id = Column(String, primary_key=True, default=_uuid)
    repertoire_id = Column(
        String, ForeignKey("repertoires.id"), nullable=False, index=True
    )
    variant_id = Column(
        String, ForeignKey("game_variants.id"), nullable=True, index=True
    )
    moves = Column(Text, nullable=False)
    starting_position = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    depth = Column(Integer, nullable=False, default=0)
    priority = Column(Integer, default=0, nullable=False)
    last_reviewed = Column(String, nullable=True)

    repertoire = relationship("Repertoire", back_populates="lines")
    variant = relationship("GameVariant", back_populates="repertoire_lines")
    training_sessions = relationship(
        "TrainingSession",
        back_populates="line",
        cascade="all, delete-orphan",
    )


class TrainingSession(Base):
    """A single training session over one or more questions of a line."""

    __tablename__ = "training_sessions"

    id = Column(String, primary_key=True, default=_uuid)
    repertoire_id = Column(
        String, ForeignKey("repertoires.id"), nullable=False, index=True
    )
    line_id = Column(
        String, ForeignKey("repertoire_lines.id"), nullable=False, index=True
    )
    mode = Column(String, nullable=False)
    date = Column(String, nullable=False)
    score = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    time_spent = Column(Integer, nullable=True)

    repertoire = relationship("Repertoire")
    line = relationship("RepertoireLine", back_populates="training_sessions")


class MemorizationStat(Base):
    """Aggregated memorization statistics per line."""

    __tablename__ = "memorization_stats"

    id = Column(String, primary_key=True, default=_uuid)
    line_id = Column(
        String, ForeignKey("repertoire_lines.id"), nullable=False, index=True
    )
    date = Column(String, nullable=False)
    success_rate = Column(Float, nullable=False, default=0.0)
    attempts = Column(Integer, nullable=False, default=0)
    last_attempt = Column(String, nullable=True)

    line = relationship("RepertoireLine")
