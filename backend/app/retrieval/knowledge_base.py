from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from yaml.constructor import ConstructorError
from yaml.resolver import BaseResolver


class KnowledgeBaseValidationError(RuntimeError):
    """Raised when the controlled criteria source is malformed or inconsistent."""


class UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueKeySafeLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeySafeLoader.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


@dataclass(frozen=True)
class KnowledgeRecord:
    record_id: str
    record_type: str
    version: int
    industry_id: str
    job_family_id: str
    role_id: str
    source_ids: tuple[str, ...]
    level_ids: tuple[str, ...]
    content: dict[str, Any]
    searchable_text: str
    retrievable: bool
    rubric_profile: str | None = None


@dataclass(frozen=True)
class KnowledgeBaseIndex:
    industries: dict[str, dict[str, Any]]
    job_families: dict[str, dict[str, Any]]
    sources: dict[str, dict[str, Any]]
    records: tuple[KnowledgeRecord, ...]
    roles: tuple[dict[str, Any], ...]


def load_knowledge_base(
    root: Path, *, level_ids: set[str], rubric_profiles: set[str]
) -> KnowledgeBaseIndex:
    schema_root = root / "schemas"
    industries_data = _load_and_validate(
        root / "taxonomies" / "industries.yaml",
        schema_root / "industry.schema.json",
    )
    families_data = _load_and_validate(
        root / "taxonomies" / "job_families.yaml",
        schema_root / "job_family.schema.json",
    )
    source_data = _load_and_validate(
        root / "sources" / "manifest.yaml",
        schema_root / "source.schema.json",
    )
    _require_supported_version(industries_data, "industries.yaml")
    _require_supported_version(families_data, "job_families.yaml")
    _require_supported_version(source_data, "manifest.yaml")

    industries = _unique_mapping(industries_data["industries"], "industry")
    families = _unique_mapping(families_data["job_families"], "job family")
    sources = _unique_mapping(source_data["sources"], "source")

    for family in families.values():
        if family["industry_id"] not in industries:
            raise KnowledgeBaseValidationError(
                f"job family {family['id']} references unknown industry {family['industry_id']}"
            )

    records: list[KnowledgeRecord] = []
    roles: list[dict[str, Any]] = []
    seen_record_ids: set[tuple[str, str]] = set()
    roles_root = root / "roles"
    if roles_root.exists():
        for role_dir in sorted(path for path in roles_root.glob("*/*") if path.is_dir()):
            if any(part.startswith("_") for part in role_dir.relative_to(roles_root).parts):
                continue
            role_records, role_metadata = _load_role(
                role_dir,
                schema_root,
                industries=industries,
                families=families,
                sources=sources,
                level_ids=level_ids,
                rubric_profiles=rubric_profiles,
            )
            roles.append(role_metadata)
            for record in role_records:
                key = (record.record_type, record.record_id)
                if key in seen_record_ids:
                    raise KnowledgeBaseValidationError(
                        f"duplicate {record.record_type} id across knowledge base: {record.record_id}"
                    )
                seen_record_ids.add(key)
                records.append(record)

    return KnowledgeBaseIndex(
        industries=industries,
        job_families=families,
        sources=sources,
        records=tuple(records),
        roles=tuple(roles),
    )


