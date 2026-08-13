"""Extracting move variants from PGN games."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

import chess
import chess.pgn


@dataclass
class ExtractedVariant:
    moves: str  # SAN moves, e.g. "1. e4 e5 2. Nf3"
    starting_position: str  # FEN
    eco_code: str | None = None


def _normalize_pgn(pgn: str) -> str:
    """Ensure a blank line separates PGN headers from the movetext.

    python-chess requires a blank line between the header section and the
    movetext; some compact PGN strings omit it, which causes the moves to be
    silently dropped. Handles both multi-line and single-line inputs where
    headers and movetext share one line.
    """
    text = pgn.strip()
    if not text:
        return pgn
    # Single-line case: headers + movetext on one line.
    if "\n" not in text:
        # Find the last ']' that closes the header section, followed by
        # whitespace and the first movetext token (not '[').
        m = re.search(r"\](\s+)([^\[\s].*)$", text)
        if m:
            headers = text[: m.start() + 1]
            movetext = m.group(2)
            return headers + "\n\n" + movetext
    # Multi-line case: insert a blank line if missing.
    lines = pgn.splitlines()
    if not lines:
        return pgn
    last_header_idx = -1
    for i, ln in enumerate(lines):
        if ln.strip().startswith("["):
            last_header_idx = i
    if last_header_idx >= 0 and last_header_idx + 1 < len(lines):
        nxt = lines[last_header_idx + 1].strip()
        if nxt and not nxt.startswith("["):
            out = lines[: last_header_idx + 1] + [""] + lines[last_header_idx + 1:]
            return "\n".join(out)
    return pgn


def extract_variants(pgn: str, color: str = "white", min_depth: int = 0) -> list[ExtractedVariant]:
    """Extract the mainline move sequence of the game from the given player's
    perspective, up to and including their moves.

    The extracted `moves` string is the SAN of the full line played, and the
    `starting_position` is the standard initial position FEN.

    Only one variant per game is extracted (the played mainline). Variations
    embedded in the PGN are not traversed in this MVP.
    """
    game = chess.pgn.read_game(io.StringIO(_normalize_pgn(pgn)))
    if game is None:
        return []

    board = game.board()
    san_moves: list[str] = []
    node = game
    while node.variations:
        node = node.variation(0)
        san = board.san_and_push(node.move)
        san_moves.append(san)

    if len(san_moves) < min_depth:
        return []

    eco = game.headers.get("ECO")
    initial = chess.Board().fen()
    return [ExtractedVariant(moves=" ".join(san_moves), starting_position=initial, eco_code=eco)]


def split_moves(moves_san: str) -> list[str]:
    """Split a SAN move string like '1. e4 e5 2. Nf3' into ['e4','e5','Nf3']."""
    tokens = moves_san.split()
    return [t for t in tokens if not t.endswith(".")]
