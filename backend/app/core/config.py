from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from yaml.constructor import ConstructorError
from yaml.resolver import BaseResolver


class ConfigValidationError(RuntimeError):
    """Raised when a project YAML config is invalid."""


class UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


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


UniqueKeySafeLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = yaml.load(stream, Loader=UniqueKeySafeLoader)
    except FileNotFoundError as exc:
        raise ConfigValidationError(f"Required configuration not found: {path.name}") from exc
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"Invalid YAML in {path.name}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigValidationError(f"Configuration root in {path.name} must be a mapping")
    return data


def _validate_schema(data: dict[str, Any], schema_path: Path, source_name: str) -> None:
    schema = _read_json(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{source_name} at {'.'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ConfigValidationError(details)


def _read_json(path: Path) -> dict[str, Any]:
    import json

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ConfigValidationError(f"Invalid or missing schema: {path.name}") from exc
    if not isinstance(value, dict):
        raise ConfigValidationError(f"Schema root in {path.name} must be an object")
    return value


def _unique_ids(items: list[dict[str, Any]], name: str) -> None:
    identifiers = [item.get("id") for item in items]
    if len(identifiers) != len(set(identifiers)):
        raise ConfigValidationError(f"Duplicate {name} id in configuration")


def _validate_levels(config: dict[str, Any]) -> None:
    levels = config["levels"]
    _unique_ids(levels, "interview level")
    level_ids = {item["id"] for item in levels}
    if config["default_level"] not in level_ids:
        raise ConfigValidationError("default_level must reference a configured level")

    for level in levels:
        mix = level["question_mix"]
        total = mix["behavioral"] + mix["role_specific"]
        if abs(total - 1.0) > 0.000001:
            raise ConfigValidationError(
                f"question_mix for {level['id']} must sum to 1 (received {total})"
            )


def _validate_pressure_profiles(config: dict[str, Any]) -> None:
    profiles = config["profiles"]
    if config["default_profile"] not in profiles:
        raise ConfigValidationError(
            "default_profile must reference a configured pressure profile"
        )


def _validate_document_processing(config: dict[str, Any]) -> None:
    extensions = [item["extension"] for item in config["accepted_formats"]]
    kinds = [item["kind"] for item in config["accepted_formats"]]
    if len(extensions) != len(set(extensions)) or len(kinds) != len(set(kinds)):
        raise ConfigValidationError("Document processing formats must be unique")
    if set(extensions) != {".pdf", ".docx"} or set(kinds) != {"pdf", "docx"}:
        raise ConfigValidationError("Document processing must configure PDF and DOCX formats")
    if config["max_docx_uncompressed_size_bytes"] < config["max_file_size_bytes"]:
        raise ConfigValidationError(
            "max_docx_uncompressed_size_bytes must be at least max_file_size_bytes"
        )


def load_runtime_config(project_root: Path) -> dict[str, Any]:
    """Load and validate config once during application startup."""
    config_dir = project_root / "configs"
    schema_dir = config_dir / "schemas"
    levels = _read_yaml(config_dir / "interview_levels.yaml")
    pressure = _read_yaml(config_dir / "pressure_profiles.yaml")
    documents = _read_yaml(config_dir / "document_processing.yaml")

    _validate_schema(
        levels, schema_dir / "interview_levels.schema.json", "interview_levels.yaml"
    )
    _validate_schema(
        pressure,
        schema_dir / "pressure_profiles.schema.json",
        "pressure_profiles.yaml",
    )
    _validate_levels(levels)
    _validate_pressure_profiles(pressure)
    _validate_schema(
        documents,
        schema_dir / "document_processing.schema.json",
        "document_processing.yaml",
    )
    _validate_document_processing(documents)
    return {
        "interview_levels": levels,
        "pressure_profiles": pressure,
        "document_processing": documents,
    }
