"""chess.com import endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import ImportedGame
from app.core.schemas import (
    ChesscomImportIn,
    ImportedGameOut,
    ImportedGameCreate,
)
from app.services.chesscom.api import (
    ChesscomClient,
    ChesscomError,
    build_imported_game_dicts,
)
from app.services.chesscom.pgn import PgnParseError, parse_pgn_string, save_uploaded_pgn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chesscom", tags=["chesscom"])


@router.post(
    "/import",
    response_model=list[ImportedGameOut],
    status_code=status.HTTP_201_CREATED,
)
def import_from_chesscom(
    payload: ChesscomImportIn, db: Session = Depends(get_db)
) -> list[ImportedGameOut]:
    """Import games from the chess.com public API."""
    client = ChesscomClient()
    try:
        raw_games = client.fetch_games(
            username=payload.username,
            time_control=payload.time_control,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
    except ChesscomError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    dicts = build_imported_game_dicts(payload.username, raw_games)
    created: list[ImportedGame] = []
    for d in dicts:
        game = ImportedGame(**ImportedGameCreate(**d).model_dump())
        db.add(game)
        created.append(game)
    db.commit()
    for g in created:
        db.refresh(g)
    return [ImportedGameOut.model_validate(g) for g in created]


@router.post(
    "/upload-pgn",
    response_model=list[ImportedGameOut],
    status_code=status.HTTP_201_CREATED,
)
async def upload_pgn(body: str = "", db: Session = Depends(get_db)) -> list[ImportedGameOut]:
    """Upload a raw PGN string and import the games it contains."""
    if not body or not body.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty PGN body",
        )
    path = save_uploaded_pgn("upload.pgn", body)
    try:
        dicts = parse_pgn_string(body, pgn_file_path=str(path))
    except PgnParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    created: list[ImportedGame] = []
    for d in dicts:
        game = ImportedGame(**ImportedGameCreate(**d).model_dump())
        db.add(game)
        created.append(game)
    db.commit()
    for g in created:
        db.refresh(g)
    return [ImportedGameOut.model_validate(g) for g in created]
