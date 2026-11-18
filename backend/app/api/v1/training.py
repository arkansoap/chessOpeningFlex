"""Training: spaced repetition over the repertoire."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.schemas import AnswerIn
from app.services.training import srs

router = APIRouter(prefix="/training", tags=["training"])


@router.get("/next")
def next_question(
    color: Literal["white", "black", "any"] = Query("any"),
    mode: Literal["due", "all"] = Query("due"),
    exclude: str | None = Query(None, description="Entry just asked, not to repeat at once"),
    db: Session = Depends(get_db),
) -> dict:
    return srs.next_question(db, None if color == "any" else color, mode, exclude)


@router.post("/answer")
def submit_answer(payload: AnswerIn, db: Session = Depends(get_db)) -> dict:
    result = srs.answer(db, payload.entry_id, payload.move, payload.reveal)
    if result is None:
        raise HTTPException(404, "Ce coup n'est plus dans le répertoire.")
    return result


@router.get("/stats")
def training_stats(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)) -> dict:
    return srs.stats(db, days)
