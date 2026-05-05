"""JSON-Schema-Validator für Flowcation-Specs (Draft-2020-12)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema import exceptions as js_exceptions

# Repo-Root → schema/spec.schema.json. core/src/flowcation_core/validator.py → ../../../schema/...
DEFAULT_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "spec.schema.json"
)


@dataclass(frozen=True)
class ValidationIssue:
    """Ein einzelner Schema-Verstoß, formatiert für CLI-Ausgabe."""

    path: str
    message: str

    def format(self) -> str:
        return f"{self.path}: {self.message}" if self.path else self.message


def _format_json_pointer(error: js_exceptions.ValidationError) -> str:
    if not error.absolute_path:
        return "$"
    parts: list[str] = []
    for part in error.absolute_path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            parts.append(f".{part}")
    return "$" + "".join(parts)


class SchemaValidator:
    """Validiert geladene Spec-Mappings gegen `spec.schema.json`."""

    def __init__(self, schema_path: str | Path | None = None) -> None:
        self.schema_path: Path = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
        with self.schema_path.open("r", encoding="utf-8") as fh:
            self._schema: dict[str, Any] = json.load(fh)
        Draft202012Validator.check_schema(self._schema)
        self._validator = Draft202012Validator(self._schema)

    @property
    def schema(self) -> dict[str, Any]:
        return self._schema

    def iter_issues(self, data: Any) -> list[ValidationIssue]:
        errors = sorted(self._validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        return [
            ValidationIssue(path=_format_json_pointer(err), message=err.message)
            for err in errors
        ]

    def is_valid(self, data: Any) -> bool:
        return not self.iter_issues(data)
