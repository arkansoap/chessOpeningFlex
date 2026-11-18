"""Turning a raw game from any source into indexed rows."""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from datetime import datetime

import chess
import chess.pgn
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models import Account, Game, GamePly
from app.services import openings
from app.services.chess_utils import position_key


@dataclass
class RawGame:
    """A game as read from a source, before indexing."""

    platform: str
    external_id: str
    white: str
    black: str
    result: str = "*"
    moves: list[str] = field(default_factory=list)  # SAN, from the start position
    url: str | None = None
    white_elo: int | None = None
    black_elo: int | None = None
    time_class: str | None = None
    rated: bool | None = None
    played_at: datetime | None = None


def my_usernames(db: Session) -> dict[str, str]:
    """Lower-cased usernames of my accounts, by platform."""
    return {a.platform: a.username.lower() for a in db.scalars(select(Account))}


def _my_color(raw: RawGame, usernames: dict[str, str]) -> str | None:
    """Which side I played. A PGN file may come from either site, or carry
    my real name: any known name is accepted for it."""
    if raw.platform in usernames:
        candidates = {usernames[raw.platform]}
    else:
        candidates = set(usernames.values())
    if raw.white.lower() in candidates:
        return "white"
    if raw.black.lower() in candidates:
        return "black"
    return None


def _my_result(result: str, my_color: str | None) -> str | None:
    if my_color is None or result not in ("1-0", "0-1", "1/2-1/2"):
        return None
    if result == "1/2-1/2":
        return "draw"
    won = (result == "1-0") == (my_color == "white")
    return "win" if won else "loss"


def ingest(db: Session, raw: RawGame, usernames: dict[str, str]) -> Game | None:
    """Store a game and index its opening plies.

    Returns None when the game is already known or has no playable move.
    The caller commits.
    """
    exists = db.scalar(
        select(Game.id).where(
            Game.platform == raw.platform, Game.external_id == raw.external_id
        )
    )
    if exists:
        return None

    board = chess.Board()
    plies: list[GamePly] = []
    keys: list[str] = []
    sans: list[str] = []
    for index, san in enumerate(raw.moves):
        try:
            move = board.parse_san(san)
        except ValueError:
            break  # corrupt tail: keep what could be read
        key_before = position_key(board)
        clean_san = board.san(move)
        board.push(move)
        sans.append(clean_san)
        if index < settings.max_indexed_plies:
            key_after = position_key(board)
            keys.append(key_after)
            plies.append(
                GamePly(
                    ply=index,
                    key_before=key_before,
                    key_after=key_after,
                    san=clean_san,
                    uci=move.uci(),
                )
            )
    if not sans:
        return None

    my_color = _my_color(raw, usernames)
    opening = openings.classify(keys)
    if my_color == "white":
        opponent, opponent_elo = raw.black, raw.black_elo
    elif my_color == "black":
        opponent, opponent_elo = raw.white, raw.white_elo
    else:
        opponent, opponent_elo = None, None

    game = Game(
        platform=raw.platform,
        external_id=raw.external_id,
        url=raw.url,
        white=raw.white,
        black=raw.black,
        white_elo=raw.white_elo,
        black_elo=raw.black_elo,
        result=raw.result,
        my_color=my_color,
        my_result=_my_result(raw.result, my_color),
        opponent=opponent,
        opponent_elo=opponent_elo,
        time_class=raw.time_class,
        rated=raw.rated,
        played_at=raw.played_at,
        eco=opening.eco if opening else None,
        opening_name=opening.name if opening else None,
        moves_san=" ".join(sans),
        ply_count=len(sans),
        plies=plies,
    )
    db.add(game)
    return game


# --- PGN parsing ------------------------------------------------------------


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def time_class_from_control(time_control: str | None) -> str | None:
    """Classify a PGN TimeControl header ("600+5", "1/86400", "-")."""
    if not time_control or time_control in ("-", "?"):
        return None
    if "/" in time_control:
        return "daily"
    base, _, increment = time_control.partition("+")
    try:
        estimated = int(base) + 40 * int(increment or 0)
    except ValueError:
        return None
    if estimated < 180:
        return "bullet"
    if estimated < 480:
        return "blitz"
    if estimated < 1500:
        return "rapid"
    return "classical"


def _played_at(headers: chess.pgn.Headers) -> datetime | None:
    date = headers.get("UTCDate") or headers.get("Date") or ""
    time = headers.get("UTCTime") or "00:00:00"
    try:
        return datetime.strptime(f"{date} {time}", "%Y.%m.%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(date, "%Y.%m.%d")
        except ValueError:
            return None


def raw_from_pgn_game(
    game: chess.pgn.Game,
    platform: str = "pgn",
    external_id: str | None = None,
    url: str | None = None,
) -> RawGame | None:
    """Convert a parsed PGN game. Non-standard starts and variants are skipped."""
    headers = game.headers
    if headers.get("Variant", "Standard").lower() not in ("standard", "chess", "from position"):
        return None
    if "FEN" in headers and headers["FEN"] != chess.STARTING_FEN:
        return None
    board = game.board()
    moves: list[str] = []
    for move in game.mainline_moves():
        moves.append(board.san(move))
        board.push(move)
    if not moves:
        return None
    if external_id is None:
        # Stable across imports and restarts, unlike Python's salted hash().
        fingerprint = "|".join(
            [headers.get("White", ""), headers.get("Black", ""), headers.get("Date", ""),
             headers.get("UTCTime", ""), " ".join(moves)]
        )
        external_id = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()
    link = url or headers.get("Link") or headers.get("Site")
    if link and not link.startswith("http"):
        link = None
    event = headers.get("Event", "").lower()
    return RawGame(
        platform=platform,
        external_id=external_id,
        white=headers.get("White", "?"),
        black=headers.get("Black", "?"),
        result=headers.get("Result", "*"),
        moves=moves,
        url=link,
        white_elo=_int(headers.get("WhiteElo")),
        black_elo=_int(headers.get("BlackElo")),
        time_class=time_class_from_control(headers.get("TimeControl")),
        rated=("rated" in event) if event else None,
        played_at=_played_at(headers),
    )


def iter_pgn(text: str):
    """Yield the games of a PGN text, skipping those that fail to parse."""
    stream = io.StringIO(text)
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            return
        yield game


def import_pgn_text(db: Session, text: str, player: str | None = None) -> dict:
    """Import every game of a PGN text. Returns counts.

    `player` is the name I appear under in this file, when it is not one of
    my site usernames (over-the-board games, for instance).
    """
    usernames = my_usernames(db)
    if player and player.strip():
        usernames["_file"] = player.strip().lower()
    found = imported = unknown_side = 0
    for parsed in iter_pgn(text):
        raw = raw_from_pgn_game(parsed)
        if raw is None:
            continue
        found += 1
        game = ingest(db, raw, usernames)
        if game is not None:
            imported += 1
            if game.my_color is None:
                unknown_side += 1
    db.commit()
    return {"found": found, "imported": imported, "unknown_side": unknown_side}
