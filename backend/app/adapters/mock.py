from __future__ import annotations

from typing import Any

from .protocols import RetrievedRecord


class MockLLMProvider:
    async def generate(
        self, *, system_prompt: str, user_prompt: str, language: str
    ) -> str:
        del system_prompt, user_prompt
        return "Mock response (" + language + ")"


class MockSpeechToTextProvider:
    async def transcribe(self, *, audio: bytes, language: str) -> str:
        del audio
        return "Mock transcript (" + language + ")"


class MockTextToSpeechProvider:
    async def synthesize(self, *, text: str, language: str) -> bytes:
        return ("Mock audio placeholder (" + language + "): " + text).encode("utf-8")


class EmptyCriteriaRetriever:
    async def retrieve(
        self, *, query: str, industry_id: str | None, role_id: str | None, level_id: str
    ) -> list[RetrievedRecord]:
        del query, industry_id, role_id, level_id
        return []


def mock_provider_status() -> dict[str, Any]:
    return {
        "llm": "mock",
        "speech_to_text": "mock",
        "text_to_speech": "mock",
        "criteria_retriever": "empty",
    }
