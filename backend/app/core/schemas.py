"""Pydantic schemas for request/response validation."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# --- Common config ---------------------------------------------------------


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Enums mirrored from models (as plain str for API stability) ----------


# --- ImportedGame ---------------------------------------------------------


class ImportedGameBase(BaseModel):
    source: str
    chesscom_username: str | None = None
    pgn_file_path: str | None = None
    game_id: str
    white_player: str
    black_player: str
    result: str
    date: str | None = None
    eco_code: str | None = None
    pgn_data: str
    is_processed: bool = False


class ImportedGameCreate(ImportedGameBase):
    pass


class ImportedGameOut(ORMBase, ImportedGameBase):
    id: str


# --- GameVariant ----------------------------------------------------------


class GameVariantBase(BaseModel):
    moves: str
    starting_position: str = "startpos"
    evaluation: float | None = None
    is_valid: bool = True
    depth: int = 0


class GameVariantCreate(GameVariantBase):
    game_id: str


class GameVariantOut(ORMBase, GameVariantBase):
    id: str
    game_id: str


# --- Repertoire -----------------------------------------------------------


class RepertoireBase(BaseModel):
    name: str
    color: str
    description: str | None = None
    is_active: bool = True


class RepertoireCreate(RepertoireBase):
    pass


class RepertoireUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class RepertoireOut(ORMBase, RepertoireBase):
    id: str


class RepertoireDetailOut(RepertoireOut):
    lines: list["RepertoireLineOut"] = Field(default_factory=list)


# --- RepertoireLine -------------------------------------------------------


class RepertoireLineBase(BaseModel):
    moves: str
    starting_position: str = "startpos"
    comment: str | None = None
    depth: int = 0
    priority: int = 0


class RepertoireLineCreate(RepertoireLineBase):
    repertoire_id: str
    variant_id: str | None = None


class RepertoireLineUpdate(BaseModel):
    moves: str | None = None
    comment: str | None = None
    depth: int | None = None
    priority: int | None = None
    last_reviewed: str | None = None


class RepertoireLineOut(ORMBase, RepertoireLineBase):
    id: str
    repertoire_id: str
    variant_id: str | None = None
    last_reviewed: str | None = None


# --- Training -------------------------------------------------------------


class TrainingSessionBase(BaseModel):
    repertoire_id: str
    line_id: str
    mode: str
    date: str
    score: int | None = None
    total_questions: int = 0
    correct_answers: int = 0
    time_spent: int | None = None


class TrainingSessionCreate(TrainingSessionBase):
    pass


class TrainingSessionOut(ORMBase, TrainingSessionBase):
    id: str


class TrainingQuestionOut(BaseModel):
    """A single training question: a FEN position and the expected next move."""

    line_id: str
    fen: str
    expected_move: str  # SAN
    move_number: int
    color_to_move: str


class TrainingAnswerIn(BaseModel):
    line_id: str
    move_played: str  # SAN
    expected_move: str
    fen: str


class TrainingAnswerOut(BaseModel):
    is_correct: bool
    expected_move: str
    move_played: str


# --- chess.com import -----------------------------------------------------


class ChesscomImportIn(BaseModel):
    username: str
    time_control: str | None = None
    start_date: str | None = None  # YYYY-MM
    end_date: str | None = None  # YYYY-MM


# --- stats ----------------------------------------------------------------


class MemorizationStatOut(ORMBase):
    id: str
    line_id: str
    date: str
    success_rate: float
    attempts: int
    last_attempt: str | None = None


# Re-resolve forward references
RepertoireDetailOut.model_rebuild()


# --- Analysis -------------------------------------------------------------


class AnalyzeVariantsIn(BaseModel):
    pgn: str
    color: str = "white"  # which side's perspective to extract variants for
    min_depth: int = 0


class VariantExtractedOut(BaseModel):
    moves: str
    starting_position: str
    eco_code: str | None = None


class EvaluatePositionIn(BaseModel):
    fen: str
    depth: int | None = None


class EvaluatePositionOut(BaseModel):
    fen: str
    score: float  # centipawn score from white's perspective
    depth: int
    best_move: str | None = None
    mate: int | None = None


# helper for date.today() defaults kept out of schemas (controllers compute them)
__all__ = [
    "ORMBase",
    "ImportedGameBase",
    "ImportedGameCreate",
    "ImportedGameOut",
    "GameVariantBase",
    "GameVariantCreate",
    "GameVariantOut",
    "RepertoireBase",
    "RepertoireCreate",
    "RepertoireUpdate",
    "RepertoireOut",
    "RepertoireDetailOut",
    "RepertoireLineBase",
    "RepertoireLineCreate",
    "RepertoireLineUpdate",
    "RepertoireLineOut",
    "TrainingSessionBase",
    "TrainingSessionCreate",
    "TrainingSessionOut",
    "TrainingQuestionOut",
    "TrainingAnswerIn",
    "TrainingAnswerOut",
    "ChesscomImportIn",
    "MemorizationStatOut",
    "AnalyzeVariantsIn",
    "VariantExtractedOut",
    "EvaluatePositionIn",
    "EvaluatePositionOut",
]
