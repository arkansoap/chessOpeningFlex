"""Spaced repetition."""
from __future__ import annotations

from datetime import timedelta

from app.core.models import utcnow
from app.services.chess_utils import board_from
from app.services.repertoire import service
from app.services.training import srs


def add(db, color, line, move):
    board, sans = board_from(line)
    entry, _ = service.upsert_entry(db, color, board, sans, move)
    db.commit()
    return entry


def test_new_moves_come_root_first(db_session):
    deep = add(db_session, "white", "e4 e5", "Nf3")
    root = add(db_session, "white", "", "e4")
    first = srs.next_question(db_session, "white")
    assert first["remaining"] == 2 and first["question"]["entry_id"] == root.id
    assert first["question"]["is_new"] and first["question"]["color"] == "white"
    second = srs.next_question(db_session, "white", exclude=root.id)
    assert second["question"]["entry_id"] == deep.id and second["question"]["line"] == ["e4", "e5"]


def test_correct_answers_climb_the_ladder(db_session):
    entry = add(db_session, "white", "", "e4")
    result = srs.answer(db_session, entry.id, "e4")
    assert result["correct"] and result["entry"]["srs_level"] == 1
    assert timedelta(hours=3) < entry.due_at - utcnow() <= timedelta(hours=4)
    assert srs.next_question(db_session, "white")["question"] is None
    result = srs.answer(db_session, entry.id, "e2e4")  # UCI accepted too
    assert result["entry"]["srs_level"] == 2


def test_a_mistake_resets_the_move(db_session):
    entry = add(db_session, "white", "", "e4")
    entry.srs_level = 5
    db_session.commit()
    result = srs.answer(db_session, entry.id, "d4")
    assert not result["correct"] and result["entry"]["srs_level"] == 0
    assert entry.lapses == 1 and srs.next_question(db_session, "white")["remaining"] == 1
    assert not srs.answer(db_session, entry.id, "", reveal=True)["correct"]
    assert srs.answer(db_session, "missing", "e4") is None


def test_missed_moves_come_before_new_ones(db_session):
    add(db_session, "white", "", "e4")
    missed = add(db_session, "white", "e4 e5", "Nf3")
    missed.lapses, missed.due_at = 1, utcnow()
    db_session.commit()
    assert srs.next_question(db_session, "white")["question"]["entry_id"] == missed.id


def test_colour_filter_and_all_mode(db_session):
    white = add(db_session, "white", "", "e4")
    black = add(db_session, "black", "e4", "c5")
    assert srs.next_question(db_session, "black")["question"]["entry_id"] == black.id
    assert srs.next_question(db_session, None)["remaining"] == 2
    srs.answer(db_session, white.id, "e4")
    srs.answer(db_session, black.id, "c5")
    assert srs.next_question(db_session, None)["question"] is None
    assert srs.next_question(db_session, None, mode="all")["remaining"] == 2


def test_stats_and_api(client, db_session):
    entry = add(db_session, "white", "", "e4")
    question = client.get("/api/v1/training/next", params={"color": "white"}).json()
    assert question["question"]["entry_id"] == entry.id
    answer = client.post("/api/v1/training/answer", json={"entry_id": entry.id, "move": "e4"})
    assert answer.json()["correct"] is True
    stats = client.get("/api/v1/training/stats").json()
    assert stats["days"][0]["reviews"] == 1 and stats["days"][0]["correct"] == 1
    assert stats["colors"]["white"] == {"entries": 1, "new": 0, "due": 0, "learned": 0}
    assert client.post("/api/v1/training/answer", json={"entry_id": "x", "move": "e4"}).status_code == 404
