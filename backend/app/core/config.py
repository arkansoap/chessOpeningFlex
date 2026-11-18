"""Application configuration loaded from environment variables."""
from __future__ import annotations

import shutil
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# config lives in backend/app/core, so the repo root is three parents up.
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database. Defaults to a SQLite file under the repo's data/ directory so the
    # app runs out-of-the-box without a configured database URL.
    database_url: str = f"sqlite:///{REPO_ROOT}/data/chessopeningflex.db"

    # Stockfish engine binary. When unset we look for the copy installed by
    # `scripts/fetch_stockfish.py`, then for `stockfish` on PATH.
    stockfish_path: str | None = None
    # Depth of the batch analysis of opening positions.
    analysis_depth: int = 16
    analysis_threads: int = 4
    analysis_hash_mb: int = 128

    # How many plies of each game are indexed in the opening tree (40 = 20 moves).
    max_indexed_plies: int = 40
    # The batch analysis stops at this ply: beyond it positions rarely repeat.
    max_analysed_plies: int = 30

    # External services.
    chesscom_api_base: str = "https://api.chess.com/pub"
    lichess_base: str = "https://lichess.org"
    lichess_explorer_base: str = "https://explorer.lichess.org"
    # Personal Lichess API token. Optional for importing games (it only raises
    # the download speed), required for the opening explorer statistics.
    lichess_token: str | None = None
    # Identifies this app to chess.com and Lichess, which both reject
    # anonymous clients.
    http_user_agent: str = "ChessOpeningFlex/0.2 (https://github.com/arkansoap/chessOpeningFlex)"

    # CORS: comma-separated list of allowed origins.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Data directory (SQLite database, uploads).
    data_dir: Path = REPO_ROOT / "data"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_stockfish_path(self) -> str | None:
        """Path of a usable engine binary, or None when there is none."""
        if self.stockfish_path:
            found = shutil.which(self.stockfish_path)
            return found or (self.stockfish_path if Path(self.stockfish_path).exists() else None)
        bundled = BACKEND_ROOT / ".tools" / "stockfish" / "stockfish"
        if bundled.exists():
            return str(bundled)
        return shutil.which("stockfish")


settings = Settings()


def ensure_data_dirs() -> None:
    """Create the data directory if it doesn't exist yet."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
