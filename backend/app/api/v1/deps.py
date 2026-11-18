"""Shared request parameters."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import Query

from app.services.explorer import TIME_CLASSES, GameFilters

ColorParam = Literal["white", "black"]


def game_filters(
    color: ColorParam = Query(..., description="Side I played"),
    time_class: str | None = Query(None, description="Comma-separated: bullet,blitz,rapid,classical,daily"),
    since: date | None = Query(None),
    until: date | None = Query(None),
    min_elo: int | None = Query(None, ge=0, description="Minimum opponent rating"),
    max_elo: int | None = Query(None, ge=0, description="Maximum opponent rating"),
    platform: Literal["chesscom", "lichess", "pgn"] | None = Query(None),
) -> GameFilters:
    classes = tuple(c for c in (time_class or "").split(",") if c in TIME_CLASSES)
    return GameFilters(
        color=color,
        time_classes=classes,
        since=since,
        until=until,
        min_opponent_elo=min_elo,
        max_opponent_elo=max_elo,
        platform=platform,
    )
