"""Pydantic schemas for request bodies.

Responses are plain dictionaries built by the services; their shape is
mirrored in `frontend/src/types`.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AccountsIn(BaseModel):
    chesscom: str | None = None
    lichess: str | None = None


class SyncIn(BaseModel):
    platforms: list[Literal["chesscom", "lichess"]] | None = None
    # On a first import, only go back this many months (None = everything).
    months: int | None = Field(None, ge=1, le=600)


class AnalysisRunIn(BaseModel):
    min_games: int = Field(2, ge=1, le=50)


class EvaluateIn(BaseModel):
    line: str | None = None
    fen: str | None = None
    depth: int | None = Field(None, ge=1, le=30)


class EntryIn(BaseModel):
    """The move I play in the position reached by `line` (or given by `fen`)."""

    line: str | None = None
    fen: str | None = None
    move: str
    comment: str | None = None
    source: str = "manual"


class EntryCommentIn(BaseModel):
    comment: str | None = None


class AdoptIn(BaseModel):
    min_games: int = Field(3, ge=1, le=100)
    min_share: float = Field(0.5, ge=0, le=1)
    max_loss: float = Field(5.0, ge=0, le=100)
    require_eval: bool = False
    dry_run: bool = True


class AnswerIn(BaseModel):
    entry_id: str
    move: str = ""
    reveal: bool = False
