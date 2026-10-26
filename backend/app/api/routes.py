from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool

from ..documents.context import build_document_context
from ..documents.parsers import DocumentParseError, parse_document
from ..documents.store import DocumentConflictError, DocumentNotFoundError
from .schemas import (
    APIError,
    ConfirmDocumentRequest,
    ConfirmDocumentResponse,
    CriteriaRecordResponse,
    CriteriaSearchResponse,
    CriteriaTaxonomiesResponse,
    CriteriaSource,
    CreateSessionRequest,
    DocumentUploadResponse,
    HealthResponse,
    RuntimeConfigResponse,
    SessionContextResponse,
    SessionResponse,
    SubmitTurnRequest,
    TimeoutTurnRequest,
    InterviewStateResponse,
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
        document_processing=config["document_processing"],
    )


@router.get(
    "/criteria/taxonomies",
    response_model=CriteriaTaxonomiesResponse,
    tags=["criteria"],
    summary="List configured industries, job families, and roles",
)
async def get_criteria_taxonomies(request: Request) -> CriteriaTaxonomiesResponse:
    index = request.app.state.knowledge_base
    return CriteriaTaxonomiesResponse(
        industries=list(index.industries.values()),
        job_families=list(index.job_families.values()),
        roles=list(index.roles),
    )


@router.get(
    "/criteria/search",
    response_model=CriteriaSearchResponse,
    tags=["criteria"],
    summary="Search reviewed criteria by metadata and keywords",
)
async def search_criteria(
    request: Request,
    level_id: str = Query(..., min_length=1),
    query: str = "",
    industry_id: str | None = None,
    job_family_id: str | None = None,
    role_id: str | None = None,
    limit: int = Query(default=10, ge=1, le=100),
) -> CriteriaSearchResponse:
    runtime_config = request.app.state.runtime_config
    configured_level_ids = {
        level["id"] for level in runtime_config["interview_levels"]["levels"]
    }
    if level_id not in configured_level_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNKNOWN_INTERVIEW_LEVEL",
                "message": "The selected interview level is not configured.",
            },
        )

    retrieved = await request.app.state.providers["criteria_retriever"].retrieve(
        query=query,
        industry_id=industry_id,
        job_family_id=job_family_id,
        role_id=role_id,
        level_id=level_id,
        limit=limit,
    )
    warnings = []
    if not retrieved:
        warnings.append(
            "Không có tiêu chí đã duyệt khớp bộ lọc/từ khóa. Hệ thống không thay bằng dữ liệu chưa kiểm chứng."
        )
    return CriteriaSearchResponse(
        records=[
            CriteriaRecordResponse(
                record_id=item.record_id,
                record_type=item.record_type,
                version=item.version,
                relevance_score=item.relevance_score,
                metadata=item.metadata or {},
                content=item.content,
                source_ids=list(item.source_ids),
                sources=[CriteriaSource.model_validate(source) for source in item.sources],
            )
            for item in retrieved
        ],
        total=len(retrieved),
        warnings=warnings,
    )


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
    summary="Upload a CV or job description (Phase 2)",
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    kind: Literal["cv", "jd"] = Form(...),
) -> DocumentUploadResponse:
    config = request.app.state.runtime_config["document_processing"]
    max_bytes = config["max_file_size_bytes"]
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not filename:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_FILENAME", "message": "Tên file không hợp lệ."},
        )
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "DOCUMENT_TOO_LARGE",
                "message": f"Mỗi file không được vượt quá {max_bytes // (1024 * 1024)} MB.",
            },
        )
    try:
        parsed = await run_in_threadpool(
            parse_document,
            filename=filename,
            content_type=file.content_type,
            content=content,
            config=config,
        )
    except DocumentParseError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    document = request.app.state.document_store.add(
        kind=kind,
        filename=filename,
        media_type=parsed.media_type,
        extracted_text=parsed.text,
    )
    return DocumentUploadResponse(
        document_id=document.document_id,
        kind=kind,
        status="uploaded",
        extracted_text=document.extracted_text,
    )


