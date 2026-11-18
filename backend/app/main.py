"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import ensure_data_dirs, settings
from app.core.database import run_migrations
from app.services.analysis.engine import engine_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dirs()
    run_migrations()
    logger.info("Database migrations applied")
    yield
    engine_service.close()


app = FastAPI(
    title="ChessOpeningFlex API",
    version="0.2.0",
    description="Build an opening repertoire from your own games, and train it.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
