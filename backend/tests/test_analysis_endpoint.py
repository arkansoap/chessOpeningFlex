"""Tests for the analysis variants endpoint."""
from __future__ import annotations


def test_analyze_variants_endpoint(client):
    pgn = '[White "A"][Black "B"][Result "1-0"] 1. e4 e5 2. Nf3 1-0'
    resp = client.post("/api/v1/analysis/variants", json={"pgn": pgn})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert "e4" in data[0]["moves"]


def test_analyze_variants_min_depth(client):
    pgn = '[White "A"][Black "B"][Result "1-0"] 1. e4 e5 1-0'
    resp = client.post(
        "/api/v1/analysis/variants", json={"pgn": pgn, "min_depth": 10}
    )
    assert resp.status_code == 200
    assert resp.json() == []