@router.put(
    "/documents/{document_id}/confirm",
    response_model=ConfirmDocumentResponse,
    tags=["documents"],
    summary="Confirm extracted or edited document text",
)
async def confirm_document(
    request: Request, document_id: UUID, payload: ConfirmDocumentRequest
) -> ConfirmDocumentResponse:
    max_text_bytes = request.app.state.runtime_config["document_processing"][
        "max_file_size_bytes"
    ]
    if len(payload.extracted_text.encode("utf-8")) > max_text_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "DOCUMENT_TEXT_TOO_LARGE",
                "message": "Text xác nhận vượt giới hạn xử lý cho mỗi tài liệu.",
            },
        )
    try:
        document = request.app.state.document_store.confirm(
            document_id, payload.extracted_text
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Không tìm thấy tài liệu."},
        ) from exc
    except DocumentConflictError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "EMPTY_DOCUMENT_TEXT", "message": "Text tài liệu không được để trống."},
        ) from exc
    return ConfirmDocumentResponse(
        document_id=document.document_id, kind=document.kind, status="ready"
    )


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["documents"],
    summary="Discard an in-memory document",
)
async def delete_document(request: Request, document_id: UUID) -> None:
    try:
        request.app.state.document_store.delete(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Không tìm thấy tài liệu."},
        ) from exc


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["sessions"],
    summary="Create a development session",
    description=(
        "Creates an in-memory session after both confirmed CV/JD documents are validated."
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
    document_store = request.app.state.document_store
    try:
        cv_document = document_store.get(payload.documents.cv_document_id)
        jd_document = document_store.get(payload.documents.jd_document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "CV hoặc JD không tồn tại."},
        ) from exc
    if cv_document.kind != "cv" or jd_document.kind != "jd":
        raise HTTPException(
            status_code=422,
            detail={"code": "DOCUMENT_KIND_MISMATCH", "message": "Cần cung cấp đúng một CV và một JD."},
        )
    if not cv_document.confirmed or not jd_document.confirmed:
        raise HTTPException(
            status_code=409,
            detail={"code": "DOCUMENT_NOT_CONFIRMED", "message": "Hãy xem và xác nhận text của cả CV và JD trước."},
        )
    context = {
        "cv_context": build_document_context("cv", cv_document.document_id, cv_document.extracted_text),
        "jd_context": build_document_context("jd", jd_document.document_id, jd_document.extracted_text),
    }
    return request.app.state.session_store.create(payload, context)


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    tags=["sessions"],
)
async def get_session(request: Request, session_id: UUID) -> SessionResponse:
    return _get_session(request, session_id)


@router.get(
    "/sessions/{session_id}/context",
    response_model=SessionContextResponse,
    tags=["sessions"],
    summary="Inspect the confirmed CV/JD context for a session",
)
async def get_session_context(
    request: Request, session_id: UUID
) -> SessionContextResponse:
    try:
        session = request.app.state.session_store.get(session_id)
        context = request.app.state.session_store.get_context(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "SESSION_NOT_FOUND", "message": "Không tìm thấy phiên."},
        ) from exc
    return SessionContextResponse(
        session_id=session.session_id,
        language=session.language,
        level_id=session.level_id,
        pressure_profile_id=session.pressure_profile_id,
        role_mapping=session.role_mapping,
        **context,
    )


@router.post(
    "/sessions/{session_id}/start",
    response_model=InterviewStateResponse,
    tags=["sessions"],
)
async def start_session(request: Request, session_id: UUID) -> InterviewStateResponse:
    try:
        return await request.app.state.interview_workflow.start(session_id)
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
    "/sessions/{session_id}/interview",
    response_model=InterviewStateResponse,
    tags=["interview"],
)
async def get_interview_state(request: Request, session_id: UUID) -> InterviewStateResponse:
    try:
        return request.app.state.interview_workflow.get(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Không tìm thấy phiên."}) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "INTERVIEW_NOT_STARTED", "message": str(exc)}) from exc


@router.post(
    "/sessions/{session_id}/turns",
    response_model=InterviewStateResponse,
    tags=["interview"],
    summary="Submit an answer for the current question",
)
async def submit_turn(request: Request, session_id: UUID, payload: SubmitTurnRequest) -> InterviewStateResponse:
    try:
        return await request.app.state.interview_workflow.submit(session_id, payload.turn_id, payload.answer_text)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Không tìm thấy phiên."}) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "INVALID_INTERVIEW_STATE", "message": str(exc)}) from exc


@router.post(
    "/sessions/{session_id}/turns/timeout",
    response_model=InterviewStateResponse,
    tags=["interview"],
    summary="Record that the current answer timed out",
)
async def timeout_turn(request: Request, session_id: UUID, payload: TimeoutTurnRequest) -> InterviewStateResponse:
    try:
        return await request.app.state.interview_workflow.timeout(session_id, payload.turn_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Không tìm thấy phiên."}) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "INVALID_INTERVIEW_STATE", "message": str(exc)}) from exc


@router.post(
    "/sessions/{session_id}/complete",
    response_model=SessionResponse,
    tags=["sessions"],
)
async def complete_session(request: Request, session_id: UUID) -> SessionResponse:
    try:
        return (await request.app.state.interview_workflow.end_early(session_id)).session
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
