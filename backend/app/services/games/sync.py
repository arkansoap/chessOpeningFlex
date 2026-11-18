"""Incremental import of my games from chess.com and Lichess."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.models import Account, utcnow
from app.services import jobs
from app.services.games.ingest import ingest, my_usernames
from app.services.games.sources import ChesscomClient, LichessClient

logger = logging.getLogger(__name__)

PLATFORMS = ("chesscom", "lichess")
PLATFORM_LABELS = {"chesscom": "chess.com", "lichess": "Lichess"}


def _months_ago(months: int, now: datetime | None = None) -> str:
    """"YYYY/MM" of the month `months` months before now."""
    now = now or utcnow()
    index = now.year * 12 + (now.month - 1) - months
    return f"{index // 12:04d}/{index % 12 + 1:02d}"


def sync_chesscom(
    db: Session,
    account: Account,
    state: jobs.JobState,
    client: ChesscomClient | None = None,
    months: int | None = None,
) -> list[str]:
    """Fetch the archives not seen yet. Returns the ids of the new games.

    The month of the last sync is always fetched again: it was still filling
    up when we read it.
    """
    client = client or ChesscomClient()
    usernames = my_usernames(db)
    archives = client.archives(account.username)
    start = account.sync_cursor
    if start is None and months:
        start = _months_ago(months)
    if start:
        archives = [a for a in archives if a[0] >= start]
    state.total += len(archives)
    new_ids: list[str] = []
    for month, url in archives:
        if state.stop_requested:
            break
        state.message = f"chess.com : {month.replace('/', '-')}"
        for raw in client.games(url):
            game = ingest(db, raw, usernames)
            if game is not None:
                db.flush()
                new_ids.append(game.id)
        account.sync_cursor = month
        account.last_synced_at = utcnow()
        db.commit()
        state.done += 1
        state.result["chesscom"] = len(new_ids)
    return new_ids


def sync_lichess(
    db: Session,
    account: Account,
    state: jobs.JobState,
    client: LichessClient | None = None,
    months: int | None = None,
) -> list[str]:
    """Stream the games created since the last sync, oldest first."""
    client = client or LichessClient()
    usernames = my_usernames(db)
    since = int(account.sync_cursor) if account.sync_cursor else None
    if since is None and months:
        year, month = _months_ago(months).split("/")
        since = int(datetime(int(year), int(month), 1).timestamp() * 1000)
    new_ids: list[str] = []
    seen = 0
    state.message = "Lichess : téléchargement…"
    for raw, created_ms in client.games(account.username, since):
        seen += 1
        game = ingest(db, raw, usernames)
        if game is not None:
            db.flush()
            new_ids.append(game.id)
        if created_ms:
            account.sync_cursor = str(created_ms)
        if seen % 100 == 0:
            db.commit()
            state.message = f"Lichess : {seen} parties lues"
            state.result["lichess"] = len(new_ids)
            if state.stop_requested:
                break
    account.last_synced_at = utcnow()
    db.commit()
    state.result["lichess"] = len(new_ids)
    return new_ids


def run_sync(db: Session, state: jobs.JobState, platforms: list[str], months: int | None) -> None:
    """Sync the requested platforms, then check the new games against the
    repertoire so that the moves I got wrong come back in training."""
    from app.services.repertoire.coverage import flag_deviations

    new_ids: list[str] = []
    errors: list[str] = []
    for platform in platforms:
        account = db.get(Account, platform)
        if account is None:
            continue
        try:
            if platform == "chesscom":
                new_ids += sync_chesscom(db, account, state, months=months)
            else:
                new_ids += sync_lichess(db, account, state, months=months)
        except Exception as exc:  # noqa: BLE001 - one site failing must not hide the other
            db.rollback()
            logger.warning("Sync %s failed: %s", platform, exc)
            errors.append(f"{PLATFORM_LABELS[platform]} : {exc}")
    state.result["imported"] = len(new_ids)
    state.result["deviations"] = flag_deviations(db, new_ids) if new_ids else 0
    if errors:
        state.result["errors"] = errors
        if not new_ids:
            raise RuntimeError(" ; ".join(errors))
    state.message = f"{len(new_ids)} nouvelle(s) partie(s)"


def start_sync(platforms: list[str] | None = None, months: int | None = None) -> tuple[jobs.JobState, bool]:
    """Launch the sync in the background."""
    from app.core.database import SessionLocal

    wanted = [p for p in (platforms or PLATFORMS) if p in PLATFORMS]

    def target(state: jobs.JobState) -> None:
        db = SessionLocal()
        try:
            run_sync(db, state, wanted, months)
        finally:
            db.close()

    return jobs.start("sync", target)
