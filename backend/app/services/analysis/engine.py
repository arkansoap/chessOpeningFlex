"""Native Stockfish, driven over UCI, with a cache of evaluations.

The engine process is started on first use and shared; a lock serialises the
searches. When no binary is available the service reports itself unavailable
and callers degrade gracefully (the browser keeps its own WASM engine).
"""
from __future__ import annotations

import logging
import os
import threading

import chess
import chess.engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models import PositionEval, utcnow
from app.services.chess_utils import position_key

logger = logging.getLogger(__name__)


class EngineUnavailable(RuntimeError):
    """Raised when no Stockfish binary can be started."""


class EngineService:
    def __init__(self) -> None:
        self._engine: chess.engine.SimpleEngine | None = None
        self._lock = threading.Lock()

    @property
    def path(self) -> str | None:
        return settings.resolved_stockfish_path

    @property
    def available(self) -> bool:
        return self.path is not None

    def _ensure(self) -> chess.engine.SimpleEngine:
        if self._engine is None:
            path = self.path
            if path is None:
                raise EngineUnavailable("Stockfish introuvable sur le serveur")
            try:
                engine = chess.engine.SimpleEngine.popen_uci(path)
                # Never more threads than cores: on a small server that would
                # only slow the search down.
                threads = max(1, min(settings.analysis_threads, os.cpu_count() or 1))
                engine.configure({"Threads": threads, "Hash": settings.analysis_hash_mb})
            except Exception as exc:  # noqa: BLE001 - binary missing, wrong arch...
                raise EngineUnavailable(f"Stockfish ne démarre pas : {exc}") from exc
            self._engine = engine
            logger.info("Stockfish started: %s", path)
        return self._engine

    def analyse(self, board: chess.Board, depth: int | None = None) -> dict:
        """Evaluate a position from the side to move.

        Returns {"cp", "mate", "best_uci", "best_san", "pv_san", "depth"}.
        """
        depth = depth or settings.analysis_depth
        if board.is_game_over():
            mated = board.is_checkmate()
            return {
                "cp": None if mated else 0,
                "mate": 0 if mated else None,
                "best_uci": None,
                "best_san": None,
                "pv_san": "",
                "depth": depth,
            }
        with self._lock:
            engine = self._ensure()
            try:
                info = engine.analyse(board, chess.engine.Limit(depth=depth))
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError) as exc:
                # A dead process must not poison the next request.
                self._engine = None
                raise EngineUnavailable(f"Stockfish s'est arrêté : {exc}") from exc
        score = info["score"].pov(board.turn)
        pv = info.get("pv") or []
        best = pv[0] if pv else None
        return {
            "cp": score.score(),
            "mate": score.mate(),
            "best_uci": best.uci() if best else None,
            "best_san": board.san(best) if best else None,
            "pv_san": board.variation_san(pv[:8]) if pv else "",
            "depth": info.get("depth", depth),
        }

    def close(self) -> None:
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.quit()
                except Exception:  # noqa: BLE001 - already gone
                    pass
                self._engine = None


engine_service = EngineService()


def board_from_key(key: str) -> chess.Board:
    board = chess.Board()
    board.set_epd(key)
    return board


def cached_eval(db: Session, key: str) -> PositionEval | None:
    return db.get(PositionEval, key)


def evaluate(
    db: Session,
    board: chess.Board,
    depth: int | None = None,
    engine: EngineService | None = None,
) -> PositionEval:
    """Evaluation of a position, from the cache when deep enough.

    The caller commits.
    """
    depth = depth or settings.analysis_depth
    key = position_key(board)
    row = db.get(PositionEval, key)
    if row is not None and row.depth >= depth:
        return row
    result = (engine or engine_service).analyse(board, depth)
    if row is None:
        row = PositionEval(key=key)
        db.add(row)
    row.depth = result["depth"]
    row.cp = result["cp"]
    row.mate = result["mate"]
    row.best_uci = result["best_uci"]
    row.best_san = result["best_san"]
    row.pv_san = result["pv_san"]
    row.updated_at = utcnow()
    return row


def eval_dict(row: PositionEval | None, pov_is_mover: bool = True) -> dict | None:
    """Serialise an evaluation, optionally flipped to the other side."""
    if row is None:
        return None
    sign = 1 if pov_is_mover else -1
    return {
        "cp": sign * row.cp if row.cp is not None else None,
        "mate": sign * row.mate if row.mate is not None else None,
        "best_san": row.best_san,
        "best_uci": row.best_uci,
        "pv_san": row.pv_san,
        "depth": row.depth,
    }
