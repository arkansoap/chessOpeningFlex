"""Everything known about one position, assembled for the explorer screen."""
from __future__ import annotations

import chess
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import PositionEval
from app.services import openings
from app.services.analysis.leaks import move_loss, severity, INACCURACY
from app.services.chess_utils import board_from, position_key, turn_of_key
from app.services.explorer import GameFilters, games_through, moves_from
from app.services.repertoire.service import entries_by_key, entry_dict, get_repertoire


def white_pov(row: PositionEval | None) -> dict | None:
    """Evaluation as chess players read it: positive is good for White."""
    if row is None:
        return None
    sign = 1 if turn_of_key(row.key) == "white" else -1
    return {
        "cp": sign * row.cp if row.cp is not None else None,
        "mate": sign * row.mate if row.mate is not None else None,
        "depth": row.depth,
    }


def position_view(
    db: Session,
    filters: GameFilters,
    line: str | None = None,
    fen: str | None = None,
    recent_games: int = 8,
) -> dict:
    board, sans = board_from(line, fen)
    key = position_key(board)
    color = filters.color
    my_turn = (board.turn == chess.WHITE) == (color == "white")

    edges = moves_from(db, key, filters)
    entries = entries_by_key(db, get_repertoire(db, color))
    entry = entries.get(key) if my_turn else None

    # Positions one move away: every legal move, so that repertoire moves and
    # covered replies show up even when no game of mine went there.
    after: dict[str, tuple[str, str]] = {}
    for move in board.legal_moves:
        san = board.san(move)
        board.push(move)
        after[move.uci()] = (san, position_key(board))
        board.pop()

    wanted = {key, *(k for _, k in after.values())}
    evals = {
        row.key: row
        for row in db.scalars(select(PositionEval).where(PositionEval.key.in_(wanted)))
    }
    here = evals.get(key)

    rows: dict[str, dict] = {}
    for edge in edges:
        rows[edge.uci] = edge.as_dict()

    def ensure(uci: str) -> dict:
        if uci not in rows:
            san, key_after = after[uci]
            rows[uci] = {"san": san, "uci": uci, "key_after": key_after, "games": 0,
                         "wins": 0, "draws": 0, "losses": 0, "score": 0.0, "last_played": None}
        return rows[uci]

    if my_turn:
        if entry is not None and entry.move_uci in after:
            ensure(entry.move_uci)
        if here is not None and here.best_uci in after:
            ensure(here.best_uci)
    else:
        for uci, (_, key_after) in after.items():
            if key_after in entries:
                ensure(uci)

    moves = []
    for uci, row in rows.items():
        child = evals.get(row["key_after"])
        row["eval"] = white_pov(child)
        if my_turn:
            row["is_repertoire"] = entry is not None and entry.move_uci == uci
            row["is_best"] = here is not None and here.best_uci == uci
            cost = move_loss(here, child)
            row["loss"] = cost["loss"] if cost else None
            row["severity"] = (
                severity(cost["loss"]) if cost and cost["loss"] >= INACCURACY else None
            )
        else:
            row["covered"] = row["key_after"] in entries
            answer = entries.get(row["key_after"])
            row["answer"] = answer.move_san if answer else None
        moves.append(row)
    moves.sort(key=lambda r: (-r["games"], not r.get("is_repertoire", False), r["san"]))

    # The move that led here, when it was mine: the screen offers to make it
    # my repertoire move, which is how a move I never played gets in.
    last_move = None
    if sans and not my_turn and board.move_stack:
        played = board.pop()
        previous = entries.get(position_key(board))
        last_move = {
            "san": sans[-1],
            "uci": played.uci(),
            "is_repertoire": previous is not None and previous.move_uci == played.uci(),
            "repertoire_move": previous.move_san if previous else None,
        }
        board.push(played)

    opening = openings.classify_line(sans) if sans else openings.lookup(key)
    total = sum(e.games for e in edges)
    wins, draws, losses = (sum(getattr(e, f) for e in edges) for f in ("wins", "draws", "losses"))
    decided = wins + draws + losses
    return {
        "key": key,
        "fen": board.fen(),
        "line": sans,
        "color": color,
        "turn": "white" if board.turn == chess.WHITE else "black",
        "my_turn": my_turn,
        "opening": {"eco": opening.eco, "name": opening.name} if opening else None,
        "games": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "score": round(100 * (wins + 0.5 * draws) / decided, 1) if decided else 0.0,
        "moves": moves,
        "repertoire": entry_dict(entry) if entry else None,
        "last_move": last_move,
        "eval": (
            {**white_pov(here), "best_san": here.best_san, "best_uci": here.best_uci,
             "pv_san": here.pv_san}
            if here else None
        ),
        "recent_games": games_through(db, key, filters, recent_games) if total else [],
    }