def _load_role(
    role_dir: Path,
    schema_root: Path,
    *,
    industries: dict[str, dict[str, Any]],
    families: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    level_ids: set[str],
    rubric_profiles: set[str],
) -> tuple[list[KnowledgeRecord], dict[str, Any]]:
    filenames = {
        "competency": "competencies.yaml",
        "question": "questions.yaml",
        "rubric": "rubrics.yaml",
    }
    documents = {
        kind: _load_and_validate(role_dir / filename, schema_root / f"{kind}.schema.json")
        for kind, filename in filenames.items()
    }
    for kind, document in documents.items():
        _require_supported_version(document, f"{role_dir.name}/{filenames[kind]}")
        if document["industry_id"] != role_dir.parent.name:
            raise KnowledgeBaseValidationError(
                f"{role_dir.name}/{filenames[kind]} industry_id does not match its directory"
            )
        if document["role_id"] != role_dir.name:
            raise KnowledgeBaseValidationError(
                f"{role_dir.name}/{filenames[kind]} role_id does not match its directory"
            )
        if document["industry_id"] not in industries:
            raise KnowledgeBaseValidationError(
                f"{role_dir.name} references unknown industry {document['industry_id']}"
            )
        family = families.get(document["job_family_id"])
        if family is None or family["industry_id"] != document["industry_id"]:
            raise KnowledgeBaseValidationError(
                f"{role_dir.name} references unknown or mismatched job family {document['job_family_id']}"
            )
    family_ids = {document["job_family_id"] for document in documents.values()}
    if len(family_ids) != 1:
        raise KnowledgeBaseValidationError(
            f"Role files in {role_dir.name} must use the same job_family_id"
        )
    rubric_blocks = documents["rubric"]["rubrics"]
    rubric_profile_ids = [block["rubric_profile"] for block in rubric_blocks]
    if len(rubric_profile_ids) != len(set(rubric_profile_ids)):
        raise KnowledgeBaseValidationError(
            f"Duplicate rubric_profile in {role_dir.name}/rubrics.yaml"
        )
    unknown_rubric_profiles = set(rubric_profile_ids) - rubric_profiles
    if unknown_rubric_profiles:
        raise KnowledgeBaseValidationError(
            f"{role_dir.name}/rubrics.yaml references unknown rubric profiles: {sorted(unknown_rubric_profiles)}"
        )

    competencies = documents["competency"]["competencies"]
    competency_ids = _unique_item_ids(competencies, "competency", role_dir.name)
    _unique_item_ids(documents["question"]["questions"], "question", role_dir.name)
    rubric_dimensions = [
        {"rubric_profile": block["rubric_profile"], **dimension}
        for block in rubric_blocks
        for dimension in block["dimensions"]
    ]
    _unique_item_ids(rubric_dimensions, "rubric dimension", role_dir.name)

    all_items = [
        ("competency", item, documents["competency"]["version"], None)
        for item in competencies
    ] + [
        ("question", item, documents["question"]["version"], None)
        for item in documents["question"]["questions"]
    ] + [
        ("rubric_dimension", item, documents["rubric"]["version"], item["rubric_profile"])
        for item in rubric_dimensions
    ]

    result: list[KnowledgeRecord] = []
    for record_type, item, version, rubric_profile in all_items:
        source_ids = tuple(item.get("source_ids", []))
        _validate_references(source_ids, sources, f"{record_type} {item['id']}")
        item_level_ids = tuple(item.get("level_ids", []))
        unknown_levels = set(item_level_ids) - level_ids
        if unknown_levels:
            raise KnowledgeBaseValidationError(
                f"{record_type} {item['id']} references unknown interview levels: {sorted(unknown_levels)}"
            )
        if record_type == "question":
            unknown_competencies = set(item["competency_ids"]) - competency_ids
            if unknown_competencies:
                raise KnowledgeBaseValidationError(
                    f"question {item['id']} references unknown competencies: {sorted(unknown_competencies)}"
                )
        if record_type == "rubric_dimension":
            unknown_competencies = set(item["competency_ids"]) - competency_ids
            if unknown_competencies:
                raise KnowledgeBaseValidationError(
                    f"rubric dimension {item['id']} references unknown competencies: {sorted(unknown_competencies)}"
                )

        source_statuses = [sources[source_id]["status"] for source_id in source_ids]
        retrievable = bool(source_ids) and all(status == "approved" for status in source_statuses)
        searchable = " ".join(_flatten_text(item))
        result.append(
            KnowledgeRecord(
                record_id=item["id"],
                record_type=record_type,
                version=version,
                industry_id=item["industry_id"] if "industry_id" in item else documents["competency"]["industry_id"],
                job_family_id=item["job_family_id"] if "job_family_id" in item else documents["competency"]["job_family_id"],
                role_id=item["role_id"] if "role_id" in item else documents["competency"]["role_id"],
                source_ids=source_ids,
                level_ids=item_level_ids,
                content=item,
                searchable_text=searchable,
                retrievable=retrievable,
                rubric_profile=rubric_profile,
            )
        )

    role_metadata = {
        "industry_id": documents["competency"]["industry_id"],
        "job_family_id": documents["competency"]["job_family_id"],
        "role_id": documents["competency"]["role_id"],
        "rubric_profiles": sorted(rubric_profile_ids),
        "record_count": len(result),
        "retrievable_record_count": sum(record.retrievable for record in result),
    }
    # Role data without approved sources remains valid but is not eligible for retrieval.
    return result, role_metadata


def _load_and_validate(path: Path, schema_path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = yaml.load(stream, Loader=UniqueKeySafeLoader)
    except FileNotFoundError as exc:
        raise KnowledgeBaseValidationError(f"Required knowledge-base file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise KnowledgeBaseValidationError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise KnowledgeBaseValidationError(f"Knowledge-base document must be a mapping: {path}")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise KnowledgeBaseValidationError(f"Invalid or missing schema: {schema_path}") from exc
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(data),
        key=lambda error: tuple(str(part) for part in error.path),
    )
    if errors:
        details = "; ".join(
            f"{'.'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise KnowledgeBaseValidationError(f"{path}: {details}")
    return data


def _require_supported_version(document: dict[str, Any], label: str) -> None:
    if document["version"] != 1:
        raise KnowledgeBaseValidationError(
            f"Unsupported knowledge-base version {document['version']} in {label}; supported version is 1"
        )


def _unique_mapping(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if item["id"] in result:
            raise KnowledgeBaseValidationError(f"Duplicate {label} id: {item['id']}")
        result[item["id"]] = item
    return result


def _unique_item_ids(items: list[dict[str, Any]], label: str, role_id: str) -> set[str]:
    identifiers = [item["id"] for item in items]
    if len(identifiers) != len(set(identifiers)):
        raise KnowledgeBaseValidationError(f"Duplicate {label} id in role {role_id}")
    return set(identifiers)


def _validate_references(
    source_ids: tuple[str, ...], sources: dict[str, dict[str, Any]], label: str
) -> None:
    missing = set(source_ids) - set(sources)
    if missing:
        raise KnowledgeBaseValidationError(
            f"{label} references unknown sources: {sorted(missing)}"
        )


def _flatten_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [part for nested in value.values() for part in _flatten_text(nested)]
    if isinstance(value, list):
        return [part for nested in value for part in _flatten_text(nested)]
    return []


def tokenize(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.lower().replace("đ", "d"))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return {token for token in re.findall(r"[a-z0-9_]+", ascii_text) if len(token) > 1}
