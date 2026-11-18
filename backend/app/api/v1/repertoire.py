"""Repertoire: entries, coverage, review of recent games, draft, PGN."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.v1.deps import ColorParam, game_filters
from app.core.database import get_db
from app.core.models import RepertoireEntry
from app.core.schemas import AdoptIn, EntryCommentIn, EntryIn
from app.services.chess_utils import InvalidLine, board_from
from app.services.explorer import GameFilters
from app.services.repertoire import adopt, coverage, pgn_io, service

router = APIRouter(prefix="/repertoire", tags=["repertoire"])


@router.get("/coverage")
def get_coverage(
    filters: GameFilters = Depends(game_filters), db: Session = Depends(get_db)
) -> dict:
    data = coverage.coverage(db, filters)
    db.commit()
    return data


@router.post("/adopt")
def adopt_from_games(
    payload: AdoptIn,
    filters: GameFilters = Depends(game_filters),
    db: Session = Depends(get_db),
) -> dict:
    """Draft a repertoire from my usual moves. `dry_run` only previews it."""
    params = payload.model_dump(exclude={"dry_run"})
    if payload.dry_run:
        data = adopt.propose(db, filters, **params)
        db.commit()
        return {**data, "added": 0}
    return adopt.apply(db, filters, **params)


@router.delete("/entry/{entry_id}", status_code=204)
def delete_entry(entry_id: str, db: Session = Depends(get_db)) -> Response:
    if not service.delete_entry(db, entry_id):
        raise HTTPException(404, "Coup introuvable dans le répertoire.")
    db.commit()
    return Response(status_code=204)


@router.patch("/entry/{entry_id}")
def update_comment(entry_id: str, payload: EntryCommentIn, db: Session = Depends(get_db)) -> dict:
    entry = db.get(RepertoireEntry, entry_id)
    if entry is None:
        raise HTTPException(404, "Coup introuvable dans le répertoire.")
    entry.comment = (payload.comment or "").strip() or None
    db.commit()
    return service.entry_dict(entry, with_opening=True)


@router.get("/{color}")
def get_repertoire(color: ColorParam, db: Session = Depends(get_db)) -> dict:
    data = {**service.summary(db, color), "items": service.list_entries(db, color)}
    db.commit()
    return data


@router.put("/{color}/entry")
def put_entry(color: ColorParam, payload: EntryIn, db: Session = Depends(get_db)) -> dict:
    """Choose (or change) the move I play in a position."""
    try:
        board, line = board_from(payload.line, payload.fen)
        entry, _changed = service.upsert_entry(
            db, color, board, line, payload.move, payload.comment, payload.source
        )
    except (InvalidLine, service.RepertoireError) as exc:
        raise HTTPException(400, str(exc)) from exc
    db.commit()
    return service.entry_dict(entry, with_opening=True)


@router.get("/{color}/review")
def get_review(
    color: ColorParam, limit: int = Query(30, ge=1, le=200), db: Session = Depends(get_db)
) -> list[dict]:
    data = coverage.review(db, color, limit)
    db.commit()
    return data


@router.get("/{color}/export.pgn")
def export_pgn(color: ColorParam, db: Session = Depends(get_db)) -> Response:
    text = pgn_io.export_pgn(db, color)
    db.commit()
    return Response(
        content=text,
        media_type="application/x-chess-pgn",
        headers={"Content-Disposition": f'attachment; filename="repertoire-{color}.pgn"'},
    )


@router.post("/{color}/import-pgn")
async def import_pgn(
    color: ColorParam,
    request: Request,
    overwrite: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict:
    raw = await request.body()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    if not text.strip():
        raise HTTPException(400, "Le PGN est vide.")
    try:
        return pgn_io.import_pgn(db, color, text, overwrite)
    except service.RepertoireError as exc:
        raise HTTPException(400, str(exc)) from exc
