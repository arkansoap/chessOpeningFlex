"""Alembic migrations, including the conversion of legacy repertoire lines."""
from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.core.config import settings

BACKEND = Path(__file__).resolve().parents[1]


def _config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_converts_lines_and_downgrade_works(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migr.db'}"
    monkeypatch.setattr(settings, "database_url", url)
    cfg = _config(url)

    command.upgrade(cfg, "419e0e23fe81")
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO repertoires (id, name, color, is_active) VALUES ('r1', 'Noirs', 'black', 1)"
        ))
        conn.execute(sa.text(
            "INSERT INTO repertoire_lines (id, repertoire_id, moves, starting_position, comment, depth, priority) "
            "VALUES ('l1', 'r1', 'e4 c5 Nf3 d6 d4 cxd4', 'startpos', 'ma Sicilienne', 4, 0)"
        ))

    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT line_san, move_san, comment, source FROM repertoire_entries ORDER BY length(line_san)"
        )).fetchall()
        tables = set(sa.inspect(conn).get_table_names())
    # Depth 4 keeps "e4 c5 Nf3 d6": Black's two moves become two entries.
    assert rows == [("e4", "c5", None, "migrated"), ("e4 c5 Nf3", "d6", "ma Sicilienne", "migrated")]
    assert "repertoire_lines" not in tables and {"games", "game_plies", "accounts"} <= tables

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    engine.dispose()
