from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import UUID, uuid4

from ..api.schemas import CreateSessionRequest, SessionResponse


class SessionConflictError(ValueError):
    pass


class SessionNotFoundError(LookupError):
    pass


class InMemorySessionStore:
    """Development-only lifecycle store; replace with persistence after a decision."""

    def __init__(self) -> None:
        self._items: dict[UUID, SessionResponse] = {}
        self._lock = RLock()

    def create(self, request: CreateSessionRequest) -> SessionResponse:
        now = datetime.now(timezone.utc)
        session = SessionResponse(
            session_id=uuid4(),
            status="ready",
            language=request.language,
            level_id=request.level_id,
            pressure_profile_id=request.pressure_profile_id,
            documents=request.documents,
            created_at=now,
        )
        with self._lock:
            self._items[session.session_id] = session
        return session

    def get(self, session_id: UUID) -> SessionResponse:
        with self._lock:
            session = self._items.get(session_id)
        if session is None:
            raise SessionNotFoundError(str(session_id))
        return session

    def start(self, session_id: UUID) -> SessionResponse:
        with self._lock:
            session = self._get_locked(session_id)
            if session.status != "ready":
                raise SessionConflictError(
                    f"Cannot start a session in state '{session.status}'"
                )
            updated = session.model_copy(
                update={"status": "running", "started_at": datetime.now(timezone.utc)}
            )
            self._items[session_id] = updated
            return updated

    def complete(self, session_id: UUID) -> SessionResponse:
        with self._lock:
            session = self._get_locked(session_id)
            if session.status != "running":
                raise SessionConflictError(
                    f"Cannot complete a session in state '{session.status}'"
                )
            updated = session.model_copy(
                update={"status": "completed", "ended_at": datetime.now(timezone.utc)}
            )
            self._items[session_id] = updated
            return updated

    def _get_locked(self, session_id: UUID) -> SessionResponse:
        session = self._items.get(session_id)
        if session is None:
            raise SessionNotFoundError(str(session_id))
        return session
