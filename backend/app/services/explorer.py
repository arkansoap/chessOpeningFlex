"""The tree of my games: what I play, how often, and how it goes.

Everything here reads `game_plies`, where each opening ply of each game is
keyed by the position it was played from. Grouping by that key merges all
games into one tree in which transpositions meet.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.models import Game, GamePly
from app.services import openings
from app.services.chess_utils import START_KEY, turn_of_key

TIME_CLASSES = ("bullet", "blitz", "rapid", "classical", "daily")


@dataclass(frozen=True)
class GameFilters:
    """Which of my games are taken into account."""

    color: str  # "white" | "black": the side I played
    time_classes: tuple[str, ...] = ()
    since: date | None = None
    until: date | None = None
    min_opponent_elo: int | None = None
    max_opponent_elo: int | None = None
    platform: str | None = None

    def conditions(self) -> list:
        conds = [Game.my_color == self.color]
        if self.time_classes:
            conds.append(Game.time_class.in_(self.time_classes))
        if self.since:
            conds.append(Game.played_at >= datetime.combine(self.since, datetime.min.time()))
        if self.until:
            conds.append(Game.played_at <= datetime.combine(self.until, datetime.max.time()))
        if self.min_opponent_elo is not None:
            conds.append(Game.opponent_elo >= self.min_opponent_elo)
        if self.max_opponent_elo is not None:
            conds.append(Game.opponent_elo <= self.max_opponent_elo)
        if self.platform:
            conds.append(Game.platform == self.platform)
        return conds


@dataclass
class Edge:
    """A move played from a position, aggregated over my games."""

    key_before: str
    key_after: str
    san: str
    uci: str
    games: int
    wins: int
    draws: int
    losses: int
    last_played: datetime | None = None

    @property
    def score(self) -> float:
        """My score with this move, in percent."""
        decided = self.wins + self.draws + self.losses
        return 100 * (self.wins + 0.5 * self.draws) / decided if decided else 0.0

    def as_dict(self) -> dict:
        return {
            "san": self.san,
            "uci": self.uci,
            "key_after": self.key_after,
            "games": self.games,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "score": round(self.score, 1),
            "last_played": self.last_played.isoformat() if self.last_played else None,
        }


def _won(result: str):
    return func.sum(case((Game.my_result == result, 1), else_=0))


def _edge_query(filters: GameFilters):
    return (
        select(
            GamePly.key_before,
            GamePly.key_after,
            func.min(GamePly.san),
            GamePly.uci,
            func.count(func.distinct(GamePly.game_id)),
            _won("win"),
            _won("draw"),
            _won("loss"),
            func.max(Game.played_at),
        )
        .join(Game, Game.id == GamePly.game_id)
        .where(*filters.conditions())
        .group_by(GamePly.key_before, GamePly.uci, GamePly.key_after)
    )


def moves_from(db: Session, key: str, filters: GameFilters) -> list[Edge]:
    """Moves played from one position, most frequent first."""
    rows = db.execute(_edge_query(filters).where(GamePly.key_before == key)).all()
    edges = [Edge(*row) for row in rows]
    edges.sort(key=lambda e: (-e.games, e.san))
    return edges


@dataclass
class Graph:
    """The whole aggregated tree of my games for one colour."""

    color: str
    edges: dict[str, list[Edge]] = field(default_factory=dict)
    # Shortest known path from the start to each position, as SAN moves.
    _paths: dict[str, list[str]] | None = None

    def moves(self, key: str) -> list[Edge]:
        return self.edges.get(key, [])

    def games_at(self, key: str) -> int:
        return sum(e.games for e in self.moves(key))

    def paths(self) -> dict[str, list[str]]:
        """Breadth-first search from the start position."""
        if self._paths is None:
            paths: dict[str, list[str]] = {START_KEY: []}
            queue = deque([START_KEY])
            while queue:
                key = queue.popleft()
                for edge in self.moves(key):
                    if edge.key_after not in paths:
                        paths[edge.key_after] = paths[key] + [edge.san]
                        queue.append(edge.key_after)
            self._paths = paths
        return self._paths

    def line_to(self, key: str) -> list[str] | None:
        return self.paths().get(key)

    def is_my_turn(self, key: str) -> bool:
        return turn_of_key(key) == self.color


def load_graph(db: Session, filters: GameFilters) -> Graph:
    """Aggregate every indexed ply of my games in one query."""
    graph = Graph(color=filters.color)
    for row in db.execute(_edge_query(filters)):
        edge = Edge(*row)
        graph.edges.setdefault(edge.key_before, []).append(edge)
    for edges in graph.edges.values():
        edges.sort(key=lambda e: (-e.games, e.san))
    return graph


def games_through(db: Session, key: str, filters: GameFilters, limit: int = 10) -> list[dict]:
    """Most recent games of mine that reached a position."""
    if key == START_KEY:
        stmt = select(Game).where(*filters.conditions())
    else:
        stmt = (
            select(Game)
            .join(GamePly, GamePly.game_id == Game.id)
            .where(GamePly.key_after == key, *filters.conditions())
            .distinct()
        )
    stmt = stmt.order_by(Game.played_at.desc().nullslast()).limit(limit)
    return [game_summary(g) for g in db.scalars(stmt)]


def game_summary(game: Game) -> dict:
    return {
        "id": game.id,
        "platform": game.platform,
        "url": game.url,
        "white": game.white,
        "black": game.black,
        "white_elo": game.white_elo,
        "black_elo": game.black_elo,
        "opponent": game.opponent,
        "opponent_elo": game.opponent_elo,
        "my_color": game.my_color,
        "my_result": game.my_result,
        "result": game.result,
        "time_class": game.time_class,
        "played_at": game.played_at.isoformat() if game.played_at else None,
        "eco": game.eco,
        "opening_name": game.opening_name,
        "ply_count": game.ply_count,
    }


def openings_summary(db: Session, filters: GameFilters) -> list[dict]:
    """My results opening by opening, grouped by family.

    "Sicilian Defense: Najdorf Variation" and "Sicilian Defense: Alapin
    Variation" are two variations of the family "Sicilian Defense".
    """
    rows = db.execute(
        select(
            Game.opening_name,
            func.min(Game.eco),
            func.count(Game.id),
            _won("win"),
            _won("draw"),
            _won("loss"),
            func.max(Game.played_at),
        )
        .where(*filters.conditions())
        .group_by(Game.opening_name)
    ).all()

    families: dict[str, dict] = {}
    for name, eco, games, wins, draws, losses, last_played in rows:
        label = name or "Sans nom"
        family_name = label.split(":")[0].strip()
        family = families.setdefault(
            family_name,
            {"family": family_name, "games": 0, "wins": 0, "draws": 0, "losses": 0,
             "variations": []},
        )
        for field_name, value in (("games", games), ("wins", wins), ("draws", draws), ("losses", losses)):
            family[field_name] += value
        family["variations"].append(
            {
                "name": label,
                "eco": eco,
                "line": openings.line_of(label),
                "games": games,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "score": _score(wins, draws, losses),
                "last_played": last_played.isoformat() if last_played else None,
            }
        )
    out = []
    for family in families.values():
        family["score"] = _score(family["wins"], family["draws"], family["losses"])
        family["variations"].sort(key=lambda v: -v["games"])
        # A family opens on its shortest line, i.e. its root position.
        with_line = [v for v in family["variations"] if v["line"]]
        family["line"] = min((v["line"] for v in with_line), key=len, default="")
        out.append(family)
    out.sort(key=lambda f: -f["games"])
    return out


def _score(wins: int, draws: int, losses: int) -> float:
    decided = wins + draws + losses
    return round(100 * (wins + 0.5 * draws) / decided, 1) if decided else 0.0


def totals(db: Session) -> dict:
    """Counts of imported games, for the home page."""
    rows = db.execute(
        select(Game.platform, Game.my_color, func.count(Game.id)).group_by(
            Game.platform, Game.my_color
        )
    ).all()
    by_platform: dict[str, int] = {}
    by_color = {"white": 0, "black": 0, "unknown": 0}
    for platform, color, count in rows:
        by_platform[platform] = by_platform.get(platform, 0) + count
        by_color[color or "unknown"] += count
    last = db.scalar(select(func.max(Game.played_at)))
    return {
        "games": sum(by_platform.values()),
        "by_platform": by_platform,
        "by_color": by_color,
        "last_played": last.isoformat() if last else None,
    }
