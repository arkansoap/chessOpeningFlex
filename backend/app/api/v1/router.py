"""Aggregated v1 API router."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import analysis, explorer, games, repertoire, training

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(games.router)
api_router.include_router(explorer.router)
api_router.include_router(analysis.router)
api_router.include_router(repertoire.router)
api_router.include_router(training.router)
