from __future__ import annotations

from typing import Any

from ..adapters.protocols import RetrievedRecord
from .knowledge_base import KnowledgeBaseIndex, tokenize


class KnowledgeBaseRetriever:
    """Metadata filtering followed by small-corpus Unicode keyword ranking."""

    def __init__(self, index: KnowledgeBaseIndex, *, levels: dict[str, dict[str, Any]]) -> None:
        self._index = index
        self._levels = levels

    async def retrieve(
        self,
        *,
        query: str,
        industry_id: str | None = None,
        job_family_id: str | None = None,
        role_id: str | None = None,
        level_id: str,
        limit: int = 10,
    ) -> list[RetrievedRecord]:
        query_tokens = tokenize(query)
        level = self._levels[level_id]
        rubric_profile = level["rubric_profile"]
        matches: list[tuple[float, str, RetrievedRecord]] = []

        for item in self._index.records:
            if not item.retrievable:
                continue
            if industry_id and item.industry_id != industry_id:
                continue
            if job_family_id and item.job_family_id != job_family_id:
                continue
            if role_id and item.role_id != role_id:
                continue
            if item.level_ids and level_id not in item.level_ids:
                continue
            if item.record_type == "rubric_dimension" and item.rubric_profile != rubric_profile:
                continue

            record_tokens = tokenize(item.searchable_text)
            overlap = query_tokens & record_tokens
            if query_tokens and not overlap:
                continue
            score = len(overlap) / len(query_tokens) if query_tokens else 0.0
            source_details = tuple(self._index.sources[source_id] for source_id in item.source_ids)
            record = RetrievedRecord(
                record_id=item.record_id,
                record_type=item.record_type,
                content=item.content,
                source_ids=item.source_ids,
                version=item.version,
                relevance_score=score,
                metadata={
                    "industry_id": item.industry_id,
                    "job_family_id": item.job_family_id,
                    "role_id": item.role_id,
                    "level_ids": list(item.level_ids),
                    "rubric_profile": item.rubric_profile,
                },
                sources=source_details,
            )
            matches.append((score, item.record_id, record))

        matches.sort(key=lambda match: (-match[0], match[1]))
        return [record for _, _, record in matches[:limit]]
