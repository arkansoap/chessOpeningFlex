"""Checking my games against my repertoire.

Each game is followed from the start. On my moves the repertoire is looked up:
a different move than the one I chose is a *deviation* (I forgot my line), a
position with no chosen move is a *gap* (the repertoire stops there, usually
after an opponent's move I have not prepared).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import COLORS, Game, GamePly, RepertoireEntry, utcnow
from app.services import openings
from app.services.explorer import GameFilters, game_summary
from app.services.repertoire.service import entries_by_key, get_repertoire


@dataclass
class GameReport:
    game_id: str
    status: str  # "covered" | "deviation" | "gap"
    ply: int = 0  # ply of the event
    line: list[str] = field(default_factory=list)  # moves before the event
    key: str | None = None
    played: str | None = None
    expected: str | None = None
    entry_id: str | None = None
    followed: int = 0  # how many of my moves matched the repertoire


def _load_plies(db: Session, color: str, conditions: list) -> dict[str, list[tuple]]:
    rows = db.execute(
        select(GamePly.game_id, GamePly.ply, GamePly.key_before, GamePly.san, GamePly.uci)
        .join(Game, Game.id == GamePly.game_id)
        .where(Game.my_color == color, *conditions)
        .order_by(GamePly.game_id, GamePly.ply)
    )
    games: dict[str, list[tuple]] = {}
    for game_id, ply, key, san, uci in rows:
        games.setdefault(game_id, []).append((ply, key, san, uci))
    return games


def check_game(color: str, plies: list[tuple], entries: dict[str, RepertoireEntry], game_id: str) -> GameReport:
    my_parity = 0 if color == "white" else 1
    line: list[str] = []
    followed = 0
    for ply, key, san, uci in plies:
        if ply % 2 == my_parity:
            entry = entries.get(key)
            if entry is None:
                return GameReport(game_id, "gap", ply, line, key, played=san, followed=followed)
            if entry.move_uci != uci:
                return GameReport(
                    game_id, "deviation", ply, line, key, played=san,
                    expected=entry.move_san, entry_id=entry.id, followed=followed,
                )
            followed += 1
        line = line + [san]
    return GameReport(game_id, "covered", len(plies), line, followed=followed)


def check_games(db: Session, color: str, conditions: list | None = None) -> list[GameReport]:
    rep = get_repertoire(db, color)
    entries = entries_by_key(db, rep)
    plies = _load_plies(db, color, conditions or [])
    return [check_game(color, game_plies, entries, gid) for gid, game_plies in plies.items()]


def coverage(db: Session, filters: GameFilters) -> dict:
    """How far my repertoire carries me, and where it stops most often."""
    # The colour condition comes first and is already applied by check_games.
    reports = check_games(db, filters.color, filters.conditions()[1:])
    played_at = dict(
        db.execute(select(Game.id, Game.played_at).where(*filters.conditions())).all()
    )
    total = len(reports)
    by_status = Counter(r.status for r in reports)

    gaps: dict[str, dict] = {}
    deviations: dict[str, dict] = {}
    for report in reports:
        when = played_at.get(report.game_id)
        if report.status == "gap":
            bucket = gaps.setdefault(
                report.key,
                {"key": report.key, "line": report.line, "games": 0, "played": Counter(),
                 "last_played": None},
            )
        elif report.status == "deviation":
            bucket = deviations.setdefault(
                report.entry_id,
                {"entry_id": report.entry_id, "key": report.key, "line": report.line,
                 "expected": report.expected, "games": 0, "played": Counter(),
                 "last_played": None},
            )
        else:
            continue
        bucket["games"] += 1
        bucket["played"][report.played] += 1
        if when and (bucket["last_played"] is None or when > bucket["last_played"]):
            bucket["last_played"] = when

    def finish(bucket: dict) -> dict:
        opening = openings.classify_line(bucket["line"])
        return {
            **bucket,
            "opening": opening.name if opening else None,
            "played": [{"san": san, "games": n} for san, n in bucket["played"].most_common(4)],
            "last_played": bucket["last_played"].isoformat() if bucket["last_played"] else None,
        }

    return {
        "color": filters.color,
        "games": total,
        "covered": by_status.get("covered", 0),
        "with_deviation": by_status.get("deviation", 0),
        "with_gap": by_status.get("gap", 0),
        # Average number of my own moves played "by the book" per game.
        "average_followed": round(sum(r.followed for r in reports) / total, 1) if total else 0.0,
        "gaps": sorted((finish(g) for g in gaps.values()), key=lambda g: -g["games"]),
        "deviations": sorted((finish(d) for d in deviations.values()), key=lambda d: -d["games"]),
    }


def review(db: Session, color: str, limit: int = 30) -> list[dict]:
    """My most recent games, each with the point where it left the repertoire."""
    games = list(
        db.scalars(
            select(Game)
            .where(Game.my_color == color)
            .order_by(Game.played_at.desc().nullslast())
            .limit(limit)
        )
    )
    if not games:
        return []
    ids = [g.id for g in games]
    reports = {r.game_id: r for r in check_games(db, color, [Game.id.in_(ids)])}
    out = []
    for game in games:
        report = reports.get(game.id)
        if report is None:
            continue
        out.append(
            {
                "game": game_summary(game),
                "status": report.status,
                "ply": report.ply,
                "line": report.line,
                "played": report.played,
                "expected": report.expected,
                "entry_id": report.entry_id,
                "followed": report.followed,
            }
        )
    return out


def flag_deviations(db: Session, game_ids: list[str]) -> int:
    """Send back to training the repertoire moves I got wrong in these games.

    Returns the number of entries flagged. Commits.
    """
    if not game_ids:
        return 0
    flagged: set[str] = set()
    now = utcnow()
    for color in COLORS:
        for start in range(0, len(game_ids), 500):
            chunk = game_ids[start:start + 500]
            for report in check_games(db, color, [Game.id.in_(chunk)]):
                if report.status != "deviation" or report.entry_id in flagged:
                    continue
                entry = db.get(RepertoireEntry, report.entry_id)
                if entry is None:
                    continue
                entry.srs_level = 0
                entry.due_at = now
                entry.lapses += 1
                flagged.add(entry.id)
    db.commit()
    return len(flagged)
