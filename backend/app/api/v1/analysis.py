"""Engine analysis: batch job over my games, leaks, single positions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import game_filters
from app.core.config import settings
from app.core.database import get_db
from app.core.schemas import AnalysisRunIn, EvaluateIn
from app.services import jobs
from app.services.analysis import leaks
from app.services.analysis.engine import EngineUnavailable, engine_service, evaluate
from app.services.chess_utils import InvalidLine, board_from
from app.services.explorer import GameFilters
from app.services.position_view import white_pov
from app.services.repertoire.service import moves_by_key

router = APIRouter(tags=["analysis"])


@router.get("/analysis/status")
def analysis_status(
    min_games: int = Query(2, ge=1, le=50), db: Session = Depends(get_db)
) -> dict:
    pending, total = leaks.pending_targets(db, min_games)
    return {
        "engine_available": engine_service.available,
        "depth": settings.analysis_depth,
        "total": total,
        "pending": len(pending),
        "job": jobs.get("analysis").as_dict(),
    }


@router.post("/analysis/run")
def run_analysis(payload: AnalysisRunIn) -> dict:
    if not engine_service.available:
        raise HTTPException(
            503, "Stockfish n'est pas installé sur le serveur (voir le README, section Moteur)."
        )
    state, _started = leaks.start_analysis(payload.min_games)
    return state.as_dict()


@router.post("/analysis/stop")
def stop_analysis() -> dict:
    return jobs.request_stop("analysis").as_dict()


@router.post("/analysis/evaluate")
def evaluate_position(payload: EvaluateIn, db: Session = Depends(get_db)) -> dict:
    """Evaluate one position on the server (cached). Score from White's side."""
    try:
        board, _ = board_from(payload.line, payload.fen)
    except InvalidLine as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        row = evaluate(db, board, payload.depth)
    except EngineUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    db.commit()
    return {**white_pov(row), "best_san": row.best_san, "best_uci": row.best_uci,
            "pv_san": row.pv_san}


@router.get("/leaks")
def get_leaks(
    min_games: int = Query(2, ge=1, le=50),
    min_loss: float = Query(leaks.INACCURACY, ge=0, le=100),
    limit: int = Query(100, ge=1, le=500),
    filters: GameFilters = Depends(game_filters),
    db: Session = Depends(get_db),
) -> dict:
    found = leaks.find_leaks(
        db, filters, min_games, min_loss, moves_by_key(db, filters.color)
    )
    db.commit()  # the repertoire row may have just been created
    return {"total": len(found), "leaks": found[:limit]}
