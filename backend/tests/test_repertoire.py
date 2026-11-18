"""Repertoire entries, coverage of my games, draft from games, PGN exchange."""
from __future__ import annotations

import pytest

from app.core.models import Game, PositionEval, RepertoireEntry
from app.services.chess_utils import board_from, position_key
from app.services.explorer import GameFilters
from app.services.repertoire import adopt, coverage, pgn_io, service

WHITE = GameFilters(color="white")


def key_of(line: str) -> str:
    return position_key(board_from(line)[0])


def add(db, color: str, line: str, move: str, **kwargs):
    board, sans = board_from(line)
    entry, changed = service.upsert_entry(db, color, board, sans, move, **kwargs)
    db.commit()
    return entry, changed


def test_upsert_and_replace(db_session):
    entry, created = add(db_session, "white", "", "e4", comment="centre")
    assert created and entry.move_uci == "e2e4" and entry.line_san == ""
    entry.srs_level = 5
    same, changed = add(db_session, "white", "", "e2e4")
    assert same.id == entry.id and not changed and same.srs_level == 5
    replaced, changed = add(db_session, "white", "", "d4")
    assert changed and replaced.move_san == "d4" and replaced.srs_level == 0
    assert replaced.comment == "centre"
    assert service.summary(db_session, "white")["entries"] == 1


def test_only_my_own_moves_are_accepted(db_session):
    with pytest.raises(service.RepertoireError):
        add(db_session, "black", "", "e4")
    with pytest.raises(service.RepertoireError):
        add(db_session, "white", "", "e5")


def test_coverage_reports_gaps_and_deviations(sample_games):
    db = sample_games
    report = coverage.coverage(db, WHITE)
    assert report["games"] == 3 and report["with_gap"] == 3
    assert report["gaps"][0]["line"] == [] and report["gaps"][0]["games"] == 3

    add(db, "white", "", "e4")
    add(db, "white", "e4 e5", "Nf3")
    add(db, "white", "e4 e5 Nf3 Nc6", "Bb5")
    report = coverage.coverage(db, WHITE)
    # Game A follows the repertoire, B plays Bc4 instead of Bb5, C starts 1.Nf3.
    assert (report["covered"], report["with_deviation"], report["with_gap"]) == (1, 2, 0)
    by_expected = {d["expected"]: d for d in report["deviations"]}
    assert by_expected["Bb5"]["played"] == [{"san": "Bc4", "games": 1}]
    assert by_expected["e4"]["played"] == [{"san": "Nf3", "games": 1}]
    assert report["average_followed"] == round((3 + 2 + 0) / 3, 1)


def test_gap_after_an_unprepared_reply(sample_games):
    db = sample_games
    add(db, "white", "", "e4")
    report = coverage.coverage(db, WHITE)
    gap = next(g for g in report["gaps"] if g["line"] == ["e4", "e5"])
    assert gap["games"] == 2 and gap["played"] == [{"san": "Nf3", "games": 2}]
    assert gap["opening"] == "King's Pawn Game"


def test_review_lists_recent_games(sample_games):
    db = sample_games
    add(db, "white", "", "e4")
    add(db, "white", "e4 e5", "Nf3")
    add(db, "white", "e4 e5 Nf3 Nc6", "Bb5")
    review = coverage.review(db, "white", limit=10)
    assert [r["game"]["opponent"] for r in review] == ["cat", "bob", "ann"]
    assert review[0]["status"] == "deviation" and review[0]["expected"] == "e4"
    assert review[1]["played"] == "Bc4" and review[1]["line"] == ["e4", "e5", "Nf3", "Nc6"]
    assert review[2]["status"] == "covered" and review[2]["followed"] == 3


def test_new_games_send_missed_moves_back_to_training(sample_games):
    db = sample_games
    entry, _ = add(db, "white", "e4 e5 Nf3 Nc6", "Bb5")
    add(db, "white", "", "e4")
    add(db, "white", "e4 e5", "Nf3")
    entry.srs_level = 6
    db.commit()
    bob = db.query(Game).filter(Game.opponent == "bob").one()
    assert coverage.flag_deviations(db, [bob.id]) == 1
    db.refresh(entry)
    assert entry.srs_level == 0 and entry.lapses == 1 and entry.due_at is not None


