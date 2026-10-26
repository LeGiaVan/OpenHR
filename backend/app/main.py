from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .adapters.mock import (
    MockLLMProvider,
    MockSpeechToTextProvider,
    MockTextToSpeechProvider,
)
from .adapters.gemini import build_gemini_providers
from .api.routes import router
from .core.config import ConfigValidationError, load_runtime_config
from .core.session_store import InMemorySessionStore
from .core.settings import get_api_prefix, get_config_dir_root, get_cors_origins
from .documents.store import InMemoryDocumentStore
from .retrieval.keyword import KnowledgeBaseRetriever
from .retrieval.knowledge_base import KnowledgeBaseValidationError, load_knowledge_base
from .workflow.service import InterviewWorkflow


logger = logging.getLogger("openhr.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.runtime_config = load_runtime_config(get_config_dir_root())
    except ConfigValidationError:
        logger.exception("Application configuration validation failed")
        raise
    levels = {
        level["id"]: level
        for level in app.state.runtime_config["interview_levels"]["levels"]
    }
    try:
        app.state.knowledge_base = load_knowledge_base(
            get_config_dir_root() / "knowledge_base",
            level_ids=set(levels),
            rubric_profiles={level["rubric_profile"] for level in levels.values()},
        )
    except KnowledgeBaseValidationError:
        logger.exception("Knowledge-base validation failed")
        raise
    app.state.session_store = InMemorySessionStore()
    app.state.document_store = InMemoryDocumentStore()
    provider_mode = os.getenv("OPENHR_PROVIDER_MODE", "mock").strip().lower()
    if provider_mode == "gemini":
        speech_providers = build_gemini_providers()
    elif provider_mode == "mock":
        speech_providers = {
            "llm": MockLLMProvider(),
            "stt": MockSpeechToTextProvider(),
            "tts": MockTextToSpeechProvider(),
        }
    else:
        raise RuntimeError("OPENHR_PROVIDER_MODE must be 'mock' or 'gemini'")
    app.state.providers = {
        **speech_providers,
        "criteria_retriever": KnowledgeBaseRetriever(
            app.state.knowledge_base, levels=levels
        ),
    }
    app.state.interview_workflow = InterviewWorkflow(
        app.state.session_store,
        app.state.runtime_config,
        app.state.providers["criteria_retriever"],
    )
    yield


app = FastAPI(
    title="OpenHR Interview Practice API",
    version="0.1.0",
    description=(
        "Text interview workflow with validated criteria retrieval. Evaluation reports "
        "are added in Phase 6."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = uuid4()
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(request_id)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    fields = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        fields.append({"field": location, "message": error.get("msg", "Invalid value")})
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "The request contains invalid fields.",
            "request_id": str(request.state.request_id),
            "fields": fields,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": detail.get("code", "HTTP_ERROR"),
            "message": detail.get("message", "The request could not be completed."),
            "request_id": str(request.state.request_id),
            "fields": [],
        },
        headers=exc.headers,
    )


app.include_router(router, prefix=get_api_prefix())
