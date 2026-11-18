"""Clients for the two playing sites: chess.com and Lichess."""
from __future__ import annotations

import io
import json
from collections.abc import Iterator
from datetime import datetime, timezone

import chess.pgn
import requests

from app.core.config import settings
from app.services.games.ingest import RawGame, raw_from_pgn_game


class SourceError(Exception):
    """Raised when a site cannot be reached or refuses the request."""


def _session() -> requests.Session:
    session = requests.Session()
    # Both sites answer 403 to clients that do not identify themselves.
    session.headers["User-Agent"] = settings.http_user_agent
    return session


def _from_epoch(seconds: float | None) -> datetime | None:
    if not seconds:
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)


# --- chess.com ---------------------------------------------------------------


class ChesscomClient:
    """Monthly archives of the chess.com public API.

    Requests are made one at a time: chess.com throttles parallel calls.
    """

    def __init__(self, session: requests.Session | None = None, timeout: int = 30) -> None:
        self.session = session or _session()
        self.timeout = timeout
        self.base = settings.chesscom_api_base.rstrip("/")

    def _get(self, url: str) -> dict:
        try:
            resp = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise SourceError(f"chess.com injoignable : {exc}") from exc
        if resp.status_code == 404:
            raise SourceError("Joueur chess.com introuvable.")
        if resp.status_code >= 400:
            raise SourceError(f"chess.com a répondu {resp.status_code}.")
        return resp.json()

    def archives(self, username: str) -> list[tuple[str, str]]:
        """Chronological list of (month "YYYY/MM", archive url)."""
        data = self._get(f"{self.base}/player/{username.strip().lower()}/games/archives")
        out: list[tuple[str, str]] = []
        for url in data.get("archives", []):
            parts = url.rstrip("/").rsplit("/", 2)
            if len(parts) == 3:
                out.append((f"{parts[1]}/{parts[2]}", url))
        return sorted(out)

    def games(self, archive_url: str) -> Iterator[RawGame]:
        for item in self._get(archive_url).get("games", []):
            raw = chesscom_game(item)
            if raw is not None:
                yield raw


def chesscom_game(item: dict) -> RawGame | None:
    """Convert one game of a chess.com archive; variants are skipped."""
    if item.get("rules", "chess") != "chess" or not item.get("pgn"):
        return None
    parsed = chess.pgn.read_game(io.StringIO(item["pgn"]))
    if parsed is None:
        return None
    raw = raw_from_pgn_game(
        parsed,
        platform="chesscom",
        external_id=str(item.get("uuid") or item.get("url")),
        url=item.get("url"),
    )
    if raw is None:
        return None
    white, black = item.get("white") or {}, item.get("black") or {}
    raw.white = white.get("username", raw.white)
    raw.black = black.get("username", raw.black)
    raw.white_elo = white.get("rating", raw.white_elo)
    raw.black_elo = black.get("rating", raw.black_elo)
    raw.time_class = item.get("time_class") or raw.time_class
    raw.rated = item.get("rated")
    raw.played_at = _from_epoch(item.get("end_time")) or raw.played_at
    return raw


# --- Lichess -----------------------------------------------------------------

_LICHESS_SPEED = {
    "ultraBullet": "bullet",
    "bullet": "bullet",
    "blitz": "blitz",
    "rapid": "rapid",
    "classical": "classical",
    "correspondence": "daily",
}
_UNFINISHED = {"created", "started", "aborted", "noStart", "unknownFinish"}


class LichessClient:
    """Streaming export of a player's games (NDJSON), oldest first."""

    def __init__(self, session: requests.Session | None = None, timeout: int = 60) -> None:
        self.session = session or _session()
        self.timeout = timeout
        self.base = settings.lichess_base.rstrip("/")
        if settings.lichess_token:
            self.session.headers["Authorization"] = f"Bearer {settings.lichess_token}"

    def games(self, username: str, since_ms: int | None = None) -> Iterator[tuple[RawGame, int]]:
        """Yield (game, creation time in ms) for standard games after `since_ms`."""
        params: dict[str, str] = {"moves": "true", "sort": "dateAsc"}
        if since_ms:
            params["since"] = str(since_ms + 1)
        try:
            resp = self.session.get(
                f"{self.base}/api/games/user/{username.strip()}",
                params=params,
                headers={"Accept": "application/x-ndjson"},
                stream=True,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise SourceError(f"Lichess injoignable : {exc}") from exc
        if resp.status_code == 404:
            raise SourceError("Joueur Lichess introuvable.")
        if resp.status_code == 429:
            raise SourceError("Lichess demande de patienter une minute avant de réessayer.")
        if resp.status_code >= 400:
            raise SourceError(f"Lichess a répondu {resp.status_code}.")
        try:
            for line in resp.iter_lines():
                if not line:
                    continue
                item = json.loads(line)
                raw = lichess_game(item, self.base)
                if raw is not None:
                    yield raw, int(item.get("createdAt") or 0)
        except requests.RequestException as exc:
            raise SourceError(f"Téléchargement Lichess interrompu : {exc}") from exc


def _lichess_player(side: dict) -> tuple[str, int | None]:
    user = side.get("user") or {}
    if "aiLevel" in side:
        return f"Stockfish niveau {side['aiLevel']}", None
    return user.get("name") or user.get("id") or "Anonyme", side.get("rating")


def lichess_game(item: dict, base: str = "https://lichess.org") -> RawGame | None:
    """Convert one game of the Lichess export; variants are skipped."""
    if item.get("variant", "standard") != "standard" or not item.get("moves"):
        return None
    if item.get("initialFen"):
        return None
    players = item.get("players") or {}
    white, white_elo = _lichess_player(players.get("white") or {})
    black, black_elo = _lichess_player(players.get("black") or {})
    winner = item.get("winner")
    if winner == "white":
        result = "1-0"
    elif winner == "black":
        result = "0-1"
    elif item.get("status") in _UNFINISHED:
        result = "*"
    else:
        result = "1/2-1/2"
    return RawGame(
        platform="lichess",
        external_id=item["id"],
        white=white,
        black=black,
        result=result,
        moves=item["moves"].split(),
        url=f"{base}/{item['id']}",
        white_elo=white_elo,
        black_elo=black_elo,
        time_class=_LICHESS_SPEED.get(item.get("speed", "")),
        rated=item.get("rated"),
        played_at=_from_epoch((item.get("createdAt") or 0) / 1000),
    )
