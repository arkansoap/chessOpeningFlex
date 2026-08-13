"""Tests for training question generation and answer checking."""
from __future__ import annotations

import chess

from app.services.training.modes import (
    check_answer,
    generate_question,
    generate_question_sequential,
)

INITIAL_FEN = chess.STARTING_FEN
LINE = "1. e4 e5 2. Nf3 Nc6 3. Bb5"


def test_sequential_question_step0():
    q = generate_question_sequential(LINE, INITIAL_FEN, "line-1", step=0)
    assert q is not None
    assert q["expected_move"] == "e4"
    assert q["color_to_move"] == "white"


def test_sequential_question_step1():
    q = generate_question_sequential(LINE, INITIAL_FEN, "line-1", step=1)
    assert q is not None
    assert q["expected_move"] == "e5"
    assert q["color_to_move"] == "black"


def test_random_mode_returns_valid_question():
    q = generate_question("random", LINE, INITIAL_FEN, "line-1")
    assert q is not None
    # the expected move must be legal in the returned fen
    board = chess.Board(q["fen"])
    board.parse_san(q["expected_move"])  # raises if illegal


def test_check_answer_correct():
    board = chess.Board()
    board.push_san("e4")  # white played e4, black to move
    assert check_answer(board.fen(), "e5", "e5") is True


def test_check_answer_incorrect():
    board = chess.Board()
    board.push_san("e4")
    assert check_answer(board.fen(), "d5", "e5") is False


def test_check_answer_illegal_move_is_wrong():
    board = chess.Board()
    board.push_san("e4")
    assert check_answer(board.fen(), "e8", "e5") is False
