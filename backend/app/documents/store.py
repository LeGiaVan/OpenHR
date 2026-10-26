from __future__ import annotations

from dataclasses import dataclass, replace
from threading import RLock
from uuid import UUID, uuid4


class DocumentNotFoundError(LookupError):
    pass


class DocumentConflictError(ValueError):
    pass


@dataclass(frozen=True)
class StoredDocument:
    document_id: UUID
    kind: str
    filename: str
    media_type: str
    extracted_text: str
    confirmed: bool = False


class InMemoryDocumentStore:
    """Process-local storage only; uploaded file bytes are discarded after parsing."""

    def __init__(self) -> None:
        self._items: dict[UUID, StoredDocument] = {}
        self._lock = RLock()

    def add(self, *, kind: str, filename: str, media_type: str, extracted_text: str) -> StoredDocument:
        document = StoredDocument(
            document_id=uuid4(),
            kind=kind,
            filename=filename,
            media_type=media_type,
            extracted_text=extracted_text,
        )
        with self._lock:
            self._items[document.document_id] = document
        return document

    def get(self, document_id: UUID) -> StoredDocument:
        with self._lock:
            document = self._items.get(document_id)
        if document is None:
            raise DocumentNotFoundError(str(document_id))
        return document

    def confirm(self, document_id: UUID, extracted_text: str) -> StoredDocument:
        text = extracted_text.strip()
        if not text:
            raise DocumentConflictError("Extracted text cannot be empty")
        with self._lock:
            document = self._items.get(document_id)
            if document is None:
                raise DocumentNotFoundError(str(document_id))
            updated = replace(document, extracted_text=text, confirmed=True)
            self._items[document_id] = updated
            return updated

    def delete(self, document_id: UUID) -> None:
        with self._lock:
            if self._items.pop(document_id, None) is None:
                raise DocumentNotFoundError(str(document_id))
