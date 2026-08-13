"""Memorization statistics computation and persistence."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import MemorizationStat, RepertoireLine, TrainingSession


def record_session(
    db: Session,
    repertoire_id: str,
    line_id: str,
    mode: str,
    total_questions: int,
    correct_answers: int,
    time_spent: int | None = None,
    score: int | None = None,
) -> TrainingSession:
    """Persist a training session and update the line's memorization stats."""
    today = date.today().isoformat()
    session = TrainingSession(
        repertoire_id=repertoire_id,
        line_id=line_id,
        mode=mode,
        date=today,
        score=score,
        total_questions=total_questions,
        correct_answers=correct_answers,
        time_spent=time_spent,
    )
    db.add(session)

    stat = db.scalar(
        select(MemorizationStat).where(
            MemorizationStat.line_id == line_id,
            MemorizationStat.date == today,
        )
    )
    attempts = total_questions
    correct = correct_answers
    success_rate = (correct / attempts) if attempts else 0.0
    if stat is None:
        stat = MemorizationStat(
            line_id=line_id,
            date=today,
            success_rate=success_rate,
            attempts=attempts,
            last_attempt=today,
        )
        db.add(stat)
    else:
        prev_attempts = stat.attempts or 0
        prev_correct = round(stat.success_rate * prev_attempts)
        new_attempts = prev_attempts + attempts
        new_correct = prev_correct + correct
        stat.attempts = new_attempts
        stat.success_rate = (new_correct / new_attempts) if new_attempts else 0.0
        stat.last_attempt = today

    # mark line as reviewed
    line = db.get(RepertoireLine, line_id)
    if line is not None:
        line.last_reviewed = today

    db.commit()
    db.refresh(session)
    return session


def stats_for_repertoire(db: Session, repertoire_id: str) -> list[MemorizationStat]:
    """Return memorization stats for all lines in a repertoire."""
    return list(
        db.scalars(
            select(MemorizationStat)
            .join(RepertoireLine, RepertoireLine.id == MemorizationStat.line_id)
            .where(RepertoireLine.repertoire_id == repertoire_id)
            .order_by(MemorizationStat.date.desc())
        )
    )


def stats_for_line(db: Session, line_id: str) -> list[MemorizationStat]:
    return list(
        db.scalars(
            select(MemorizationStat)
            .where(MemorizationStat.line_id == line_id)
            .order_by(MemorizationStat.date.desc())
        )
    )
