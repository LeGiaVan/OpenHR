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
        self._contexts: dict[UUID, dict[str, object]] = {}
        self._workflows: dict[UUID, dict[str, object]] = {}
        self._lock = RLock()

    def create(
        self, request: CreateSessionRequest, context: dict[str, object] | None = None
    ) -> SessionResponse:
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
            self._contexts[session.session_id] = context or {}
        return session

    def get(self, session_id: UUID) -> SessionResponse:
        with self._lock:
            session = self._items.get(session_id)
        if session is None:
            raise SessionNotFoundError(str(session_id))
        return session

    def get_context(self, session_id: UUID) -> dict[str, object]:
        with self._lock:
            if session_id not in self._items:
                raise SessionNotFoundError(str(session_id))
            return dict(self._contexts.get(session_id, {}))

    def get_workflow(self, session_id: UUID) -> dict[str, object]:
        with self._lock:
            if session_id not in self._items:
                raise SessionNotFoundError(str(session_id))
            workflow = self._workflows.get(session_id)
            if workflow is None:
                raise SessionConflictError("Interview workflow has not started")
            return workflow

    def set_workflow(self, session_id: UUID, workflow: dict[str, object]) -> None:
        with self._lock:
            session = self._items.get(session_id)
            if session is None:
                raise SessionNotFoundError(str(session_id))
            self._workflows[session_id] = workflow
            turn_ids = [item["turn_id"] for item in workflow.get("turns", [])]
            self._items[session_id] = session.model_copy(update={"turn_ids": turn_ids})

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

    def complete(
        self,
        session_id: UUID,
        *,
        completion_reason: str = "plan_completed",
    ) -> SessionResponse:
        with self._lock:
            session = self._get_locked(session_id)
            if session.status != "running":
                raise SessionConflictError(
                    f"Cannot complete a session in state '{session.status}'"
                )
            updated = session.model_copy(
                update={"status": "completed", "ended_at": datetime.now(timezone.utc),
                        "completion_reason": completion_reason}
            )
            self._items[session_id] = updated
            return updated

    def _get_locked(self, session_id: UUID) -> SessionResponse:
        session = self._items.get(session_id)
        if session is None:
            raise SessionNotFoundError(str(session_id))
        return session
