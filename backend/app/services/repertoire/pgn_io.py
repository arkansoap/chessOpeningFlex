"""Exchanging a repertoire as PGN (Lichess studies, Chessable, ChessBase...)."""
from __future__ import annotations

import io

import chess
import chess.pgn
from sqlalchemy.orm import Session

from app.core.models import RepertoireEntry
from app.services.chess_utils import board_from, position_key
from app.services.repertoire.service import entries_by_key, get_repertoire, upsert_entry


def export_pgn(db: Session, color: str) -> str:
    """One game holding the whole tree as variations.

    My moves come from the entries; the opponent's replies are the legal moves
    that lead to a position I have an answer for. Entries that cannot be
    reached that way are appended as separate games, on their own line.
    """
    rep = get_repertoire(db, color)
    entries = entries_by_key(db, rep)
    reached: set[str] = set()

    main = chess.pgn.Game()
    main.headers["Event"] = f"Répertoire — {rep.name}"
    main.headers["White" if color == "white" else "Black"] = "Moi"
    main.headers["Result"] = "*"

    def grow(node: chess.pgn.GameNode, board: chess.Board) -> None:
        key = position_key(board)
        mine = (board.turn == chess.WHITE) == (color == "white")
        if mine:
            entry = entries.get(key)
            if entry is None or key in reached:
                return
            reached.add(key)
            move = chess.Move.from_uci(entry.move_uci)
            child = node.add_variation(move, comment=entry.comment or "")
            board.push(move)
            grow(child, board)
            board.pop()
            return
        for move in list(board.legal_moves):
            board.push(move)
            next_key = position_key(board)
            if next_key in entries and next_key not in reached:
                grow(node.add_variation(move), board)
            board.pop()

    grow(main, main.board())
    games = [main]
    orphans = sorted(
        (e for key, e in entries.items() if key not in reached),
        key=lambda e: (len(e.line_san.split()), e.line_san),
    )
    for entry in orphans:
        if entry.position_key in reached:
            continue
        games.append(_orphan_game(entry, rep.name, entries, reached, color))

    out = io.StringIO()
    for game in games:
        print(game, file=out, end="\n\n")
    return out.getvalue()


def _orphan_game(entry: RepertoireEntry, name: str, entries: dict, reached: set[str], color: str) -> chess.pgn.Game:
    """A separate game for an entry the main tree does not lead to."""
    game = chess.pgn.Game()
    game.headers["Event"] = f"Répertoire — {name} (ligne isolée)"
    game.headers["Result"] = "*"
    board, sans = board_from(entry.line_san)
    if position_key(board) != entry.position_key:
        board = chess.Board(entry.fen)
        game.setup(board)
        sans = []
    node: chess.pgn.GameNode = game
    replay = game.board()
    for san in sans:
        move = replay.parse_san(san)
        node = node.add_variation(move)
        replay.push(move)
    reached.add(entry.position_key)
    node.add_variation(chess.Move.from_uci(entry.move_uci), comment=entry.comment or "")
    return game


def import_pgn(db: Session, color: str, text: str, overwrite: bool = False) -> dict:
    """Read my moves from the main lines and variations of a PGN.

    Where a position offers several moves for my side, the first one (the
    main line) is taken. Existing entries are kept unless `overwrite`.
    Commits.
    """
    added = updated = kept = 0
    stream = io.StringIO(text)
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        stack: list[tuple[chess.pgn.GameNode, chess.Board, list[str]]] = [(game, game.board(), [])]
        from_start = game.board().fen() == chess.STARTING_FEN
        while stack:
            node, board, line = stack.pop()
            if not node.variations:
                continue
            mine = (board.turn == chess.WHITE) == (color == "white")
            if mine:
                child = node.variations[0]
                existing_before = _has_entry(db, color, board)
                entry, changed = upsert_entry(
                    db, color, board, line if from_start else [], child.move.uci(),
                    comment=child.comment.strip() or None, source="pgn", overwrite=overwrite,
                )
                db.flush()
                if not existing_before:
                    added += 1
                elif changed:
                    updated += 1
                else:
                    kept += 1
            for child in node.variations:
                next_board = board.copy(stack=False)
                san = next_board.san(child.move)
                next_board.push(child.move)
                stack.append((child, next_board, line + [san]))
    db.commit()
    return {"added": added, "updated": updated, "kept": kept}


def _has_entry(db: Session, color: str, board: chess.Board) -> bool:
    rep = get_repertoire(db, color)
    return position_key(board) in entries_by_key(db, rep)
