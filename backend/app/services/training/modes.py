"""Training question generation per mode."""
from __future__ import annotations

import random

import chess

from app.core.models import TrainingMode
from app.services.analysis.variants import split_moves


def _board_from_fen(fen: str) -> chess.Board:
    if fen in ("startpos", "", None):
        return chess.Board()
    return chess.Board(fen)


def _player_color_str(color: chess.Color) -> str:
    return "white" if color == chess.WHITE else "black"


def generate_question_full_variation(
    moves_san: str, starting_position: str, line_id: str
) -> dict | None:
    """Full-variation mode: ask for the next move from the line at a random
    point where it's the repertoire side's turn."""
    moves = split_moves(moves_san)
    if not moves:
        return None
    # Build all intermediate positions and pick one where it's the player's turn.
    board = _board_from_fen(starting_position)
    checkpoints: list[tuple[chess.Board, str, int]] = []
    for idx, san in enumerate(moves):
        try:
            san_clean = san
            board_before = board.copy()
            move = board.parse_san(san_clean)
        except (chess.IllegalMoveError, chess.InvalidMoveError, ValueError):
            break
        # question: position BEFORE this move, expected answer is this move
        checkpoints.append((board_before.fen(), san_clean, idx + 1))
        board.push(move)
    if not checkpoints:
        return None
    fen, expected, move_number = random.choice(checkpoints)
    color_to_move = _player_color_str(chess.Board(fen).turn)
    return {
        "line_id": line_id,
        "fen": fen,
        "expected_move": expected,
        "move_number": move_number,
        "color_to_move": color_to_move,
    }


def generate_question_random(
    moves_san: str, starting_position: str, line_id: str
) -> dict | None:
    """Random mode: the opponent's move is played, then ask the player for
    the correct response. For the MVP this collapses to picking any position
    in the line and asking for the next move."""
    return generate_question_full_variation(moves_san, starting_position, line_id)


def generate_question_sequential(
    moves_san: str, starting_position: str, line_id: str, step: int = 0
) -> dict | None:
    """Sequential mode: deterministic step through the line."""
    moves = split_moves(moves_san)
    if not moves:
        return None
    step = max(0, min(step, len(moves) - 1))
    board = _board_from_fen(starting_position)
    for san in moves[:step]:
        try:
            board.push_san(san)
        except (chess.IllegalMoveError, chess.InvalidMoveError, ValueError):
            return None
    expected = moves[step]
    color_to_move = _player_color_str(board.turn)
    return {
        "line_id": line_id,
        "fen": board.fen(),
        "expected_move": expected,
        "move_number": step + 1,
        "color_to_move": color_to_move,
    }


def generate_question(
    mode: str,
    moves_san: str,
    starting_position: str,
    line_id: str,
    step: int = 0,
) -> dict | None:
    if mode == TrainingMode.FULL_VARIATION.value:
        return generate_question_full_variation(moves_san, starting_position, line_id)
    if mode == TrainingMode.RANDOM.value:
        return generate_question_random(moves_san, starting_position, line_id)
    if mode == TrainingMode.SEQUENTIAL.value:
        return generate_question_sequential(
            moves_san, starting_position, line_id, step=step
        )
    raise ValueError(f"Unknown training mode: {mode}")


def check_answer(fen: str, move_played: str, expected_move: str) -> bool:
    """Check whether the played SAN move matches the expected one in the
    position. Legality is verified; illegal played moves count as wrong."""
    board = chess.Board(fen)
    try:
        played = board.parse_san(move_played)
        expected = board.parse_san(expected_move)
    except (chess.IllegalMoveError, chess.InvalidMoveError, ValueError):
        return False
    return played == expected
