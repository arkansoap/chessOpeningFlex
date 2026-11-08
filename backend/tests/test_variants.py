"""Tests for variant extraction and move splitting."""
from __future__ import annotations

import pytest

from app.services.analysis.variants import extract_variants, split_moves


PGN = '[White "A"][Black "B"][Result "1-0"] 1. e4 e5 2. Nf3 Nc6 1-0'


def test_extract_variants_for_white_ends_on_a_white_move():
    """A repertoire line closes on its own side's move, so Black's reply goes."""
    variants = extract_variants(PGN, color="white")
    assert len(variants) == 1
    assert split_moves(variants[0].moves) == ["e4", "e5", "Nf3"]


def test_extract_variants_for_black_ends_on_a_black_move():
    variants = extract_variants(PGN, color="black")
    assert len(variants) == 1
    assert split_moves(variants[0].moves) == ["e4", "e5", "Nf3", "Nc6"]


def test_extract_variants_rejects_an_unknown_color():
    with pytest.raises(ValueError):
        extract_variants(PGN, color="red")


def test_extract_variants_returns_nothing_when_the_side_never_moved():
    """One ply of white: a black repertoire has nothing to record."""
    pgn = '[White "A"][Black "B"][Result "*"] 1. e4 *'
    assert extract_variants(pgn, color="black") == []
    assert len(extract_variants(pgn, color="white")) == 1


def test_extract_variants_respects_min_depth():
    pgn = '[White "A"][Black "B"][Result "1-0"] 1. e4 e5 1-0'
    assert extract_variants(pgn, min_depth=5) == []
    assert len(extract_variants(pgn, min_depth=2)) == 1


def test_split_moves_handles_move_numbers():
    assert split_moves("1. e4 e5 2. Nf3") == ["e4", "e5", "Nf3"]
