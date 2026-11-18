"""The tree of my games, position by position."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import game_filters
from app.core.database import get_db
from app.services import explorer, lichess_explorer
from app.services.chess_utils import InvalidLine, board_from
from app.services.explorer import GameFilters
from app.services.position_view import position_view

router = APIRouter(prefix="/explorer", tags=["explorer"])


@router.get("/position")
def get_position(
    line: str | None = Query(None, description="SAN moves from the start, space-separated"),
    fen: str | None = Query(None),
    filters: GameFilters = Depends(game_filters),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return position_view(db, filters, line, fen)
    except InvalidLine as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/openings")
def get_openings(
    filters: GameFilters = Depends(game_filters), db: Session = Depends(get_db)
) -> list[dict]:
    return explorer.openings_summary(db, filters)


@router.get("/lichess")
def get_lichess_stats(
    line: str | None = Query(None),
    fen: str | None = Query(None),
    rating: int = Query(1600, ge=0, le=3500, description="My approximate rating"),
    db: Session = Depends(get_db),
) -> dict:
    """What Lichess players around my level play in this position."""
    if not lichess_explorer.is_configured():
        return {"available": False, "reason": "Aucun jeton Lichess configuré sur le serveur."}
    try:
        board, _ = board_from(line, fen)
        data = lichess_explorer.fetch(db, board.fen(), lichess_explorer.bands_around(rating))
    except InvalidLine as exc:
        raise HTTPException(400, str(exc)) from exc
    except lichess_explorer.ExplorerUnavailable as exc:
        return {"available": False, "reason": str(exc)}
    return {"available": True, **data}
