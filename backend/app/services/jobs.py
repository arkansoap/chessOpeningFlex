"""Minimal background jobs: one thread per kind, progress kept in memory.

The app has a single user, so a process-local registry is enough: no queue,
no broker. A job that is asked to stop finishes its current step and exits.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.core.models import utcnow

logger = logging.getLogger(__name__)


@dataclass
class JobState:
    kind: str
    status: str = "idle"  # idle | running | done | error | stopped
    message: str = ""
    done: int = 0
    total: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: dict = field(default_factory=dict)
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def stop_requested(self) -> bool:
        return self._stop.is_set()

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "status": self.status,
            "message": self.message,
            "done": self.done,
            "total": self.total,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "result": self.result,
        }


_jobs: dict[str, JobState] = {}
_lock = threading.Lock()


def get(kind: str) -> JobState:
    with _lock:
        return _jobs.setdefault(kind, JobState(kind=kind))


def start(kind: str, target: Callable[[JobState], None]) -> tuple[JobState, bool]:
    """Run `target(state)` in a thread unless a job of this kind is running.

    Returns the state and whether a new job was started.
    """
    with _lock:
        current = _jobs.get(kind)
        if current is not None and current.status == "running":
            return current, False
        state = JobState(kind=kind, status="running", started_at=utcnow())
        _jobs[kind] = state

    def runner() -> None:
        try:
            target(state)
            if state.status == "running":
                state.status = "stopped" if state.stop_requested else "done"
        except Exception as exc:  # noqa: BLE001 - reported to the UI
            logger.exception("Job %s failed", kind)
            state.status = "error"
            state.error = str(exc)
        finally:
            state.finished_at = utcnow()

    threading.Thread(target=runner, name=f"job-{kind}", daemon=True).start()
    return state, True


def request_stop(kind: str) -> JobState:
    state = get(kind)
    state._stop.set()
    return state
