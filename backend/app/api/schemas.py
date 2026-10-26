from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LanguageOption(StrictModel):
    code: Literal["vi", "en"]
    label: str


class QuestionMix(StrictModel):
    behavioral: float = Field(ge=0, le=1)
    role_specific: float = Field(ge=0, le=1)


class FollowUpProfile(StrictModel):
    enabled: bool
    strategy: str
    max_depth: int = Field(ge=0)


class InterviewLevel(StrictModel):
    id: str
    name: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    primary_question_count: int = Field(ge=1)
    fallback_question_band: Literal["low", "medium", "high"]
    question_mix: QuestionMix
    follow_up: FollowUpProfile
    rubric_profile: str


class TimeAllowance(StrictModel):
    preparation_seconds: int = Field(ge=0)
    answer_seconds: int = Field(gt=0)


class DifficultyBands(StrictModel):
    low: TimeAllowance
    medium: TimeAllowance
    high: TimeAllowance


class InterviewerBehavior(StrictModel):
    challenge_style: str
    follow_up_depth: str


class PressureProfile(StrictModel):
    description: str
    difficulty_bands: DifficultyBands
    max_followups_per_question: int = Field(ge=0)
    interviewer_behavior: InterviewerBehavior


class AcceptedDocumentFormat(StrictModel):
    extension: Literal[".pdf", ".docx"]
    kind: Literal["pdf", "docx"]
    media_types: list[str]


class DocumentProcessingConfig(StrictModel):
    version: Literal[1]
    max_file_size_bytes: int = Field(gt=0)
    max_docx_uncompressed_size_bytes: int = Field(gt=0)
    accepted_formats: list[AcceptedDocumentFormat]
    ocr_enabled: Literal[False]


class RuntimeConfigResponse(StrictModel):
    contract_version: Literal[1] = 1
    languages: list[LanguageOption]
    default_level: str
    levels: list[InterviewLevel]
    default_pressure_profile: str
    pressure_profiles: dict[str, PressureProfile]
    document_processing: DocumentProcessingConfig


class DocumentReferences(StrictModel):
    cv_document_id: UUID
    jd_document_id: UUID


class CreateSessionRequest(StrictModel):
    documents: DocumentReferences
    language: Literal["vi", "en"]
    level_id: str
    pressure_profile_id: str


class SessionResponse(StrictModel):
    contract_version: Literal[1] = 1
    session_id: UUID
    status: Literal["preparing", "ready", "running", "completed", "failed", "cancelled"]
    language: Literal["vi", "en"]
    level_id: str
    pressure_profile_id: str
    documents: DocumentReferences
    role_mapping: dict[str, Any] | None = None
    completion_reason: Literal["plan_completed", "user_ended_early"] | None = None
    turn_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None


class APIFieldError(StrictModel):
    field: str
    message: str


class APIError(StrictModel):
    code: str
    message: str
    request_id: UUID
    fields: list[APIFieldError] = Field(default_factory=list)


class HealthResponse(StrictModel):
    status: Literal["ok"] = "ok"
    service: str = "openhr-api"
    config_loaded: bool


class DocumentUploadResponse(StrictModel):
    document_id: UUID
    kind: Literal["cv", "jd"]
    status: Literal["uploaded", "processing", "ready", "failed"]
    extracted_text: str | None = None


class ConfirmDocumentRequest(StrictModel):
    extracted_text: str = Field(min_length=1)


class ConfirmDocumentResponse(StrictModel):
    document_id: UUID
    kind: Literal["cv", "jd"]
    status: Literal["ready"]


class SessionContextResponse(StrictModel):
    contract_version: Literal[1] = 1
    session_id: UUID
    language: Literal["vi", "en"]
    level_id: str
    pressure_profile_id: str
    role_mapping: dict[str, Any] | None = None
    cv_context: dict[str, Any]
    jd_context: dict[str, Any]


class CriteriaSource(StrictModel):
    id: str
    title: str
    source_type: str
    owner: str
    version: int
    status: Literal["draft", "in_review", "approved", "deprecated"]
    license_or_usage_notes: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    uri: str | None = None


class CriteriaRecordResponse(StrictModel):
    record_id: str
    record_type: Literal["competency", "question", "rubric_dimension"]
    version: int
    relevance_score: float = Field(ge=0, le=1)
    metadata: dict[str, Any]
    content: dict[str, Any]
    source_ids: list[str]
    sources: list[CriteriaSource]


class CriteriaSearchResponse(StrictModel):
    records: list[CriteriaRecordResponse]
    total: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class CriteriaTaxonomiesResponse(StrictModel):
    industries: list[dict[str, Any]]
    job_families: list[dict[str, Any]]
    roles: list[dict[str, Any]]


class TurnResponse(StrictModel):
    contract_version: Literal[1] = 1
    turn_id: UUID
    sequence: int
    kind: Literal["primary", "follow_up"]
    status: Literal["queued", "asking", "answering", "submitted", "timed_out", "skipped"]
    question: dict[str, Any]
    answer: dict[str, Any] | None = None
    timing: dict[str, Any] | None = None
    parent_turn_id: UUID | None = None
    follow_up_depth: int | None = Field(default=None, ge=1)
    criteria_provenance: list[dict[str, Any]] = Field(default_factory=list)
    asked_at: datetime | None = None
    completed_at: datetime | None = None


class InterviewStateResponse(StrictModel):
    session: SessionResponse
    turns: list[TurnResponse]
    current_turn: TurnResponse | None = None
    primary_question_count: int
    primary_questions_completed: int
    retrieved_criteria_ids: list[str] = Field(default_factory=list)
    transition_reason: str | None = None
    criteria_warnings: list[str] = Field(default_factory=list)


class SubmitTurnRequest(StrictModel):
    turn_id: UUID
    answer_text: str = Field(min_length=1)


class TimeoutTurnRequest(StrictModel):
    turn_id: UUID


class ReportResponse(StrictModel):
    report_id: UUID
    session_id: UUID
    language: Literal["vi", "en"]
    rubric_version: int
    overall_summary: str | None = None
    dimensions: list[dict[str, Any]]
    language_notes: str | None = None
    speech_observations: list[str] = Field(default_factory=list)
    created_at: datetime
