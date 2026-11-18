"""Batch analysis and leak detection, with a scripted engine."""
from __future__ import annotations

import chess

from app.core.models import PositionEval
from app.services import jobs
from app.services.analysis import leaks
from app.services.chess_utils import board_from, position_key, win_percent
from app.services.explorer import GameFilters, load_graph

WHITE = GameFilters(color="white")


def key_of(line: str) -> str:
    return position_key(board_from(line)[0])


class ScriptedEngine:
    """Returns a fixed evaluation per position, +20 for the mover otherwise."""

    def __init__(self, script: dict[str, dict]):
        self.script = script
        self.calls = 0

    def analyse(self, board: chess.Board, depth: int | None = None) -> dict:
        self.calls += 1
        base = {"cp": 20, "mate": None, "best_uci": None, "best_san": None, "pv_san": "", "depth": depth or 16}
        return {**base, **self.script.get(position_key(board), {})}


def test_win_percent_curve():
    assert win_percent(0, None) == 50
    assert 58 < win_percent(100, None) < 60
    assert win_percent(None, 3) == 100 and win_percent(None, -2) == 0


def test_targets_are_my_repeated_positions(sample_games):
    graph = load_graph(sample_games, WHITE)
    targets = {t.key: t.weight for t in leaks.analysis_targets(graph, min_games=2)}
    spanish = key_of("e4 e5 Nf3 Nc6")
    assert targets[spanish] == 3  # reached three times, I am to move
    assert key_of("e4 e5 Nf3 Nc6 Bb5") in targets  # after my repeated move
    assert key_of("e4 e5 Nf3 Nc6 Bc4") not in targets  # played only once
    assert key_of("e4") in targets  # after 1.e4, played twice


def test_analysis_fills_the_cache_once(sample_games):
    engine = ScriptedEngine({})
    state = jobs.JobState(kind="analysis")
    analysed = leaks.run_analysis(sample_games, state, min_games=2, engine=engine)
    assert analysed == engine.calls > 0 and state.done == state.total
    # A second run has nothing left to do.
    assert leaks.run_analysis(sample_games, jobs.JobState(kind="analysis"), min_games=2, engine=engine) == 0
    assert leaks.pending_targets(sample_games, 2)[0] == []


def test_leak_is_found_and_ranked(sample_games):
    spanish = key_of("e4 e5 Nf3 Nc6")
    engine = ScriptedEngine({
        # Before my move: +0.8 for me, best is Bc4.
        spanish: {"cp": 80, "best_uci": "f1c4", "best_san": "Bc4"},
        # After my usual Bb5 the opponent is better by 1.2: I lost about 2 pawns.
        key_of("e4 e5 Nf3 Nc6 Bb5"): {"cp": 120},
    })
    leaks.run_analysis(sample_games, jobs.JobState(kind="analysis"), min_games=2, engine=engine)
    found = leaks.find_leaks(sample_games, WHITE, min_games=2, repertoire_moves={spanish: "Bc4"})
    assert len(found) == 1
    leak = found[0]
    assert leak["move"]["san"] == "Bb5" and leak["move"]["games"] == 2
    assert leak["best_san"] == "Bc4" and leak["loss_cp"] == 200
    assert leak["severity"] == "gaffe" and leak["repertoire_move"] == "Bc4"
    assert leak["line"][-1] in ("Nc6", "e5")
    assert leak["opening"]
    # Nothing to report for moves played once or at a high threshold.
    assert leaks.find_leaks(sample_games, WHITE, min_games=3) == []
    assert leaks.find_leaks(sample_games, WHITE, min_loss=40) == []


def test_best_move_is_never_a_leak(sample_games):
    spanish = key_of("e4 e5 Nf3 Nc6")
    sample_games.add_all([
        PositionEval(key=spanish, depth=16, cp=30, best_uci="f1b5", best_san="Bb5"),
        PositionEval(key=key_of("e4 e5 Nf3 Nc6 Bb5"), depth=16, cp=400),
    ])
    sample_games.commit()
    assert leaks.find_leaks(sample_games, WHITE) == []


def test_move_loss_handles_mate():
    before = PositionEval(key="k w", depth=1, cp=50)
    mated = PositionEval(key="k b", depth=1, mate=0)
    assert leaks.move_loss(before, mated)["loss"] == 0.0  # I delivered mate
    getting_mated = PositionEval(key="k b", depth=1, mate=2)
    assert leaks.move_loss(before, getting_mated)["loss"] > 50


def test_leaks_api(client, sample_games):
    status = client.get("/api/v1/analysis/status").json()
    assert status["total"] > 0 and status["pending"] == status["total"]
    assert client.get("/api/v1/leaks", params={"color": "white"}).json() == {"total": 0, "leaks": []}
