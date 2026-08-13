"""Parsing of uploaded PGN files into ImportedGame-compatible dicts."""
from __future__ import annotations

from pathlib import Path

import chess
import chess.pgn

from app.core.config import settings


class PgnParseError(Exception):
    """Raised when a PGN file cannot be parsed."""


def save_uploaded_pgn(filename: str, content: str) -> Path:
    """Persist an uploaded PGN to the raw data dir and return its path."""
    settings.raw_pgn_dir.mkdir(parents=True, exist_ok=True)
    # sanitize filename
    safe = "".join(c for c in filename if c.isalnum() or c in ("-", "_", "."))
    if not safe:
        safe = "upload.pgn"
    path = settings.raw_pgn_dir / safe
    path.write_text(content, encoding="utf-8")
    return path


def parse_pgn_file(path: str | Path) -> list[dict]:
    """Parse a multi-game PGN file into ImportedGame-compatible dicts."""
    path = Path(path)
    pgn_text = path.read_text(encoding="utf-8", errors="replace")
    return parse_pgn_string(pgn_text, pgn_file_path=str(path))


def parse_pgn_string(
    pgn_text: str, pgn_file_path: str | None = None
) -> list[dict]:
    """Parse a PGN string (possibly multiple games) into dicts."""
    import io

    out: list[dict] = []
    pgn_io = io.StringIO(pgn_text)
    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break
        headers = game.headers
        # re-export the game to a normalized PGN string
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        pgn_data = game.accept(exporter)

        out.append(
            {
                "source": "pgn_upload",
                "chesscom_username": None,
                "pgn_file_path": pgn_file_path,
                "game_id": str(game_id_hash(pgn_data)),
                "white_player": headers.get("White", "?"),
                "black_player": headers.get("Black", "?"),
                "result": headers.get("Result", "*"),
                "date": headers.get("UTCDate") or headers.get("Date"),
                "eco_code": headers.get("ECO"),
                "pgn_data": pgn_data,
                "is_processed": False,
            }
        )
    if not out:
        raise PgnParseError("No games found in PGN input")
    return out


def game_id_hash(pgn_data: str) -> int:
    """Stable-ish hash used as a fallback game id."""
    return abs(hash(pgn_data))
