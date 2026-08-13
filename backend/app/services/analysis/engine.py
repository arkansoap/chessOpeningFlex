"""Stockfish engine integration, with a graceful fallback when unavailable."""
from __future__ import annotations

import logging
from typing import Any

import chess
import chess.engine

from app.core.config import settings

logger = logging.getLogger(__name__)


class EngineUnavailable(RuntimeError):
    """Raised when no Stockfish binary is available."""


class EngineService:
    """Wraps the python `stockfish` package if available; otherwise a
    python-chess UCI fallback is used. If neither engine is available the
    service reports itself as disabled so callers can degrade gracefully.
    """

    def __init__(self) -> None:
        self._engine: Any | None = None
        self._disabled = False
        self._init_engine()

    def _init_engine(self) -> None:
        # Prefer the `stockfish` package wrapper.
        try:
            from stockfish import Stockfish  # type: ignore

            path = settings.stockfish_path
            try:
                self._engine = Stockfish(path) if path else Stockfish()
                logger.info("Stockfish engine loaded via stockfish package")
                return
            except Exception as exc:  # pragma: no cover - env dependent
                logger.warning("stockfish package init failed: %s", exc)
        except ImportError:
            logger.info("stockfish package not installed; trying UCI fallback")

        # Fallback: python-chess engine protocol (needs a binary on PATH).
        try:
            path = settings.stockfish_path or "stockfish"
            self._engine = chess.engine.SimpleEngine.popen_uci(path)
            logger.info("Stockfish engine loaded via UCI: %s", path)
        except Exception as exc:  # pragma: no cover - env dependent
            logger.warning("No usable Stockfish binary (%s); analysis disabled", exc)
            self._engine = None
            self._disabled = True

    @property
    def available(self) -> bool:
        return self._engine is not None and not self._disabled

    def evaluate(
        self, fen: str, depth: int | None = None
    ) -> dict:
        """Return an evaluation dict: score (centipawns, white POV),
        depth, best_move (SAN), mate (plies, signed)."""
        depth = depth or settings.stockfish_depth
        if not self.available:
            return {
                "fen": fen,
                "score": 0.0,
                "depth": 0,
                "best_move": None,
                "mate": None,
                "available": False,
            }
        board = chess.Board(fen)

        if self._is_stockfish_pkg():
            self._engine.set_fen_position(fen)
            sf = self._engine
            info = sf.get_evaluation()
            best_move_uci = sf.get_best_move()
            best_move_san = (
                board.san(chess.Move.from_uci(best_move_uci))
                if best_move_uci
                else None
            )
            if info.get("type") == "cp":
                score = float(info.get("value", 0.0))
                # score is from side-to-move POV; normalize to white POV
                if board.turn == chess.BLACK:
                    score = -score
                return {
                    "fen": fen,
                    "score": score,
                    "depth": depth,
                    "best_move": best_move_san,
                    "mate": None,
                    "available": True,
                }
            elif info.get("type") == "mate":
                mate = int(info.get("value", 0))
                if board.turn == chess.BLACK:
                    mate = -mate
                return {
                    "fen": fen,
                    "score": 0.0,
                    "depth": depth,
                    "best_move": best_move_san,
                    "mate": mate,
                    "available": True,
                }
            return {
                "fen": fen,
                "score": 0.0,
                "depth": depth,
                "best_move": best_move_san,
                "mate": None,
                "available": True,
            }
        # UCI fallback
        info = self._engine.analyse(board, chess.engine.Limit(depth=depth))
        pov = info.get("score")
        best_move = info.get("pv", [None])[0] if info.get("pv") else None
        best_move_san = board.san(best_move) if best_move else None
        if pov is None:
            return {
                "fen": fen,
                "score": 0.0,
                "depth": depth,
                "best_move": best_move_san,
                "mate": None,
                "available": True,
            }
        white_score = pov.white()
        if white_score.is_mate():
            return {
                "fen": fen,
                "score": 0.0,
                "depth": depth,
                "best_move": best_move_san,
                "mate": white_score.mate(),
                "available": True,
            }
        return {
            "fen": fen,
            "score": float(white_score.score()),
            "depth": depth,
            "best_move": best_move_san,
            "mate": None,
            "available": True,
        }

    def _is_stockfish_pkg(self) -> bool:
        return self._engine.__class__.__module__.startswith("stockfish")


# Singleton used across requests.
engine_service = EngineService()
