"""Analysis endpoints (variant extraction + Stockfish evaluation)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.schemas import (
    AnalyzeVariantsIn,
    EvaluatePositionIn,
    EvaluatePositionOut,
    VariantExtractedOut,
)
from app.services.analysis.engine import engine_service
from app.services.analysis.variants import extract_variants

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/variants", response_model=list[VariantExtractedOut])
def analyze_variants(payload: AnalyzeVariantsIn) -> list[VariantExtractedOut]:
    """Extract variants from a PGN string."""
    variants = extract_variants(payload.pgn, color=payload.color, min_depth=payload.min_depth)
    return [
        VariantExtractedOut(
            moves=v.moves,
            starting_position=v.starting_position,
            eco_code=v.eco_code,
        )
        for v in variants
    ]


@router.post("/evaluate", response_model=EvaluatePositionOut)
def evaluate_position(payload: EvaluatePositionIn) -> EvaluatePositionOut:
    """Evaluate a FEN position with Stockfish (best-effort)."""
    result = engine_service.evaluate(payload.fen, depth=payload.depth)
    if not result.get("available", True) and payload.depth is not None:
        # Engine disabled: still return a valid response but flag it.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stockfish engine is not available in this environment",
        )
    return EvaluatePositionOut(
        fen=result["fen"],
        score=result["score"],
        depth=result["depth"],
        best_move=result.get("best_move"),
        mate=result.get("mate"),
    )
