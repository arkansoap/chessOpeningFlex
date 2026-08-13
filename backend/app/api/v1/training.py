"""Training endpoints."""
from __future__ import annotations

import random

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import TrainingMode
from app.core.schemas import (
    MemorizationStatOut,
    TrainingAnswerIn,
    TrainingAnswerOut,
    TrainingQuestionOut,
    TrainingSessionOut,
)
from app.services.repertoire import storage
from app.services.training import stats as stats_service
from app.services.training.modes import generate_question, check_answer

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/session", response_model=TrainingSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    repertoire_id: str = Query(...),
    line_id: str = Query(...),
    mode: str = Query(TrainingMode.RANDOM.value),
    total_questions: int = Query(0, ge=0),
    correct_answers: int = Query(0, ge=0),
    time_spent: int | None = Query(None, ge=0),
    score: int | None = Query(None),
    db: Session = Depends(get_db),
) -> TrainingSessionOut:
    """Record a completed training session and update memorization stats."""
    line = storage.get_line(db, line_id)
    if line is None:
        raise HTTPException(status_code=404, detail="Line not found")
    session = stats_service.record_session(
        db=db,
        repertoire_id=repertoire_id,
        line_id=line_id,
        mode=mode,
        total_questions=total_questions,
        correct_answers=correct_answers,
        time_spent=time_spent,
        score=score,
    )
    return TrainingSessionOut.model_validate(session)


@router.get("/question", response_model=TrainingQuestionOut)
def get_question(
    line_id: str = Query(...),
    mode: str = Query(TrainingMode.RANDOM.value),
    step: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> TrainingQuestionOut:
    """Generate a training question for a given line and mode."""
    line = storage.get_line(db, line_id)
    if line is None:
        raise HTTPException(status_code=404, detail="Line not found")
    q = generate_question(
        mode=mode,
        moves_san=line.moves,
        starting_position=line.starting_position,
        line_id=line_id,
        step=step,
    )
    if q is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No question available for this line",
        )
    return TrainingQuestionOut(**q)


@router.post("/answer", response_model=TrainingAnswerOut)
def submit_answer(payload: TrainingAnswerIn) -> TrainingAnswerOut:
    """Check a submitted answer against the expected move."""
    correct = check_answer(
        fen=payload.fen,
        move_played=payload.move_played,
        expected_move=payload.expected_move,
    )
    return TrainingAnswerOut(
        is_correct=correct,
        expected_move=payload.expected_move,
        move_played=payload.move_played,
    )


@router.get("/stats", response_model=list[MemorizationStatOut])
def get_stats(
    repertoire_id: str | None = Query(None),
    line_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[MemorizationStatOut]:
    """Retrieve memorization stats, optionally filtered by repertoire or line."""
    if line_id:
        rows = stats_service.stats_for_line(db, line_id)
    elif repertoire_id:
        rows = stats_service.stats_for_repertoire(db, repertoire_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either repertoire_id or line_id",
        )
    return [MemorizationStatOut.model_validate(r) for r in rows]
