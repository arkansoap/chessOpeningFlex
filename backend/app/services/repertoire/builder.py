"""Building repertoire lines from analyzed game variants."""
from __future__ import annotations

import chess

from app.services.analysis.variants import ExtractedVariant, split_moves


def build_line_from_variant(
    variant: ExtractedVariant,
    color: str,
    max_depth: int | None = None,
) -> dict:
    """Construct a repertoire-line-compatible dict from an extracted variant.

    The moves are trimmed to `max_depth` plies (full plies, both colors). The
    `starting_position` is taken from the variant.
    """
    moves = split_moves(variant.moves)
    if max_depth is not None and max_depth > 0:
        moves = moves[:max_depth]
    return {
        "moves": " ".join(moves),
        "starting_position": variant.starting_position,
        "depth": len(moves),
    }


def validate_line(moves_san: str, starting_position: str) -> bool:
    """Validate that a sequence of SAN moves is legal from the given FEN."""
    board = chess.Board(starting_position)
    for san in split_moves(moves_san):
        try:
            board.parse_san(san)
            board.push_san(san)
        except (chess.IllegalMoveError, chess.InvalidMoveError, ValueError):
            return False
    return True
