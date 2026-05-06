"""Lokale Pseudo-Registry für Phase 1a.

Layout: `<root>/<scope>/<name>/<version>/spec.speccify.yaml`. Spec-IDs sind in der Form
`@<scope>/<name>` erwartet (siehe Manifest-Schema). `spec://`-IDs werden in 1a nicht
verwendet, weil das lokale Registry-Layout zwingend einen Scope braucht.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_SPEC_FILENAME = "spec.speccify.yaml"
_SCOPED_ID_PATTERN = re.compile(r"^@([a-z0-9][a-z0-9-]*)/([a-z0-9][a-z0-9-]*)$")
_SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class RegistryError(Exception):
    """Registry-Lookup ist fehlgeschlagen (Spec/Version fehlt, Layout kaputt)."""


@dataclass(frozen=True, order=True)
class Version:
    """Semver-Version (Phase 1a: nur major.minor.patch, ohne Pre-Release/Build)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, raw: str) -> Version:
        match = _SEMVER_PATTERN.match(raw)
        if not match:
            raise ValueError(
                f"Ungültige Version '{raw}': Phase 1a erlaubt nur major.minor.patch ohne Suffix."
            )
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class Spec:
    """Geladene Spec inkl. Original-Bytes (für stabile Hashes) und Pfad."""

    spec_id: str
    version: Version
    raw_bytes: bytes
    path: Path

    def parsed(self) -> dict:
        """Lazy parse: PyYAML auf den Original-Bytes."""
        return yaml.safe_load(self.raw_bytes.decode("utf-8")) or {}


class LocalRegistry:
    """Verzeichnis-basierte Pseudo-Registry. Read-only in Phase 1a."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        if not self._root.exists():
            raise RegistryError(f"Registry-Pfad existiert nicht: {self._root}")
        if not self._root.is_dir():
            raise RegistryError(f"Registry-Pfad ist kein Verzeichnis: {self._root}")

    @property
    def root(self) -> Path:
        return self._root

    def list_versions(self, spec_id: str) -> list[Version]:
        """Sortiert aufsteigend; ignoriert Verzeichnisse mit ungültiger Version."""
        scope, name = _split_id(spec_id)
        spec_dir = self._root / scope / name
        if not spec_dir.is_dir():
            return []
        versions: list[Version] = []
        for entry in spec_dir.iterdir():
            if not entry.is_dir():
                continue
            if not (entry / _SPEC_FILENAME).is_file():
                continue
            try:
                versions.append(Version.parse(entry.name))
            except ValueError:
                continue
        return sorted(versions)

    def fetch(self, spec_id: str, version: Version) -> Spec:
        scope, name = _split_id(spec_id)
        spec_path = self._root / scope / name / str(version) / _SPEC_FILENAME
        if not spec_path.is_file():
            available = self.list_versions(spec_id)
            raise RegistryError(
                f"Spec '{spec_id}@{version}' nicht in Registry {self._root} gefunden. "
                f"Verfügbare Versionen: {[str(v) for v in available] or '∅'}."
            )
        raw = spec_path.read_bytes()
        return Spec(spec_id=spec_id, version=version, raw_bytes=raw, path=spec_path)


def _split_id(spec_id: str) -> tuple[str, str]:
    match = _SCOPED_ID_PATTERN.match(spec_id)
    if not match:
        raise RegistryError(
            f"Spec-Id '{spec_id}' ist nicht im erwarteten Format '@scope/name' "
            f"(Phase 1a unterstützt nur scoped IDs in der lokalen Registry)."
        )
    return match.group(1), match.group(2)
