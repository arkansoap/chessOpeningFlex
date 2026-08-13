"""Persistence helpers for repertoires and lines."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Repertoire, RepertoireLine
from app.core.schemas import (
    RepertoireCreate,
    RepertoireLineCreate,
    RepertoireLineUpdate,
    RepertoireUpdate,
)


def list_repertoires(db: Session) -> list[Repertoire]:
    return list(db.scalars(select(Repertoire).order_by(Repertoire.name)))


def get_repertoire(db: Session, repertoire_id: str) -> Repertoire | None:
    return db.get(Repertoire, repertoire_id)


def create_repertoire(db: Session, data: RepertoireCreate) -> Repertoire:
    rep = Repertoire(
        name=data.name,
        color=data.color,
        description=data.description,
        is_active=data.is_active,
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return rep


def update_repertoire(
    db: Session, repertoire_id: str, data: RepertoireUpdate
) -> Repertoire | None:
    rep = db.get(Repertoire, repertoire_id)
    if rep is None:
        return None
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(rep, k, v)
    db.commit()
    db.refresh(rep)
    return rep


def delete_repertoire(db: Session, repertoire_id: str) -> bool:
    rep = db.get(Repertoire, repertoire_id)
    if rep is None:
        return False
    db.delete(rep)
    db.commit()
    return True


def list_lines(db: Session, repertoire_id: str) -> list[RepertoireLine]:
    return list(
        db.scalars(
            select(RepertoireLine)
            .where(RepertoireLine.repertoire_id == repertoire_id)
            .order_by(RepertoireLine.priority.desc(), RepertoireLine.depth)
        )
    )


def get_line(db: Session, line_id: str) -> RepertoireLine | None:
    return db.get(RepertoireLine, line_id)


def create_line(db: Session, data: RepertoireLineCreate) -> RepertoireLine:
    line = RepertoireLine(
        repertoire_id=data.repertoire_id,
        variant_id=data.variant_id,
        moves=data.moves,
        starting_position=data.starting_position,
        comment=data.comment,
        depth=data.depth,
        priority=data.priority,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def update_line(
    db: Session, line_id: str, data: RepertoireLineUpdate
) -> RepertoireLine | None:
    line = db.get(RepertoireLine, line_id)
    if line is None:
        return None
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(line, k, v)
    db.commit()
    db.refresh(line)
    return line


def delete_line(db: Session, line_id: str) -> bool:
    line = db.get(RepertoireLine, line_id)
    if line is None:
        return False
    db.delete(line)
    db.commit()
    return True
