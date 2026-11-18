"""Drafting a repertoire from what I already play.

Starting from the initial position, the draft follows my games: where I am to
move it takes my usual move, provided I play it most of the time and the
engine does not object; then it continues through every reply opponents have
actually played against me often enough.
"""
from __future__ import annotations

import chess
from sqlalchemy.orm import Session

from app.services.analysis.engine import board_from_key
from app.services.analysis.leaks import load_evals, move_loss
from app.services.chess_utils import START_KEY, position_key
from app.services.explorer import GameFilters, load_graph
from app.services.repertoire.service import entries_by_key, get_repertoire, upsert_entry


def propose(
    db: Session,
    filters: GameFilters,
    min_games: int = 3,
    min_share: float = 0.5,
    max_loss: float = 5.0,
    require_eval: bool = False,
) -> dict:
    """Moves that could be added, and the positions left aside with the reason.

    `min_share` is the share of my games in which I played the move;
    `max_loss` the drop in expected score tolerated (points out of 100).
    """
    color = filters.color
    graph = load_graph(db, filters)
    evals = load_evals(db)
    entries = entries_by_key(db, get_repertoire(db, color))
    additions: list[dict] = []
    skipped: list[dict] = []
    seen: set[str] = set()

    def after(key: str, uci: str) -> str:
        board = board_from_key(key)
        board.push(chess.Move.from_uci(uci))
        return position_key(board)

    def visit(key: str, line: list[str]) -> None:
        if key in seen:
            return
        seen.add(key)
        if not graph.is_my_turn(key):
            for edge in graph.moves(key):
                if edge.games >= min_games:
                    visit(edge.key_after, line + [edge.san])
            return

        entry = entries.get(key)
        if entry is not None:
            visit(after(key, entry.move_uci), line + [entry.move_san])
            return

        moves = graph.moves(key)
        total = sum(e.games for e in moves)
        if total < min_games:
            return
        top = moves[0]
        share = top.games / total
        base = {"key": key, "line": line, "games": total, "san": top.san, "share": round(share, 2)}
        if share < min_share:
            skipped.append({**base, "reason": "hesitation",
                            "alternatives": [e.san for e in moves[:3]]})
            return
        cost = move_loss(evals.get(key), evals.get(top.key_after))
        if cost is None and require_eval:
            skipped.append({**base, "reason": "not_analysed"})
            return
        if cost is not None and cost["loss"] > max_loss:
            best = evals[key]
            skipped.append({**base, "reason": "leak", "loss": cost["loss"],
                            "best_san": best.best_san})
            return
        additions.append({**base, "uci": top.uci, "loss": cost["loss"] if cost else None})
        visit(top.key_after, line + [top.san])

    visit(START_KEY, [])
    return {"color": color, "additions": additions, "skipped": skipped}


def apply(db: Session, filters: GameFilters, **params) -> dict:
    """Add the proposed moves to the repertoire. Commits."""
    proposal = propose(db, filters, **params)
    added = 0
    for item in proposal["additions"]:
        board = board_from_key(item["key"])
        _, changed = upsert_entry(
            db, filters.color, board, item["line"], item["uci"],
            source="adopted", overwrite=False,
        )
        added += int(changed)
    db.commit()
    return {**proposal, "added": added}
