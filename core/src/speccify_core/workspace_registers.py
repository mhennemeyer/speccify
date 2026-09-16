"""Portable register identities. Paths and credentials belong to local bindings."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
MANIFEST_FILE = "workspace-registers.json"


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class NamedIdentity:
    id: str
    name: str


@dataclass(frozen=True)
class RegisterManifest:
    version: int
    id: str
    name: str
    sources: tuple[NamedIdentity, ...]
    repositories: tuple[NamedIdentity, ...]
    default_source: str | None = None


def _identity(value: object) -> NamedIdentity:
    if not isinstance(value, dict) or set(value) != {"id", "name"}:
        raise ManifestError("An identity contains only id and name.")
    identity, name = value["id"], value["name"]
    if not isinstance(identity, str) or not _ID.fullmatch(identity):
        raise ManifestError("Invalid identity (letters, digits, dot, underscore, hyphen).")
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        raise ManifestError("A name must contain 1–200 characters.")
    return NamedIdentity(identity, name)


def parse_manifest(text: str) -> RegisterManifest:
    if len(text.encode("utf-8")) > 256 * 1024:
        raise ManifestError("Register manifest exceeds 256 KiB.")
    try:
        raw = json.loads(text)
    except (ValueError, TypeError) as error:
        raise ManifestError(f"Invalid register manifest JSON: {error}") from error
    if not isinstance(raw, dict) or set(raw) - {
        "version",
        "id",
        "name",
        "sources",
        "repositories",
        "default_source",
    }:
        raise ManifestError("Unknown manifest fields; paths and credentials are local bindings.")
    if type(raw.get("version")) is not int or raw["version"] != 1:
        raise ManifestError("Unsupported register manifest version.")
    workspace = _identity({"id": raw.get("id"), "name": raw.get("name")})

    def identities(key: str) -> tuple[NamedIdentity, ...]:
        values = raw.get(key)
        if not isinstance(values, list) or not 1 <= len(values) <= 100:
            raise ManifestError(f"{key} must contain 1–100 identities.")
        entries = tuple(_identity(value) for value in values)
        if len({entry.id for entry in entries}) != len(entries):
            raise ManifestError(f"Duplicate {key} identity.")
        return entries

    sources, repositories = identities("sources"), identities("repositories")
    default = raw.get("default_source")
    if default is not None and (
        not isinstance(default, str) or default not in {source.id for source in sources}
    ):
        raise ManifestError("Default register is not declared in sources.")
    return RegisterManifest(1, workspace.id, workspace.name, sources, repositories, default)


def load_manifest(path: Path) -> RegisterManifest:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024:
        raise ManifestError("Register manifest must be a regular file of at most 256 KiB.")
    return parse_manifest(path.read_text(encoding="utf-8"))
