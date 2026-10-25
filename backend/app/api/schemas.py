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


class TimingWorkflow(StrictModel):
    classify_question_difficulty: bool
    consider_interview_level: bool
    consider_question_type: bool
    clamp_to_configured_band: bool


class PressureProfile(StrictModel):
    description: str
    difficulty_bands: DifficultyBands
    max_followups_per_question: int = Field(ge=0)
    timing_workflow: TimingWorkflow


class RuntimeConfigResponse(StrictModel):
    contract_version: Literal[1] = 1
    languages: list[LanguageOption]
    default_level: str
    levels: list[InterviewLevel]
    default_pressure_profile: str
    pressure_profiles: dict[str, PressureProfile]


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


class TurnResponse(StrictModel):
    turn_id: UUID
    sequence: int
    kind: Literal["primary", "follow_up"]
    status: str
    question: dict[str, Any]


class SubmitTurnRequest(StrictModel):
    answer_text: str = Field(min_length=1)


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
