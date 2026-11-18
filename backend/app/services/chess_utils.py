"""Small chess helpers shared by the services."""
from __future__ import annotations

import math

import chess

START_KEY = chess.Board().epd()


def position_key(board: chess.Board) -> str:
    """Identity of a position, independent of the move order that led to it.

    This is the EPD: pieces, side to move, castling rights and the en-passant
    square only when a capture is actually possible. Two games reaching the
    same position by transposition get the same key.
    """
    return board.epd()


def turn_of_key(key: str) -> str:
    """Side to move in a position key: "white" or "black"."""
    return "white" if key.split(" ")[1] == "w" else "black"


def split_line(line: str | None) -> list[str]:
    """Split "1. e4 e5 2. Nf3" or "e4 e5 Nf3" into SAN moves."""
    if not line:
        return []
    moves: list[str] = []
    for token in line.replace(",", " ").split():
        token = token.split(".")[-1] if "." in token else token
        if token and token not in ("*", "1-0", "0-1", "1/2-1/2"):
            moves.append(token)
    return moves


class InvalidLine(ValueError):
    """Raised when a line or FEN cannot be played."""


def board_from(line: str | None = None, fen: str | None = None) -> tuple[chess.Board, list[str]]:
    """Build the board reached by `line` (from the start) or given by `fen`.

    Returns the board and the normalised SAN moves that were played.
    """
    if fen:
        try:
            return chess.Board(fen), []
        except ValueError as exc:
            raise InvalidLine(f"FEN invalide : {exc}") from exc
    board = chess.Board()
    played: list[str] = []
    for san in split_line(line):
        try:
            move = board.parse_san(san)
        except ValueError as exc:
            raise InvalidLine(f"Coup illégal « {san} » après {' '.join(played) or 'le départ'}") from exc
        played.append(board.san(move))
        board.push(move)
    return board, played


def win_percent(cp: int | None, mate: int | None) -> float:
    """Expected score (0-100) of the side the evaluation is given for.

    Same curve as Lichess, fitted on real games.
    """
    if mate is not None:
        return 100.0 if mate > 0 else 0.0
    if cp is None:
        return 50.0
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def numbered_line(sans: list[str]) -> str:
    """Render SAN moves with move numbers: "1. e4 e5 2. Nf3"."""
    parts: list[str] = []
    for i, san in enumerate(sans):
        if i % 2 == 0:
            parts.append(f"{i // 2 + 1}.")
        parts.append(san)
    return " ".join(parts)
