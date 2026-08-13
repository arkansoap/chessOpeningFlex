"""Integration tests for the repertoire API endpoints."""
from __future__ import annotations

from app.core.schemas import (
    RepertoireCreate,
    RepertoireLineCreate,
)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_get_repertoire(client):
    payload = RepertoireCreate(name="White 2024", color="white").model_dump()
    resp = client.post("/api/v1/repertoire", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    rep_id = created["id"]
    assert created["name"] == "White 2024"
    assert created["color"] == "white"

    resp = client.get(f"/api/v1/repertoire/{rep_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["lines"] == []


def test_add_update_delete_line(client):
    # create repertoire
    rep = client.post(
        "/api/v1/repertoire",
        json=RepertoireCreate(name="Black", color="black").model_dump(),
    ).json()

    # add a line
    line = client.post(
        "/api/v1/repertoire/line",
        json=RepertoireLineCreate(
            repertoire_id=rep["id"],
            moves="e4 c5",
            starting_position="startpos",
            depth=2,
        ).model_dump(),
    ).json()
    assert line["moves"] == "e4 c5"

    # update
    updated = client.put(
        f"/api/v1/repertoire/line/{line['id']}",
        json={"comment": "Sicilian", "priority": 5},
    ).json()
    assert updated["comment"] == "Sicilian"
    assert updated["priority"] == 5

    # delete
    resp = client.delete(f"/api/v1/repertoire/line/{line['id']}")
    assert resp.status_code == 204


def test_get_question_and_answer(client):
    rep = client.post(
        "/api/v1/repertoire",
        json=RepertoireCreate(name="W", color="white").model_dump(),
    ).json()
    line = client.post(
        "/api/v1/repertoire/line",
        json=RepertoireLineCreate(
            repertoire_id=rep["id"],
            moves="e4 e5 Nf3",
            starting_position="startpos",
            depth=3,
        ).model_dump(),
    ).json()

    resp = client.get(
        "/api/v1/training/question",
        params={"line_id": line["id"], "mode": "sequential", "step": 0},
    )
    assert resp.status_code == 200
    q = resp.json()
    assert q["expected_move"] == "e4"

    # correct answer
    ans = client.post(
        "/api/v1/training/answer",
        json={
            "line_id": line["id"],
            "move_played": "e4",
            "expected_move": "e4",
            "fen": q["fen"],
        },
    ).json()
    assert ans["is_correct"] is True

    # incorrect answer
    ans = client.post(
        "/api/v1/training/answer",
        json={
            "line_id": line["id"],
            "move_played": "d4",
            "expected_move": "e4",
            "fen": q["fen"],
        },
    ).json()
    assert ans["is_correct"] is False


def test_create_session_and_stats(client):
    rep = client.post(
        "/api/v1/repertoire",
        json=RepertoireCreate(name="W", color="white").model_dump(),
    ).json()
    line = client.post(
        "/api/v1/repertoire/line",
        json=RepertoireLineCreate(
            repertoire_id=rep["id"],
            moves="e4 e5",
            starting_position="startpos",
            depth=2,
        ).model_dump(),
    ).json()

    resp = client.post(
        "/api/v1/training/session",
        params={
            "repertoire_id": rep["id"],
            "line_id": line["id"],
            "mode": "random",
            "total_questions": 10,
            "correct_answers": 8,
            "time_spent": 120,
        },
    )
    assert resp.status_code == 201

    stats = client.get(
        "/api/v1/training/stats", params={"line_id": line["id"]}
    ).json()
    assert len(stats) == 1
    assert stats[0]["attempts"] == 10
    assert abs(stats[0]["success_rate"] - 0.8) < 1e-6
