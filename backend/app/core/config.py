"""Application configuration loaded from environment variables."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root: backend/ is two levels up from this file's package dir... but
# config lives in backend/app/core, so the repo root is two parents above backend/.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database. Defaults to a SQLite file under the repo's data/ directory so the
    # app runs out-of-the-box without a configured database URL.
    database_url: str = f"sqlite:///{REPO_ROOT}/data/chessopeningflex.db"

    # Stockfish engine binary path. If None, the engine service falls back to a
    # "stockfish" lookup on PATH and disables analysis if unavailable.
    stockfish_path: str | None = None
    stockfish_depth: int = 15

    # chess.com pubapi base url
    chesscom_api_base: str = "https://api.chess.com/pub"

    # CORS: comma-separated list of allowed origins.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Data directories
    data_dir: Path = REPO_ROOT / "data"
    raw_pgn_dir: Path = REPO_ROOT / "data" / "raw"
    processed_pgn_dir: Path = REPO_ROOT / "data" / "processed"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()


def ensure_data_dirs() -> None:
    """Create the data directories if they don't exist yet."""
    settings.raw_pgn_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_pgn_dir.mkdir(parents=True, exist_ok=True)
