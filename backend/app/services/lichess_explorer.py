"""What other players choose in a position: the Lichess opening explorer.

Since early 2026 the explorer requires an authenticated request, so this only
works when `LICHESS_TOKEN` is configured. Answers are cached for a month:
opening statistics move slowly and the explorer asks for one request at a time.
"""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models import ExplorerCache, utcnow

CACHE_TTL = timedelta(days=30)
DEFAULT_SPEEDS = "blitz,rapid,classical"
RATING_BANDS = (0, 1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500)


class ExplorerUnavailable(RuntimeError):
    """Raised when the explorer cannot be queried."""


def is_configured() -> bool:
    return bool(settings.lichess_token)


def bands_around(rating: int) -> str:
    """The rating band containing `rating` and the one above it."""
    lower = max(b for b in RATING_BANDS if b <= max(rating, 0))
    index = RATING_BANDS.index(lower)
    return ",".join(str(b) for b in RATING_BANDS[index:index + 2])


def fetch(db: Session, fen: str, ratings: str, speeds: str = DEFAULT_SPEEDS) -> dict:
    """Statistics of Lichess games for a position, by move. Commits the cache."""
    if not is_configured():
        raise ExplorerUnavailable("Aucun jeton Lichess configuré (LICHESS_TOKEN).")
    cache_key = hashlib.sha1(f"{fen}|{ratings}|{speeds}".encode()).hexdigest()
    cached = db.get(ExplorerCache, cache_key)
    if cached is not None and cached.fetched_at > utcnow() - CACHE_TTL:
        return json.loads(cached.payload)
    try:
        resp = requests.get(
            f"{settings.lichess_explorer_base.rstrip('/')}/lichess",
            params={"variant": "standard", "fen": fen, "ratings": ratings, "speeds": speeds,
                    "moves": 12, "topGames": 0, "recentGames": 0},
            headers={"Authorization": f"Bearer {settings.lichess_token}",
                     "User-Agent": settings.http_user_agent},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise ExplorerUnavailable(f"Explorateur Lichess injoignable : {exc}") from exc
    if resp.status_code == 401:
        raise ExplorerUnavailable("Jeton Lichess refusé.")
    if resp.status_code == 429:
        raise ExplorerUnavailable("Lichess demande de patienter une minute.")
    if resp.status_code >= 400:
        raise ExplorerUnavailable(f"Lichess a répondu {resp.status_code}.")
    data = resp.json()
    total = data.get("white", 0) + data.get("draws", 0) + data.get("black", 0)
    payload = {
        "ratings": ratings,
        "speeds": speeds,
        "games": total,
        "white": data.get("white", 0),
        "draws": data.get("draws", 0),
        "black": data.get("black", 0),
        "moves": [
            {
                "san": m["san"],
                "uci": m["uci"],
                "games": m["white"] + m["draws"] + m["black"],
                "white": m["white"],
                "draws": m["draws"],
                "black": m["black"],
                "average_rating": m.get("averageRating"),
            }
            for m in data.get("moves", [])
        ],
    }
    if cached is None:
        db.add(ExplorerCache(cache_key=cache_key, payload=json.dumps(payload)))
    else:
        cached.payload, cached.fetched_at = json.dumps(payload), utcnow()
    db.commit()
    return payload
