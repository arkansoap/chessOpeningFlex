"""The tree of my games and the per-position view."""
from __future__ import annotations

from datetime import date

from app.services.chess_utils import START_KEY, board_from, position_key
from app.services.explorer import GameFilters, load_graph, moves_from, openings_summary
from app.services.position_view import position_view

WHITE = GameFilters(color="white")


def key_of(line: str) -> str:
    return position_key(board_from(line)[0])


def test_first_moves_are_counted(sample_games):
    moves = {e.san: e for e in moves_from(sample_games, START_KEY, WHITE)}
    assert moves["e4"].games == 2 and moves["Nf3"].games == 1
    assert (moves["e4"].wins, moves["e4"].losses) == (1, 1)
    assert moves["e4"].score == 50.0


def test_transpositions_merge(sample_games):
    moves = {e.san: e for e in moves_from(sample_games, key_of("e4 e5 Nf3 Nc6"), WHITE)}
    assert moves["Bb5"].games == 2  # one via 1.e4, one via 1.Nf3
    assert moves["Bc4"].games == 1
    assert (moves["Bb5"].wins, moves["Bb5"].draws) == (1, 1)


def test_filters_narrow_the_games(sample_games):
    blitz = GameFilters(color="white", time_classes=("blitz",))
    assert [e.san for e in moves_from(sample_games, key_of("e4 e5 Nf3 Nc6"), blitz)] == ["Bc4"]
    strong = GameFilters(color="white", min_opponent_elo=1600)
    assert sum(e.games for e in moves_from(sample_games, START_KEY, strong)) == 1
    recent = GameFilters(color="white", since=date(2026, 10, 3))
    assert [e.san for e in moves_from(sample_games, START_KEY, recent)] == ["Nf3"]
    black = GameFilters(color="black")
    assert [e.san for e in moves_from(sample_games, START_KEY, black)] == ["e4"]


def test_graph_paths(sample_games):
    graph = load_graph(sample_games, WHITE)
    assert graph.line_to(key_of("e4 e5 Nf3 Nc6")) in (["e4", "e5", "Nf3", "Nc6"], ["Nf3", "Nc6", "e4", "e5"])
    assert graph.games_at(START_KEY) == 3
    assert graph.is_my_turn(START_KEY)


def test_openings_summary_groups_by_family(sample_games):
    families = {f["family"]: f for f in openings_summary(sample_games, WHITE)}
    assert families["Ruy Lopez"]["games"] == 2
    assert families["Ruy Lopez"]["score"] == 75.0
    assert families["Italian Game"]["games"] == 1
    assert families["Ruy Lopez"]["line"].startswith("e4 e5 Nf3 Nc6 Bb5")


def test_position_view(sample_games):
    view = position_view(sample_games, WHITE, line="1. e4 e5 2. Nf3 Nc6")
    assert view["my_turn"] is True and view["games"] == 3
    assert view["line"] == ["e4", "e5", "Nf3", "Nc6"]
    assert [m["san"] for m in view["moves"]] == ["Bb5", "Bc4"]
    assert view["opening"]["name"].startswith("King's Knight Opening")
    assert len(view["recent_games"]) == 3

    opp = position_view(sample_games, WHITE, line="e4")
    assert opp["my_turn"] is False
    assert opp["moves"][0]["covered"] is False


def test_position_api(client, sample_games):
    resp = client.get("/api/v1/explorer/position", params={"color": "white", "line": "e4 e5"})
    assert resp.status_code == 200
    assert resp.json()["moves"][0]["san"] == "Nf3"
    bad = client.get("/api/v1/explorer/position", params={"color": "white", "line": "e4 Ke2"})
    assert bad.status_code == 400
    assert client.get("/api/v1/explorer/openings", params={"color": "black"}).json()[0]["family"] == "Sicilian Defense"
    assert client.get("/api/v1/games/summary").json()["games"] == 4


def test_last_move_can_be_adopted(client, sample_games):
    """A move never played in my games is added by playing it, then starring it."""
    view = client.get("/api/v1/explorer/position", params={"color": "white", "line": "d4"}).json()
    assert view["games"] == 0
    assert view["last_move"] == {"san": "d4", "uci": "d2d4", "is_repertoire": False, "repertoire_move": None}
    client.put("/api/v1/repertoire/white/entry", json={"line": "", "move": "d4"})
    view = client.get("/api/v1/explorer/position", params={"color": "white", "line": "d4"}).json()
    assert view["last_move"]["is_repertoire"] is True
    other = client.get("/api/v1/explorer/position", params={"color": "white", "line": "e4"}).json()
    assert other["last_move"]["is_repertoire"] is False and other["last_move"]["repertoire_move"] == "d4"
    # On my own turn there is no "last move of mine".
    assert client.get("/api/v1/explorer/position", params={"color": "white", "line": "d4 d5"}).json()["last_move"] is None
