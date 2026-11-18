"""Importing games: parsing, my side, de-duplication, indexing."""
from __future__ import annotations

from sqlalchemy import func, select

from app.core.models import Account, Game, GamePly
from app.services.chess_utils import START_KEY
from app.services.games.ingest import import_pgn_text, time_class_from_control
from tests.conftest import SAMPLE_PGN, pgn


def test_import_sets_my_side_and_result(sample_games):
    games = {g.opponent: g for g in sample_games.scalars(select(Game))}
    assert len(games) == 4
    assert (games["ann"].my_color, games["ann"].my_result) == ("white", "win")
    assert (games["bob"].my_color, games["bob"].my_result) == ("white", "loss")
    assert games["cat"].my_result == "draw"
    assert (games["dan"].my_color, games["dan"].my_result) == ("black", "win")
    assert games["bob"].opponent_elo == 1700
    assert games["bob"].time_class == "blitz"
    assert games["ann"].time_class == "rapid"


def test_importing_twice_does_not_duplicate(sample_games):
    counts = import_pgn_text(sample_games, SAMPLE_PGN)
    assert counts == {"found": 4, "imported": 0, "unknown_side": 0}
    assert sample_games.scalar(select(func.count(Game.id))) == 4


def test_plies_are_keyed_by_position(sample_games):
    first = sample_games.scalars(select(GamePly).where(GamePly.ply == 0)).all()
    assert {p.key_before for p in first} == {START_KEY}
    # Games A (e4 e5 Nf3 Nc6) and C (Nf3 Nc6 e4 e5) transpose: same key at ply 4.
    keys = sample_games.execute(
        select(GamePly.key_before, func.count()).where(GamePly.ply == 4, GamePly.san == "Bb5")
        .group_by(GamePly.key_before)
    ).all()
    assert len(keys) == 1 and keys[0][1] == 2


def test_opening_is_named_from_the_position(sample_games):
    games = {g.opponent: g for g in sample_games.scalars(select(Game))}
    assert games["ann"].opening_name.startswith("Ruy Lopez")
    assert games["bob"].opening_name.startswith("Italian Game")
    # Reached by transposition, still a Ruy Lopez.
    assert games["cat"].opening_name.startswith("Ruy Lopez")
    assert games["dan"].opening_name.startswith("Sicilian Defense")


def test_unknown_player_is_imported_without_side(db_session):
    counts = import_pgn_text(db_session, pgn("x", "y", "1-0", "1. d4 d5"))
    assert counts == {"found": 1, "imported": 1, "unknown_side": 1}


def test_player_name_identifies_me_in_a_file(db_session):
    import_pgn_text(db_session, pgn("Dupont, Jean", "y", "1-0", "1. d4 d5"), player="dupont, jean")
    assert db_session.scalar(select(Game.my_color)) == "white"


def test_pgn_from_either_site_matches_any_of_my_usernames(db_session):
    db_session.add_all([Account(platform="chesscom", username="A"), Account(platform="lichess", username="B")])
    db_session.commit()
    import_pgn_text(db_session, pgn("x", "b", "0-1", "1. d4 d5"))
    assert db_session.scalar(select(Game.my_color)) == "black"


def test_time_class_from_control():
    assert time_class_from_control("60") == "bullet"
    assert time_class_from_control("180+2") == "blitz"
    assert time_class_from_control("600") == "rapid"
    assert time_class_from_control("1800+30") == "classical"
    assert time_class_from_control("1/86400") == "daily"
    assert time_class_from_control("-") is None
