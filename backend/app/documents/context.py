from __future__ import annotations

import re
from typing import Any
from uuid import UUID


_CV_HEADINGS = {
    "skills": ("skills", "technical skills", "skills and tools", "technical skills and tools", "technical skills & tools", "kỹ năng", "kỹ năng chuyên môn"),
    "projects": ("projects", "personal projects", "academic projects", "selected projects", "dự án", "các dự án", "đồ án"),
    "education": ("education", "academic background", "education and training", "educational background", "học vấn", "giáo dục"),
    "activities": ("activities", "extracurricular activities", "volunteering", "activities and volunteering", "hoạt động", "hoạt động ngoại khóa", "tình nguyện", "câu lạc bộ"),
    "work_experience": ("experience", "work experience", "professional experience", "relevant experience", "employment", "employment history", "work history", "internship experience", "internship", "kinh nghiệm", "kinh nghiệm làm việc", "kinh nghiệm chuyên môn", "thực tập", "việc làm"),
    "other_evidence": ("certificates", "certifications", "awards", "languages", "interests", "summary", "profile", "chứng chỉ", "giải thưởng", "ngôn ngữ", "sở thích", "giới thiệu"),
}
_JD_HEADINGS = {
    "requirements": ("requirements", "qualifications", "what you bring", "yêu cầu", "điều kiện", "trình độ"),
    "responsibilities": ("responsibilities", "what you will do", "your role", "trách nhiệm", "nhiệm vụ", "mô tả công việc"),
    "skills": ("skills", "technical skills", "technologies", "skills and experience", "kỹ năng", "công nghệ", "kiến thức"),
}


def build_document_context(kind: str, document_id: UUID, text: str) -> dict[str, Any]:
    """Group exact source lines using headings/cues; never infer missing experience."""
    headings = _CV_HEADINGS if kind == "cv" else _JD_HEADINGS
    categories: dict[str, list[dict[str, Any]]] = {key: [] for key in headings}
    unclassified: list[dict[str, Any]] = []
    active: str | None = None
    lines = text.splitlines()

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        heading = _match_heading(line, headings)
        if heading:
            active = heading
            continue
        category = active or _match_cue(line, kind)
        item = {
            "source_document_id": str(document_id),
            "source_line": line_number,
            "text": line,
        }
        if category:
            categories[category].append(item)
        else:
            unclassified.append(item)

    warnings: list[str] = []
    if kind == "jd" and not any(categories.values()):
        warnings.append("JD chưa có cấu trúc/yêu cầu nhận diện được; nội dung cần được xem lại thủ công.")
    if kind == "cv" and not categories["work_experience"]:
        warnings.append("Không nhận diện được mục kinh nghiệm làm việc. Đồ án, học vấn và hoạt động vẫn được giữ làm evidence.")
    if kind == "cv" and not any(categories.values()):
        warnings.append("CV chưa có mục kỹ năng, dự án, học vấn hoặc hoạt động nhận diện được; không suy diễn thêm thông tin.")

    return {
        "source_document_id": str(document_id),
        "analysis_method": "section_heading_and_keyword_cues",
        **categories,
        "unclassified": unclassified,
        "warnings": warnings,
    }


def _normalize_heading(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"^#{1,6}\s*", "", normalized)
    return re.sub(r"[\s:：|•#]+$", "", normalized).strip()


def _match_heading(line: str, headings: dict[str, tuple[str, ...]]) -> str | None:
    normalized = _normalize_heading(line)
    for category, variants in headings.items():
        if normalized in variants:
            return category
    return None


def _match_cue(line: str, kind: str) -> str | None:
    lowered = line.lower()
    if kind == "cv":
        cues = {
            "projects": ("project:", "dự án:", "đồ án:", "repo:"),
            "education": ("university", "bachelor", "gpa", "đại học", "cao đẳng", "điểm trung bình"),
            "activities": ("volunteer", "club", "câu lạc bộ", "tình nguyện", "ngoại khóa"),
            "work_experience": ("intern", "part-time", "part time", "thực tập", "bán thời gian"),
            "skills": ("skill:", "skills:", "kỹ năng:", "technologies:", "tools:"),
        }
    else:
        cues = {
            "requirements": ("requirement:", "requirements:", "must have", "yêu cầu:", "tối thiểu"),
            "responsibilities": ("responsibility:", "responsibilities:", "you will", "trách nhiệm:", "nhiệm vụ:"),
            "skills": ("skills:", "kỹ năng:", "experience with", "proficient in", "thành thạo"),
        }
    for category, phrases in cues.items():
        if any(phrase in lowered for phrase in phrases):
            return category
    return None
