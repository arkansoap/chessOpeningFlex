"""position-based model: games tree, repertoire entries, evaluations

Replaces the "one game -> one line" tables by tables keyed on positions.
Existing repertoire lines are converted: each of the repertoire side's moves
along a line becomes an entry "in this position I play that move".
Imported games are not carried over: they are fetched again by the sync.

Revision ID: 7c2a9d41b6e0
Revises: 419e0e23fe81
Create Date: 2026-11-18 17:30:00

"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import chess
import sqlalchemy as sa
from alembic import op

revision: str = "7c2a9d41b6e0"
down_revision: Union[str, None] = "419e0e23fe81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_TABLES = (
    "training_sessions",
    "memorization_stats",
    "repertoire_lines",
    "game_variants",
    "imported_games",
)


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("sync_cursor", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("platform"),
    )
    op.create_table(
        "games",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("white", sa.String(), nullable=False),
        sa.Column("black", sa.String(), nullable=False),
        sa.Column("white_elo", sa.Integer(), nullable=True),
        sa.Column("black_elo", sa.Integer(), nullable=True),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("my_color", sa.String(), nullable=True),
        sa.Column("my_result", sa.String(), nullable=True),
        sa.Column("opponent", sa.String(), nullable=True),
        sa.Column("opponent_elo", sa.Integer(), nullable=True),
        sa.Column("time_class", sa.String(), nullable=True),
        sa.Column("rated", sa.Boolean(), nullable=True),
        sa.Column("played_at", sa.DateTime(), nullable=True),
        sa.Column("eco", sa.String(), nullable=True),
        sa.Column("opening_name", sa.String(), nullable=True),
        sa.Column("moves_san", sa.Text(), nullable=False),
        sa.Column("ply_count", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "external_id", name="uq_games_platform_external_id"),
    )
    op.create_index("ix_games_my_color_played_at", "games", ["my_color", "played_at"])
    op.create_table(
        "game_plies",
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("ply", sa.Integer(), nullable=False),
        sa.Column("key_before", sa.String(), nullable=False),
        sa.Column("key_after", sa.String(), nullable=False),
        sa.Column("san", sa.String(), nullable=False),
        sa.Column("uci", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "ply"),
    )
    op.create_index("ix_game_plies_key_before", "game_plies", ["key_before"])
    op.create_table(
        "position_evals",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("cp", sa.Integer(), nullable=True),
        sa.Column("mate", sa.Integer(), nullable=True),
        sa.Column("best_uci", sa.String(), nullable=True),
        sa.Column("best_san", sa.String(), nullable=True),
        sa.Column("pv_san", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "repertoire_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("repertoire_id", sa.String(), nullable=False),
        sa.Column("position_key", sa.String(), nullable=False),
        sa.Column("fen", sa.String(), nullable=False),
        sa.Column("line_san", sa.Text(), nullable=False),
        sa.Column("move_san", sa.String(), nullable=False),
        sa.Column("move_uci", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("srs_level", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviews", sa.Integer(), nullable=False),
        sa.Column("lapses", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["repertoire_id"], ["repertoires.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repertoire_id", "position_key", name="uq_entries_repertoire_position"),
    )
    op.create_index("ix_repertoire_entries_repertoire_id", "repertoire_entries", ["repertoire_id"])
    op.create_index("ix_entries_due_at", "repertoire_entries", ["due_at"])
    op.create_table(
        "review_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("entry_id", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_logs_entry_id", "review_logs", ["entry_id"])
    op.create_index("ix_review_logs_reviewed_at", "review_logs", ["reviewed_at"])
    op.create_table(
        "explorer_cache",
        sa.Column("cache_key", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("cache_key"),
    )

    _convert_lines(op.get_bind())
    for table in LEGACY_TABLES:
        op.drop_table(table)


def _convert_lines(bind) -> None:
    """Turn each legacy line into one entry per move of the repertoire side."""
    lines = bind.execute(
        sa.text(
            "SELECT l.repertoire_id, r.color, l.moves, l.starting_position, l.comment, l.depth "
            "FROM repertoire_lines l JOIN repertoires r ON r.id = l.repertoire_id "
            "ORDER BY l.priority DESC, l.depth"
        )
    ).fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seen: set[tuple[str, str]] = set()
    insert = sa.text(
        "INSERT INTO repertoire_entries (id, repertoire_id, position_key, fen, line_san, "
        "move_san, move_uci, comment, source, created_at, srs_level, reviews, lapses) "
        "VALUES (:id, :repertoire_id, :key, :fen, :line, :san, :uci, :comment, 'migrated', "
        ":now, 0, 0, 0)"
    )
    for repertoire_id, color, moves, start, comment, depth in lines:
        from_start = start in (None, "", "startpos", chess.STARTING_FEN)
        try:
            board = chess.Board() if from_start else chess.Board(start)
        except ValueError:
            continue
        sans = [t for t in (moves or "").split() if not t.endswith(".")]
        if depth and depth > 0:
            sans = sans[:depth]
        played: list[str] = []
        for index, san in enumerate(sans):
            try:
                move = board.parse_san(san)
            except ValueError:
                break
            mine = (board.turn == chess.WHITE) == (color == "white")
            key = board.epd()
            if mine and (repertoire_id, key) not in seen:
                seen.add((repertoire_id, key))
                bind.execute(
                    insert,
                    {
                        "id": str(uuid.uuid4()),
                        "repertoire_id": repertoire_id,
                        "key": key,
                        "fen": board.fen(),
                        "line": " ".join(played) if from_start else "",
                        "san": board.san(move),
                        "uci": move.uci(),
                        # The line's comment belongs to its last move.
                        "comment": comment if index >= len(sans) - 2 else None,
                        "now": now,
                    },
                )
            played.append(board.san(move))
            board.push(move)


def downgrade() -> None:
    """Back to the line-based schema. Entries are not converted back."""
    for table in ("explorer_cache", "review_logs", "repertoire_entries", "position_evals",
                  "game_plies", "games", "accounts"):
        op.drop_table(table)

    op.create_table(
        "imported_games",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("chesscom_username", sa.String(), nullable=True),
        sa.Column("pgn_file_path", sa.String(), nullable=True),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("white_player", sa.String(), nullable=False),
        sa.Column("black_player", sa.String(), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=True),
        sa.Column("eco_code", sa.String(), nullable=True),
        sa.Column("pgn_data", sa.Text(), nullable=False),
        sa.Column("is_processed", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_imported_games_eco_code", "imported_games", ["eco_code"])
    op.create_index("ix_imported_games_game_id", "imported_games", ["game_id"])
    op.create_table(
        "game_variants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("moves", sa.Text(), nullable=False),
        sa.Column("starting_position", sa.String(), nullable=False),
        sa.Column("evaluation", sa.Float(), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["imported_games.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_game_variants_game_id", "game_variants", ["game_id"])
    op.create_table(
        "repertoire_lines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("repertoire_id", sa.String(), nullable=False),
        sa.Column("variant_id", sa.String(), nullable=True),
        sa.Column("moves", sa.Text(), nullable=False),
        sa.Column("starting_position", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("last_reviewed", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["repertoire_id"], ["repertoires.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["game_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repertoire_lines_repertoire_id", "repertoire_lines", ["repertoire_id"])
    op.create_index("ix_repertoire_lines_variant_id", "repertoire_lines", ["variant_id"])
    op.create_table(
        "memorization_stats",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("line_id", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_attempt", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["line_id"], ["repertoire_lines.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memorization_stats_line_id", "memorization_stats", ["line_id"])
    op.create_table(
        "training_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("repertoire_id", sa.String(), nullable=False),
        sa.Column("line_id", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("correct_answers", sa.Integer(), nullable=False),
        sa.Column("time_spent", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["line_id"], ["repertoire_lines.id"]),
        sa.ForeignKeyConstraint(["repertoire_id"], ["repertoires.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_sessions_line_id", "training_sessions", ["line_id"])
    op.create_index("ix_training_sessions_repertoire_id", "training_sessions", ["repertoire_id"])
