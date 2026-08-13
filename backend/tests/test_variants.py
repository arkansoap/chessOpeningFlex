"""Tests for variant extraction and move splitting."""
from __future__ import annotations

from app.services.analysis.variants import extract_variants, split_moves


def test_extract_variants_returns_mainline():
    pgn = '[White "A"][Black "B"][Result "1-0"] 1. e4 e5 2. Nf3 Nc6 1-0'
    variants = extract_variants(pgn, color="white")
    assert len(variants) == 1
    moves = split_moves(variants[0].moves)
    assert moves == ["e4", "e5", "Nf3", "Nc6"]


def test_extract_variants_respects_min_depth():
    pgn = '[White "A"][Black "B"][Result "1-0"] 1. e4 e5 1-0'
    assert extract_variants(pgn, min_depth=5) == []
    assert len(extract_variants(pgn, min_depth=2)) == 1


def test_split_moves_handles_move_numbers():
    assert split_moves("1. e4 e5 2. Nf3") == ["e4", "e5", "Nf3"]
