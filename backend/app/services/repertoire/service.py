"""The repertoire: for each position where I am to move, the move I play."""
from __future__ import annotations

import chess
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import COLORS, Repertoire, RepertoireEntry, utcnow
from app.services import openings
from app.services.chess_utils import position_key

DEFAULT_NAMES = {"white": "Blancs", "black": "Noirs"}


class RepertoireError(ValueError):
    """Raised on a request the repertoire cannot honour."""


def get_repertoire(db: Session, color: str) -> Repertoire:
    """My repertoire for a colour, created on first use."""
    if color not in COLORS:
        raise RepertoireError(f"Couleur inconnue : {color}")
    rep = db.scalar(
        select(Repertoire).where(Repertoire.color == color).order_by(Repertoire.name)
    )
    if rep is None:
        rep = Repertoire(name=DEFAULT_NAMES[color], color=color)
        db.add(rep)
        db.flush()
    return rep


def entries_by_key(db: Session, rep: Repertoire) -> dict[str, RepertoireEntry]:
    return {
        e.position_key: e
        for e in db.scalars(
            select(RepertoireEntry).where(RepertoireEntry.repertoire_id == rep.id)
        )
    }


def moves_by_key(db: Session, color: str) -> dict[str, str]:
    """position key -> SAN of my repertoire move, for one colour."""
    rep = get_repertoire(db, color)
    return {key: entry.move_san for key, entry in entries_by_key(db, rep).items()}


def parse_move(board: chess.Board, move: str) -> chess.Move:
    """Accept SAN ("Nf3") or UCI ("g1f3")."""
    try:
        return board.parse_san(move)
    except ValueError:
        pass
    try:
        parsed = chess.Move.from_uci(move)
    except ValueError as exc:
        raise RepertoireError(f"Coup illisible : {move}") from exc
    if parsed not in board.legal_moves:
        raise RepertoireError(f"Coup illégal : {move}")
    return parsed


def upsert_entry(
    db: Session,
    color: str,
    board: chess.Board,
    line: list[str],
    move: str,
    comment: str | None = None,
    source: str = "manual",
    overwrite: bool = True,
) -> tuple[RepertoireEntry, bool]:
    """Set the move I play in a position. Returns (entry, changed).

    Changing the move of an existing entry resets what was memorised: it is a
    new thing to learn. The caller commits.
    """
    rep = get_repertoire(db, color)
    to_move = "white" if board.turn == chess.WHITE else "black"
    if to_move != color:
        raise RepertoireError(
            "Dans cette position c'est à l'adversaire de jouer : "
            "le répertoire ne contient que mes propres coups."
        )
    parsed = parse_move(board, move)
    san, uci = board.san(parsed), parsed.uci()
    key = position_key(board)
    entry = db.scalar(
        select(RepertoireEntry).where(
            RepertoireEntry.repertoire_id == rep.id, RepertoireEntry.position_key == key
        )
    )
    if entry is None:
        entry = RepertoireEntry(
            repertoire_id=rep.id,
            position_key=key,
            fen=board.fen(),
            line_san=" ".join(line),
            move_san=san,
            move_uci=uci,
            comment=comment,
            source=source,
        )
        db.add(entry)
        return entry, True
    changed = False
    if entry.move_uci != uci:
        if not overwrite:
            return entry, False
        entry.move_san, entry.move_uci = san, uci
        entry.source = source
        entry.srs_level, entry.due_at, entry.last_reviewed_at = 0, None, None
        changed = True
    if comment is not None and comment != (entry.comment or ""):
        entry.comment = comment or None
        changed = True
    if line and not entry.line_san:
        entry.line_san = " ".join(line)
    return entry, changed


def delete_entry(db: Session, entry_id: str) -> bool:
    entry = db.get(RepertoireEntry, entry_id)
    if entry is None:
        return False
    db.delete(entry)
    return True


def entry_dict(entry: RepertoireEntry, with_opening: bool = False) -> dict:
    data = {
        "id": entry.id,
        "key": entry.position_key,
        "fen": entry.fen,
        "line": entry.line_san.split() if entry.line_san else [],
        "move_san": entry.move_san,
        "move_uci": entry.move_uci,
        "comment": entry.comment,
        "source": entry.source,
        "srs_level": entry.srs_level,
        "due_at": entry.due_at.isoformat() if entry.due_at else None,
        "last_reviewed_at": entry.last_reviewed_at.isoformat() if entry.last_reviewed_at else None,
        "reviews": entry.reviews,
        "lapses": entry.lapses,
    }
    if with_opening:
        opening = openings.classify_line(data["line"] + [entry.move_san])
        data["opening"] = opening.name if opening else None
    return data


def list_entries(db: Session, color: str) -> list[dict]:
    """Every entry of a colour, in reading order (shallow lines first)."""
    rep = get_repertoire(db, color)
    entries = sorted(
        entries_by_key(db, rep).values(), key=lambda e: (len(e.line_san.split()), e.line_san)
    )
    return [entry_dict(e, with_opening=True) for e in entries]


def summary(db: Session, color: str) -> dict:
    """Size and training state of a repertoire."""
    rep = get_repertoire(db, color)
    entries = list(entries_by_key(db, rep).values())
    now = utcnow()
    levels: dict[int, int] = {}
    for entry in entries:
        levels[entry.srs_level] = levels.get(entry.srs_level, 0) + 1
    return {
        "color": color,
        "name": rep.name,
        "entries": len(entries),
        "new": sum(1 for e in entries if e.reviews == 0),
        "due": sum(1 for e in entries if e.reviews > 0 and (e.due_at is None or e.due_at <= now)),
        "levels": {str(level): count for level, count in sorted(levels.items())},
    }