def test_draft_follows_my_usual_moves(sample_games):
    db = sample_games
    proposal = adopt.propose(db, WHITE, min_games=2, min_share=0.6)
    lines = {tuple(a["line"]): a["san"] for a in proposal["additions"]}
    # 1.e4 in 2 of 3 games, then 2.Nf3 and 3.Bb5 (2 of 3 at that position).
    assert lines[()] == "e4" and lines[("e4", "e5")] == "Nf3"
    assert lines[("e4", "e5", "Nf3", "Nc6")] == "Bb5"
    strict = adopt.propose(db, WHITE, min_games=2, min_share=0.9)
    assert strict["additions"] == [] and strict["skipped"][0]["reason"] == "hesitation"

    result = adopt.apply(db, WHITE, min_games=2, min_share=0.6)
    assert result["added"] == 3
    assert adopt.apply(db, WHITE, min_games=2, min_share=0.6)["added"] == 0


def test_draft_leaves_out_leaks(sample_games):
    db = sample_games
    db.add_all([
        PositionEval(key=key_of(""), depth=16, cp=30, best_uci="d2d4", best_san="d4"),
        PositionEval(key=key_of("e4"), depth=16, cp=250),  # 1.e4 "loses" 2.8 pawns
    ])
    db.commit()
    proposal = adopt.propose(db, WHITE, min_games=2, min_share=0.6)
    assert proposal["additions"] == []
    assert proposal["skipped"][0]["reason"] == "leak" and proposal["skipped"][0]["best_san"] == "d4"


def test_pgn_round_trip(db_session):
    db = db_session
    add(db, "black", "e4", "c5", comment="Sicilienne")
    add(db, "black", "e4 c5 Nf3", "d6")
    add(db, "black", "e4 c5 Nc3", "Nc6")
    add(db, "black", "d4", "Nf6")
    text = pgn_io.export_pgn(db, "black")
    assert "{ Sicilienne }" in text and "2. Nf3 ( 2. Nc3 Nc6 ) 2... d6" in text

    db.query(RepertoireEntry).delete()
    db.commit()
    assert pgn_io.import_pgn(db, "black", text) == {"added": 4, "updated": 0, "kept": 0}
    moves = service.moves_by_key(db, "black")
    assert moves[key_of("e4 c5 Nc3")] == "Nc6" and moves[key_of("d4")] == "Nf6"
    again = pgn_io.import_pgn(db, "black", text)
    assert again == {"added": 0, "updated": 0, "kept": 4}


def test_import_keeps_my_choice_unless_overwrite(db_session):
    db = db_session
    add(db, "white", "", "d4")
    assert pgn_io.import_pgn(db, "white", "1. e4 e5 2. Nf3 *")["kept"] == 1
    assert service.moves_by_key(db, "white")[key_of("")] == "d4"
    assert pgn_io.import_pgn(db, "white", "1. e4 e5 2. Nf3 *", overwrite=True)["updated"] == 1
    assert service.moves_by_key(db, "white")[key_of("")] == "e4"


def test_isolated_entry_is_exported(db_session):
    db = db_session
    add(db, "white", "e4 e5 Nf3 Nc6", "Bb5")  # nothing chosen before it
    text = pgn_io.export_pgn(db, "white")
    assert "3. Bb5" in text


def test_repertoire_api(client, sample_games):
    put = client.put("/api/v1/repertoire/white/entry", json={"line": "", "move": "e4"})
    assert put.status_code == 200 and put.json()["move_san"] == "e4"
    wrong = client.put("/api/v1/repertoire/white/entry", json={"line": "e4", "move": "e5"})
    assert wrong.status_code == 400
    rep = client.get("/api/v1/repertoire/white").json()
    assert rep["entries"] == 1 and rep["items"][0]["opening"]
    view = client.get("/api/v1/explorer/position", params={"color": "white", "line": ""}).json()
    assert view["repertoire"]["move_san"] == "e4"
    assert next(m for m in view["moves"] if m["san"] == "e4")["is_repertoire"] is True
    cov = client.get("/api/v1/repertoire/coverage", params={"color": "white"}).json()
    assert cov["with_deviation"] == 1 and cov["with_gap"] == 2
    entry_id = put.json()["id"]
    assert client.patch(f"/api/v1/repertoire/entry/{entry_id}", json={"comment": "plan"}).json()["comment"] == "plan"
    assert "1. e4" in client.get("/api/v1/repertoire/white/export.pgn").text
    draft = client.post("/api/v1/repertoire/adopt", params={"color": "white"},
                        json={"min_games": 2, "min_share": 0.6}).json()
    assert draft["added"] == 0 and len(draft["additions"]) == 2
    assert client.delete(f"/api/v1/repertoire/entry/{entry_id}").status_code == 204
    assert client.get("/api/v1/repertoire/white").json()["entries"] == 0
