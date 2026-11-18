"""Finding my recurring opening mistakes.

A "leak" is a move I play repeatedly in a position I reach often, and that the
engine rates clearly below its best move. Leaks are ranked by how much they
cost overall: number of games times the drop in expected score.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models import PositionEval
from app.services.analysis.engine import EngineService, board_from_key, engine_service, evaluate
from app.services.chess_utils import win_percent
from app.services.explorer import GameFilters, Graph, load_graph
from app.services import jobs, openings

# Drop in expected score (points out of 100), the scale Lichess uses.
INACCURACY, MISTAKE, BLUNDER = 5.0, 10.0, 15.0


def severity(loss: float) -> str:
    if loss >= BLUNDER:
        return "gaffe"
    if loss >= MISTAKE:
        return "erreur"
    return "imprécision"


@dataclass(frozen=True)
class Target:
    key: str
    weight: int  # games reaching the position


def analysis_targets(graph: Graph, min_games: int = 2, max_ply: int | None = None) -> list[Target]:
    """Positions worth evaluating for one colour, most visited first.

    For each position where I am to move and that I reached at least
    `min_games` times: the position itself (what is best there?) and the
    positions after each move I repeated (what did my move cost?).
    """
    max_ply = settings.max_analysed_plies if max_ply is None else max_ply
    paths = graph.paths()
    weights: dict[str, int] = {}
    for key, path in paths.items():
        if len(path) >= max_ply or not graph.is_my_turn(key):
            continue
        total = graph.games_at(key)
        if total < min_games:
            continue
        weights[key] = max(weights.get(key, 0), total)
        for edge in graph.moves(key):
            if edge.games >= min_games:
                weights[edge.key_after] = max(weights.get(edge.key_after, 0), edge.games)
    targets = [Target(key, weight) for key, weight in weights.items()]
    targets.sort(key=lambda t: -t.weight)
    return targets


def all_targets(db: Session, min_games: int = 2) -> list[Target]:
    merged: dict[str, int] = {}
    for color in ("white", "black"):
        graph = load_graph(db, GameFilters(color=color))
        for target in analysis_targets(graph, min_games):
            merged[target.key] = max(merged.get(target.key, 0), target.weight)
    return sorted((Target(k, w) for k, w in merged.items()), key=lambda t: -t.weight)


def pending_targets(db: Session, min_games: int = 2, depth: int | None = None) -> tuple[list[Target], int]:
    """Targets not evaluated deeply enough yet, and the total number of targets."""
    depth = depth or settings.analysis_depth
    targets = all_targets(db, min_games)
    known = {
        key for key, known_depth in db.execute(select(PositionEval.key, PositionEval.depth))
        if known_depth >= depth
    }
    return [t for t in targets if t.key not in known], len(targets)


def run_analysis(
    db: Session,
    state: jobs.JobState,
    min_games: int = 2,
    depth: int | None = None,
    engine: EngineService | None = None,
) -> int:
    """Evaluate every pending target. Returns the number of positions analysed."""
    engine = engine or engine_service
    pending, total = pending_targets(db, min_games, depth)
    state.total = total
    state.done = total - len(pending)
    analysed = 0
    for target in pending:
        if state.stop_requested:
            break
        evaluate(db, board_from_key(target.key), depth, engine)
        analysed += 1
        state.done += 1
        state.message = f"{state.done} / {total} positions"
        if analysed % 10 == 0:
            db.commit()
    db.commit()
    state.result["analysed"] = analysed
    return analysed


def start_analysis(min_games: int = 2) -> tuple[jobs.JobState, bool]:
    from app.core.database import SessionLocal

    def target(state: jobs.JobState) -> None:
        db = SessionLocal()
        try:
            run_analysis(db, state, min_games)
        finally:
            db.close()

    return jobs.start("analysis", target)


def load_evals(db: Session) -> dict[str, PositionEval]:
    return {row.key: row for row in db.scalars(select(PositionEval))}


def move_loss(before: PositionEval | None, after: PositionEval | None) -> dict | None:
    """What a move cost, given the evaluations before and after it.

    `before` is from my point of view (I am to move), `after` from the
    opponent's (they are to move), hence the sign flip.
    """
    if before is None or after is None:
        return None
    win_before = win_percent(before.cp, before.mate)
    after_cp = -after.cp if after.cp is not None else None
    after_mate = -after.mate if after.mate is not None else None
    if after.mate == 0:  # my move delivered mate
        after_mate, after_cp = 1, None
    win_after = win_percent(after_cp, after_mate)
    loss_cp = None
    if before.cp is not None and after_cp is not None:
        loss_cp = max(0, before.cp - after_cp)
    return {
        "loss": round(max(0.0, win_before - win_after), 1),
        "loss_cp": loss_cp,
        "eval_before": {"cp": before.cp, "mate": before.mate},
        "eval_after": {"cp": after_cp, "mate": after_mate},
    }


def find_leaks(
    db: Session,
    filters: GameFilters,
    min_games: int = 2,
    min_loss: float = INACCURACY,
    repertoire_moves: dict[str, str] | None = None,
) -> list[dict]:
    """My repeated moves that lose at least `min_loss` points of expected score."""
    graph = load_graph(db, filters)
    evals = load_evals(db)
    repertoire_moves = repertoire_moves or {}
    leaks: list[dict] = []
    for key, path in graph.paths().items():
        if not graph.is_my_turn(key):
            continue
        before = evals.get(key)
        if before is None or not before.best_uci:
            continue
        moves = graph.moves(key)
        total = sum(e.games for e in moves)
        for edge in moves:
            if edge.games < min_games or edge.uci == before.best_uci:
                continue
            cost = move_loss(before, evals.get(edge.key_after))
            if cost is None or cost["loss"] < min_loss:
                continue
            opening = openings.classify_line(path)
            leaks.append(
                {
                    "key": key,
                    "line": path,
                    "position_games": total,
                    "move": edge.as_dict(),
                    "best_san": before.best_san,
                    "best_uci": before.best_uci,
                    "pv_san": before.pv_san,
                    "severity": severity(cost["loss"]),
                    "weight": round(edge.games * cost["loss"], 1),
                    "repertoire_move": repertoire_moves.get(key),
                    "opening": opening.name if opening else None,
                    **cost,
                }
            )
    leaks.sort(key=lambda leak: -leak["weight"])
    return leaks
