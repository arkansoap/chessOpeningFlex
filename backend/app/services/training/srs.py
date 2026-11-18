"""Spaced repetition over the repertoire, one position at a time.

Each entry ("in this position I play that move") has its own level. A correct
answer moves it one level up and pushes the next review further away; a wrong
one sends it back to the start. Intervals follow the usual ladder of
opening trainers: 4 h, 1 d, 3 d, 1 w, 2 w, 1 month, 3 months, 6 months.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import chess
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.models import COLORS, Repertoire, RepertoireEntry, ReviewLog, utcnow
from app.services.repertoire.service import entry_dict

INTERVALS = [
    timedelta(0),  # level 0: to learn
    timedelta(hours=4),
    timedelta(days=1),
    timedelta(days=3),
    timedelta(days=7),
    timedelta(days=14),
    timedelta(days=30),
    timedelta(days=90),
    timedelta(days=180),
]
MAX_LEVEL = len(INTERVALS) - 1


def _entries(db: Session, color: str | None) -> list[tuple[RepertoireEntry, str]]:
    stmt = select(RepertoireEntry, Repertoire.color).join(
        Repertoire, Repertoire.id == RepertoireEntry.repertoire_id
    )
    if color in COLORS:
        stmt = stmt.where(Repertoire.color == color)
    return [(entry, entry_color) for entry, entry_color in db.execute(stmt)]


def _is_due(entry: RepertoireEntry, now: datetime) -> bool:
    return entry.due_at is None or entry.due_at <= now


def queue(db: Session, color: str | None, mode: str = "due") -> list[tuple[RepertoireEntry, str]]:
    """Entries to ask, in order.

    "due": reviews that are due first (oldest first), then new moves starting
    with the shallowest, so that a line is learned from its root.
    "all": everything, least recently seen first.
    """
    now = utcnow()
    items = _entries(db, color)
    if mode == "all":
        return sorted(items, key=lambda it: (it[0].last_reviewed_at or datetime.min, len(it[0].line_san)))
    due = [it for it in items if _is_due(it[0], now)]
    return sorted(
        due,
        key=lambda it: (
            it[0].reviews == 0 and it[0].lapses == 0,  # reviews and misses before new moves
            it[0].due_at or datetime.min,
            len(it[0].line_san.split()),
        ),
    )


def next_question(db: Session, color: str | None, mode: str = "due", exclude: str | None = None) -> dict:
    items = queue(db, color, mode)
    remaining = len(items)
    candidates = [it for it in items if it[0].id != exclude] or items
    if not candidates:
        return {"question": None, "remaining": 0}
    entry, entry_color = candidates[0]
    line = entry.line_san.split() if entry.line_san else []
    return {
        "remaining": remaining,
        "question": {
            "entry_id": entry.id,
            "color": entry_color,
            "fen": entry.fen,
            "line": line,
            "srs_level": entry.srs_level,
            "is_new": entry.reviews == 0,
        },
    }


def answer(db: Session, entry_id: str, move: str, reveal: bool = False) -> dict | None:
    """Check an answer and reschedule the entry. Commits.

    `reveal` records a failure without a move ("show me the answer").
    """
    row = db.execute(
        select(RepertoireEntry, Repertoire.color)
        .join(Repertoire, Repertoire.id == RepertoireEntry.repertoire_id)
        .where(RepertoireEntry.id == entry_id)
    ).first()
    if row is None:
        return None
    entry, color = row
    correct = False
    if not reveal:
        board = chess.Board(entry.fen)
        try:
            played = board.parse_san(move)
        except ValueError:
            try:
                played = chess.Move.from_uci(move)
            except ValueError:
                played = None
        correct = played is not None and played.uci() == entry.move_uci

    now = utcnow()
    if correct:
        entry.srs_level = min(entry.srs_level + 1, MAX_LEVEL)
        entry.due_at = now + INTERVALS[entry.srs_level]
    else:
        entry.srs_level = 0
        entry.due_at = now
        entry.lapses += 1
    entry.reviews += 1
    entry.last_reviewed_at = now
    db.add(ReviewLog(entry_id=entry.id, color=color, correct=correct, reviewed_at=now))
    db.commit()
    return {"correct": correct, "entry": entry_dict(entry, with_opening=True)}


def stats(db: Session, days: int = 30) -> dict:
    """Training activity over the last days and state of each repertoire."""
    since = utcnow() - timedelta(days=days)
    day = func.date(ReviewLog.reviewed_at)
    rows = db.execute(
        select(
            day,
            func.count(ReviewLog.id),
            func.sum(case((ReviewLog.correct.is_(True), 1), else_=0)),
        )
        .where(ReviewLog.reviewed_at >= since)
        .group_by(day)
        .order_by(day)
    ).all()
    now = utcnow()
    per_color = {}
    for color in COLORS:
        entries = [e for e, _ in _entries(db, color)]
        per_color[color] = {
            "entries": len(entries),
            "new": sum(1 for e in entries if e.reviews == 0),
            "due": sum(1 for e in entries if e.reviews > 0 and _is_due(e, now)),
            "learned": sum(1 for e in entries if e.srs_level >= 4),
        }
    return {
        "days": [
            {"date": str(d), "reviews": total, "correct": int(correct or 0)}
            for d, total, correct in rows
        ],
        "colors": per_color,
    }

