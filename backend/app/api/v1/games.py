"""Accounts, synchronisation and imported games."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import ColorParam
from app.core.database import get_db
from app.core.models import Account, Game
from app.core.schemas import AccountsIn, SyncIn
from app.services import explorer, jobs
from app.services.games import sync as sync_service
from app.services.games.ingest import import_pgn_text
from app.services.repertoire.coverage import flag_deviations

router = APIRouter(tags=["games"])


def _accounts(db: Session) -> dict:
    out: dict[str, dict | None] = {p: None for p in sync_service.PLATFORMS}
    for account in db.scalars(select(Account)):
        out[account.platform] = {
            "username": account.username,
            "last_synced_at": account.last_synced_at.isoformat() if account.last_synced_at else None,
        }
    return out


@router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)) -> dict:
    return _accounts(db)


@router.put("/accounts")
def set_accounts(payload: AccountsIn, db: Session = Depends(get_db)) -> dict:
    """Set or clear my usernames. Changing one restarts its sync from scratch."""
    for platform in sync_service.PLATFORMS:
        if platform not in payload.model_fields_set:
            continue
        username = (getattr(payload, platform) or "").strip()
        account = db.get(Account, platform)
        if not username:
            if account is not None:
                db.delete(account)
        elif account is None:
            db.add(Account(platform=platform, username=username))
        elif account.username.lower() != username.lower():
            account.username = username
            account.sync_cursor = None
            account.last_synced_at = None
    db.commit()
    return _accounts(db)


@router.post("/sync")
def start_sync(payload: SyncIn, db: Session = Depends(get_db)) -> dict:
    wanted = payload.platforms or list(sync_service.PLATFORMS)
    if not any(db.get(Account, p) for p in wanted):
        raise HTTPException(400, "Renseignez d'abord un nom d'utilisateur chess.com ou Lichess.")
    state, _started = sync_service.start_sync(wanted, payload.months)
    return state.as_dict()


@router.get("/sync/status")
def sync_status() -> dict:
    return jobs.get("sync").as_dict()


@router.post("/sync/stop")
def stop_sync() -> dict:
    return jobs.request_stop("sync").as_dict()


@router.get("/games/summary")
def games_summary(db: Session = Depends(get_db)) -> dict:
    return explorer.totals(db)


@router.get("/games")
def list_games(
    color: ColorParam | None = Query(None),
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(Game).order_by(Game.played_at.desc().nullslast()).limit(limit)
    if color:
        stmt = stmt.where(Game.my_color == color)
    return [explorer.game_summary(g) for g in db.scalars(stmt)]


@router.post("/games/upload-pgn", status_code=201)
async def upload_pgn(
    request: Request,
    player: str | None = Query(None, description="My name in this file, if not a site username"),
    db: Session = Depends(get_db),
) -> dict:
    """Import the games of a PGN sent as the raw request body."""
    raw = await request.body()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # PGN exports from older tools are frequently latin-1.
        text = raw.decode("latin-1")
    if not text.strip():
        raise HTTPException(400, "Le PGN est vide.")
    before = {gid for (gid,) in db.execute(select(Game.id))}
    counts = import_pgn_text(db, text, player)
    if counts["found"] == 0:
        raise HTTPException(400, "Aucune partie lisible dans ce PGN.")
    new_ids = [gid for (gid,) in db.execute(select(Game.id)) if gid not in before]
    counts["deviations"] = flag_deviations(db, new_ids)
    return counts
