"""Lockfile (`speccify.lock`): which playbook bundle, from where, at which commit.

Version 1 is a clean restart alongside the playbook schema. There is no code
generation any more, so there are no generator pins and no output hashes — what
has to stay reproducible is the *bundle*: same id, same version, same bytes,
same commit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

DEFAULT_LOCKFILE_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parent / "schemas" / "lockfile.schema.json"
)
CURRENT_LOCKFILE_SCHEMA_VERSION: int = 1


class LockfileError(Exception):
    """A lockfile could not be read, validated or written."""


@dataclass(frozen=True)
class LockEntry:
    id: str
    version: str
    resolved_via: str
    bundle_sha256: str
    # Git sources only: the commit behind the resolved tag.
    source_commit: str | None = None


@dataclass(frozen=True)
class Lockfile:
    entries: tuple[LockEntry, ...] = ()
    schema_version: int = CURRENT_LOCKFILE_SCHEMA_VERSION

    def entry(self, playbook_id: str) -> LockEntry | None:
        return next((e for e in self.entries if e.id == playbook_id), None)

    @classmethod
    def load(cls, path: str | Path, schema_path: str | Path | None = None) -> Lockfile:
        lock_path = Path(path)
        try:
            text = lock_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise LockfileError(f"Could not read lockfile {lock_path}: {exc}") from exc
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise LockfileError(f"Invalid YAML in {lock_path}: {exc}") from exc
        if not isinstance(data, dict):
            raise LockfileError(f"A lockfile must be a mapping: {lock_path}")

        _validate(data, schema_path or DEFAULT_LOCKFILE_SCHEMA_PATH, lock_path)
        return cls(
            entries=tuple(
                LockEntry(
                    id=item["id"],
                    version=item["version"],
                    resolved_via=item["resolved_via"],
                    bundle_sha256=item["bundle_sha256"],
                    source_commit=item.get("source_commit"),
                )
                for item in data["playbooks"]
            )
        )

    def write(self, path: str | Path, schema_path: str | Path | None = None) -> None:
        out_path = Path(path)
        payload = self.to_dict()
        _validate(payload, schema_path or DEFAULT_LOCKFILE_SCHEMA_PATH, out_path)
        out_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "playbooks": [
                {
                    key: value
                    for key, value in (
                        ("id", entry.id),
                        ("version", entry.version),
                        ("resolved_via", entry.resolved_via),
                        ("source_commit", entry.source_commit),
                        ("bundle_sha256", entry.bundle_sha256),
                    )
                    if value is not None
                }
                for entry in sorted(self.entries, key=lambda e: e.id)
            ],
        }


def build_lockfile(resolutions: list[Any]) -> Lockfile:
    """Build a lockfile from resolver output.

    `resolutions` carry `playbook_id`, `version`, `bundle_sha256`, `via` and
    optionally `source_commit` — typed as `Any` so this module stays
    independent of the resolver.
    """
    return Lockfile(
        entries=tuple(
            LockEntry(
                id=r.playbook_id,
                version=str(r.version),
                resolved_via=r.via,
                bundle_sha256=r.bundle_sha256,
                source_commit=getattr(r, "source_commit", None),
            )
            for r in sorted(resolutions, key=lambda r: r.playbook_id)
        )
    )


_VALIDATORS: dict[Path, Draft202012Validator] = {}


def _validate(data: Any, schema_path: str | Path, context: Path) -> None:
    key = Path(schema_path)
    validator = _VALIDATORS.get(key)
    if validator is None:
        try:
            schema = json.loads(key.read_text(encoding="utf-8"))
        except OSError as exc:
            raise LockfileError(f"Could not read lockfile schema {key}: {exc}") from exc
        validator = Draft202012Validator(schema)
        _VALIDATORS[key] = validator
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        location = "/".join(str(p) for p in first.absolute_path) or "$"
        raise LockfileError(
            f"{context}: lockfile does not match the schema at {location}: {first.message}"
        )


__all__ = [
    "CURRENT_LOCKFILE_SCHEMA_VERSION",
    "DEFAULT_LOCKFILE_SCHEMA_PATH",
    "LockEntry",
    "Lockfile",
    "LockfileError",
    "build_lockfile",
]
