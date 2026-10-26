from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RetrievedRecord:
    record_id: str
    record_type: str
    content: dict[str, Any]
    source_ids: tuple[str, ...] = ()
    version: int = 1
    relevance_score: float = 0.0
    metadata: dict[str, Any] | None = None
    sources: tuple[dict[str, Any], ...] = ()


class LLMProvider(Protocol):
    async def generate(
        self, *, system_prompt: str, user_prompt: str, language: str
    ) -> str: ...


class SpeechToTextProvider(Protocol):
    async def transcribe(self, *, audio: bytes, language: str) -> str: ...


class TextToSpeechProvider(Protocol):
    async def synthesize(self, *, text: str, language: str) -> bytes: ...


class CriteriaRetriever(Protocol):
    async def retrieve(
        self,
        *,
        query: str,
        industry_id: str | None,
        job_family_id: str | None,
        role_id: str | None,
        level_id: str,
        limit: int = 10,
    ) -> list[RetrievedRecord]: ...
