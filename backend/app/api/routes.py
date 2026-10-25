from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from .schemas import (
    APIError,
    CreateSessionRequest,
    DocumentUploadResponse,
    HealthResponse,
    RuntimeConfigResponse,
    SessionResponse,
    SubmitTurnRequest,
    TurnResponse,
    ReportResponse,
)
from ..core.session_store import (
    SessionConflictError,
    SessionNotFoundError,
)


router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(request: Request) -> HealthResponse:
    return HealthResponse(config_loaded=hasattr(request.app.state, "runtime_config"))


@router.get("/config", response_model=RuntimeConfigResponse, tags=["configuration"])
async def get_runtime_config(request: Request) -> RuntimeConfigResponse:
    config = request.app.state.runtime_config
    levels = config["interview_levels"]
    pressure = config["pressure_profiles"]
    return RuntimeConfigResponse(
        languages=[
            {"code": "vi", "label": "Tiếng Việt"},
            {"code": "en", "label": "English"},
        ],
        default_level=levels["default_level"],
        levels=levels["levels"],
        default_pressure_profile=pressure["default_profile"],
        pressure_profiles=pressure["profiles"],
    )


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
    responses={501: {"model": APIError}},
    summary="Upload a CV or job description (Phase 2)",
)
async def upload_document(
    file: UploadFile = File(...),
    kind: Literal["cv", "jd"] = Form(...),
) -> DocumentUploadResponse:
    del file, kind
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "DOCUMENT_PIPELINE_NOT_READY",
            "message": "Document parsing is scheduled for Phase 2.",
        },
    )


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["sessions"],
    summary="Create a development session",
    description=(
        "Phase 1 in-memory mock. Document IDs are accepted but not verified until "
        "the Phase 2 document pipeline is implemented."
    ),
)
async def create_session(
    request: Request, payload: CreateSessionRequest
) -> SessionResponse:
    config = request.app.state.runtime_config
    level_ids = {
        item["id"] for item in config["interview_levels"]["levels"]
    }
    profile_ids = set(config["pressure_profiles"]["profiles"])
    if payload.level_id not in level_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNKNOWN_INTERVIEW_LEVEL",
                "message": "The selected interview level is not configured.",
            },
        )
    if payload.pressure_profile_id not in profile_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNKNOWN_PRESSURE_PROFILE",
                "message": "The selected pressure profile is not configured.",
            },
        )
    return request.app.state.session_store.create(payload)


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    tags=["sessions"],
)
async def get_session(request: Request, session_id: UUID) -> SessionResponse:
    return _get_session(request, session_id)


@router.post(
    "/sessions/{session_id}/start",
    response_model=SessionResponse,
    tags=["sessions"],
)
async def start_session(request: Request, session_id: UUID) -> SessionResponse:
    try:
        return request.app.state.session_store.start(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found."},
        ) from exc
    except SessionConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "INVALID_SESSION_STATE", "message": str(exc)},
        ) from exc


@router.post(
    "/sessions/{session_id}/turns",
    response_model=TurnResponse,
    tags=["interview"],
    responses={501: {"model": APIError}},
    summary="Submit an answer turn (Phase 4)",
)
async def submit_turn(session_id: UUID, payload: SubmitTurnRequest) -> TurnResponse:
    del session_id, payload
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "INTERVIEW_WORKFLOW_NOT_READY",
            "message": "Question and answer turns are scheduled for Phase 4.",
        },
    )


@router.post(
    "/sessions/{session_id}/complete",
    response_model=SessionResponse,
    tags=["sessions"],
)
async def complete_session(request: Request, session_id: UUID) -> SessionResponse:
    try:
        return request.app.state.session_store.complete(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found."},
        ) from exc
    except SessionConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "INVALID_SESSION_STATE", "message": str(exc)},
        ) from exc


@router.get(
    "/sessions/{session_id}/report",
    response_model=ReportResponse,
    tags=["reports"],
    responses={501: {"model": APIError}},
    summary="Get the post-session report (Phase 6)",
)
async def get_report(session_id: UUID) -> ReportResponse:
    del session_id
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "REPORT_NOT_READY",
            "message": "Post-session evaluation is scheduled for Phase 6.",
        },
    )


def _get_session(request: Request, session_id: UUID) -> SessionResponse:
    try:
        return request.app.state.session_store.get(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found."},
        ) from exc
