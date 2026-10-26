from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


class DocumentParseError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    media_type: str


def parse_document(
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
    config: dict[str, Any],
) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    formats = {item["extension"]: item for item in config["accepted_formats"]}
    format_config = formats.get(suffix)
    if format_config is None:
        raise DocumentParseError(
            "UNSUPPORTED_DOCUMENT_TYPE",
            "Chỉ chấp nhận file PDF hoặc DOCX có text.",
        )

    allowed_types = format_config["media_types"]
    normalized_type = (content_type or "").split(";")[0].strip().lower()
    if normalized_type and normalized_type not in allowed_types and normalized_type != "application/octet-stream":
        raise DocumentParseError(
            "DOCUMENT_MEDIA_TYPE_MISMATCH",
            "Loại nội dung của file không khớp với phần mở rộng.",
        )

    if not content:
        raise DocumentParseError("EMPTY_DOCUMENT", "File tải lên đang rỗng.")

    if suffix == ".pdf":
        parsed = _parse_pdf(content)
    else:
        parsed = _parse_docx(content, config["max_docx_uncompressed_size_bytes"])
    if len(parsed.text.encode("utf-8")) > config["max_file_size_bytes"]:
        raise DocumentParseError(
            "DOCUMENT_TEXT_TOO_LARGE",
            "Text sau trích xuất vượt giới hạn xử lý cho mỗi tài liệu.",
            413,
        )
    return parsed


def _parse_pdf(content: bytes) -> ParsedDocument:
    if b"%PDF-" not in content[:1024]:
        raise DocumentParseError("INVALID_DOCUMENT", "File không có cấu trúc PDF hợp lệ.")
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise DocumentParseError(
                "ENCRYPTED_DOCUMENT", "PDF được bảo vệ bằng mật khẩu chưa được hỗ trợ."
            )
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("INVALID_DOCUMENT", "Không đọc được nội dung PDF.") from exc
    return _require_text("\n\n".join(page for page in pages if page), "PDF")


def _parse_docx(content: bytes, max_uncompressed_bytes: int) -> ParsedDocument:
    try:
        with ZipFile(BytesIO(content)) as archive:
            if sum(item.file_size for item in archive.infolist()) > max_uncompressed_bytes:
                raise DocumentParseError(
                    "DOCUMENT_EXPANSION_LIMIT",
                    "Nội dung DOCX sau giải nén vượt giới hạn xử lý an toàn.",
                    413,
                )
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise DocumentParseError("INVALID_DOCUMENT", "File không có cấu trúc DOCX hợp lệ.")
        document = Document(BytesIO(content))
        blocks: list[str] = []
        for element in document.element.body.iterchildren():
            if element.tag.endswith("}p"):
                value = Paragraph(element, document).text.strip()
                if value:
                    blocks.append(value)
            elif element.tag.endswith("}tbl"):
                table = Table(element, document)
                for row in table.rows:
                    value = " | ".join(cell.text.strip() for cell in row.cells).strip()
                    if value:
                        blocks.append(value)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("INVALID_DOCUMENT", "Không đọc được nội dung DOCX.") from exc
    return _require_text("\n".join(blocks), "DOCX")


def _require_text(text: str, file_type: str) -> ParsedDocument:
    normalized = "\n".join(line.rstrip() for line in text.replace("\x00", "").splitlines()).strip()
    if not normalized:
        raise DocumentParseError(
            "DOCUMENT_NO_TEXT",
            f"Không tìm thấy text trong {file_type}. POC chưa hỗ trợ tài liệu scan/OCR.",
        )
    return ParsedDocument(text=normalized, media_type="application/pdf" if file_type == "PDF" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
