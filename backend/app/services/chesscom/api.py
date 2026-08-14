"""chess.com pubapi client."""
from __future__ import annotations

import logging
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChesscomError(Exception):
    """Raised when chess.com API requests fail."""


class ChesscomClient:
    """Thin wrapper around the chess.com public API."""

    # chess.com requires a User-Agent header on all requests, otherwise it
    # responds with 403 Forbidden. We set it once on a shared session.
    USER_AGENT = "ChessOpeningFlex/0.1 (https://github.com/arkansoap/chessOpeningFlex)"

    def __init__(self, base_url: str | None = None, timeout: int = 30) -> None:
        self.base_url = (base_url or settings.chesscom_api_base).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:  # pragma: no cover - network
            raise ChesscomError(f"chess.com request failed: {exc}") from exc

    def list_archives(self, username: str) -> list[str]:
        """Return the list of monthly archive URLs for a player."""
        username = username.strip()
        data = self._get(f"player/{username}/games/archives")
        return list(data.get("archives", []))

    def fetch_archive(self, archive_url: str) -> list[dict]:
        """Fetch the games for one monthly archive URL."""
        try:
            resp = self.session.get(archive_url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:  # pragma: no cover - network
            raise ChesscomError(f"chess.com archive fetch failed: {exc}") from exc
        return list(data.get("games", []))

    def fetch_games(
        self,
        username: str,
        time_control: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """Fetch games for a player, optionally filtered.

        Filters:
        - time_control: chess.com time class ("rapid", "blitz", "bullet", "daily")
        - start_date / end_date: "YYYY-MM" inclusive bounds on the monthly archive.
        """
        archives = self.list_archives(username)
        selected: list[str] = []
        for url in archives:
            # archive urls end with /YYYY/MM
            tail = url.rstrip("/").rsplit("/", 2)
            if len(tail) == 3:
                year_str, month_str = tail[1], tail[2]
                key = f"{year_str}-{month_str}"
                if start_date and key < start_date:
                    continue
                if end_date and key > end_date:
                    continue
            selected.append(url)

        games: list[dict] = []
        for url in selected:
            games.extend(self.fetch_archive(url))

        if time_control:
            games = [g for g in games if g.get("time_class") == time_control]
        return games


def build_imported_game_dicts(
    username: str, games: list[dict]
) -> list[dict]:
    """Convert raw chess.com game dicts into ImportedGame-compatible dicts."""
    out: list[dict] = []
    for g in games:
        pgn = g.get("pgn") or ""
        if not pgn.strip():
            continue
        out.append(
            {
                "source": "chess_com_api",
                "chesscom_username": username,
                "pgn_file_path": None,
                "game_id": str(
                    g.get("uuid") or g.get("url") or g.get("end_time") or ""
                ),
                "white_player": (g.get("white", {}) or {}).get("username", "?"),
                "black_player": (g.get("black", {}) or {}).get("username", "?"),
                "result": g.get("pgn", "") and _result_from_pgn(pgn) or g.get("pgn", "") or "",
                "date": _date_from_pgn(pgn),
                "eco_code": _eco_from_pgn(pgn),
                "pgn_data": pgn,
                "is_processed": False,
            }
        )
    return out


def _result_from_pgn(pgn: str) -> str:
    """Best-effort extraction of the Result header value."""
    return _header(pgn, "Result") or ""


def _date_from_pgn(pgn: str) -> str | None:
    val = _header(pgn, "UTCDate") or _header(pgn, "Date")
    return val or None


def _eco_from_pgn(pgn: str) -> str | None:
    val = _header(pgn, "ECO")
    return val or None


def _header(pgn: str, name: str) -> str | None:
    import re

    m = re.search(rf'\[{name}\s+"(.*?)"\]', pgn)
    return m.group(1) if m else None
