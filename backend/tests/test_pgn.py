"""Tests for PGN parsing and chess.com dict building."""
from __future__ import annotations

from app.services.chesscom.pgn import parse_pgn_string
from app.services.chesscom.api import build_imported_game_dicts

SAMPLE_PGN = """[Event "Test"]
[Site "?"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]
[ECO "B90"]
[UTCDate "2024.01.01"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 1-0
"""


def test_parse_pgn_string_returns_one_game():
    games = parse_pgn_string(SAMPLE_PGN)
    assert len(games) == 1
    g = games[0]
    assert g["white_player"] == "Alice"
    assert g["black_player"] == "Bob"
    assert g["result"] == "1-0"
    assert g["eco_code"] == "B90"
    assert "1. e4" in g["pgn_data"]
    assert g["source"] == "pgn_upload"


def test_build_imported_game_dicts_extracts_headers():
    raw = [
        {
            "uuid": "abc",
            "white": {"username": "Alice"},
            "black": {"username": "Bob"},
            "time_class": "rapid",
            "pgn": SAMPLE_PGN,
        }
    ]
    dicts = build_imported_game_dicts("alice", raw)
    assert len(dicts) == 1
    d = dicts[0]
    assert d["white_player"] == "Alice"
    assert d["eco_code"] == "B90"
    assert d["chesscom_username"] == "alice"
    assert d["source"] == "chess_com_api"


def test_parse_empty_pgn_raises():
    import pytest

    from app.services.chesscom.pgn import PgnParseError

    with pytest.raises(PgnParseError):
        parse_pgn_string("")
