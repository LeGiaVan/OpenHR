from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .adapters.mock import (
    EmptyCriteriaRetriever,
    MockLLMProvider,
    MockSpeechToTextProvider,
    MockTextToSpeechProvider,
)
from .api.routes import router
from .core.config import ConfigValidationError, load_runtime_config
from .core.session_store import InMemorySessionStore
from .core.settings import get_api_prefix, get_config_dir_root, get_cors_origins


logger = logging.getLogger("openhr.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.runtime_config = load_runtime_config(get_config_dir_root())
    except ConfigValidationError:
        logger.exception("Application configuration validation failed")
        raise
    app.state.session_store = InMemorySessionStore()
    app.state.providers = {
        "llm": MockLLMProvider(),
        "stt": MockSpeechToTextProvider(),
        "tts": MockTextToSpeechProvider(),
        "criteria_retriever": EmptyCriteriaRetriever(),
    }
    yield


app = FastAPI(
    title="OpenHR Interview Practice API",
    version="0.1.0",
    description=(
        "Phase 1 API skeleton. Document parsing, live interview turns, and reports "
        "are added in later phases."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
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
