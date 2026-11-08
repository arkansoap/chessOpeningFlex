"""Tests for the raw-PGN upload endpoint."""
from __future__ import annotations

PGN = """[Event "Test"]
[Site "?"]
[Date "2024.01.01"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]
[ECO "C65"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 Nf6 1-0
"""


def test_upload_pgn_reads_the_raw_body(client):
    """The PGN travels in the request body, not as a query parameter."""
    resp = client.post(
        "/api/v1/chesscom/upload-pgn",
        content=PGN,
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 201, resp.text
    games = resp.json()
    assert len(games) == 1
    assert games[0]["white_player"] == "Alice"
    assert games[0]["black_player"] == "Bob"
    assert "e4" in games[0]["pgn_data"]


def test_upload_pgn_accepts_latin1_bodies(client):
    """Older exports are often latin-1; they must not 400."""
    pgn = PGN.replace('[White "Alice"]', '[White "André"]')
    resp = client.post(
        "/api/v1/chesscom/upload-pgn",
        content=pgn.encode("latin-1"),
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()[0]["white_player"] == "André"


def test_upload_pgn_rejects_an_empty_body(client):
    resp = client.post(
        "/api/v1/chesscom/upload-pgn",
        content="   \n",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Empty PGN body"
