"""Playbook sources: bundles, local libraries and the `Library` protocol.

A playbook is a **bundle**, not a single file: `playbook.yaml` plus an optional
`assets/` tree. That is what makes assets shareable and what the lockfile pins
— a hash over the whole bundle, not just the YAML.

Local layout: `<root>/<scope>/<name>/<version>/playbook.yaml`. Git sources live
in `git_registry.py` and satisfy the same protocol.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from speccify_core.skill import SKILL_FILENAME, Skill, parse_skill

_SCOPED_ID_PATTERN = re.compile(r"^@([a-z0-9][a-z0-9-]*)/([a-z0-9][a-z0-9-]*)$")
_SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class LibraryError(Exception):
    """A playbook could not be found or read."""


# Kept as an alias: callers and error paths across CLI/MCP/web still speak of
# "registry errors", and renaming that vocabulary everywhere buys nothing.
RegistryError = LibraryError


@dataclass(frozen=True, order=True)
class Version:
    """SemVer without pre-release or build metadata."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, raw: str) -> Version:
        match = _SEMVER_PATTERN.match(raw)
        if not match:
            raise ValueError(f"Invalid version '{raw}': expected major.minor.patch.")
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class Bundle:
    """A playbook bundle: every file that belongs to it, keyed by relative path.

    `files` always contains `playbook.yaml`; assets live under `assets/`.
    `source_id` is where it came from (local id or git ref) — the *declared* id
    lives inside the YAML and can differ.
    """

    source_id: str
    version: Version
    files: dict[str, bytes]
    origin: str = ""
    source_commit: str | None = None

    @property
    def is_skill(self) -> bool:
        """A bundle is a skill when it carries a `SKILL.md`."""
        return SKILL_FILENAME in self.files

    def skill(self) -> Skill:
        try:
            return parse_skill(self.files[SKILL_FILENAME].decode("utf-8"))
        except KeyError as exc:
            raise LibraryError(
                f"{self.source_id}@{self.version}: bundle has no {SKILL_FILENAME}."
            ) from exc

    @property
    def declared_id(self) -> str:
        """The id written inside the bundle; falls back to the source id."""
        return self.skill().qualified_id or self.source_id

    @property
    def uses(self) -> tuple[str, ...]:
        """What this skill builds on — the one thing the resolver needs from it."""
        return self.skill().uses

    @property
    def asset_paths(self) -> tuple[str, ...]:
        """Everything bundled beside the SKILL.md."""
        return tuple(sorted(p for p in self.files if p != SKILL_FILENAME))

    @property
    def sha256(self) -> str:
        return bundle_sha256(self.files)


def bundle_sha256(files: dict[str, bytes]) -> str:
    """Deterministic hash over a bundle: sorted paths plus their contents.

    Paths are part of the hash, so renaming an asset changes it. Length
    prefixes keep `a/b` + `c` from colliding with `a` + `b/c`.
    """
    digest = hashlib.sha256()
    for path in sorted(files):
        raw_path = path.encode("utf-8")
        digest.update(len(raw_path).to_bytes(8, "big"))
        digest.update(raw_path)
        digest.update(len(files[path]).to_bytes(8, "big"))
        digest.update(files[path])
    return f"sha256:{digest.hexdigest()}"


@runtime_checkable
class Library(Protocol):
    """Common protocol for local and git playbook sources."""

    @property
    def via(self) -> str: ...

    def serves(self, playbook_id: str) -> bool: ...

    def list_versions(self, playbook_id: str) -> list[Version]: ...

    def fetch(self, playbook_id: str, version: Version) -> Bundle: ...


# Same reasoning as `RegistryError`: the protocol name stays available under the
# older vocabulary so adapters do not need to churn.
Registry = Library


def split_id(playbook_id: str) -> tuple[str, str]:
    match = _SCOPED_ID_PATTERN.match(playbook_id)
    if not match:
        raise LibraryError(f"Playbook id '{playbook_id}' is not of the form '@scope/name'.")
    return match.group(1), match.group(2)


class MultiLibrary:
    """Fans one `Library` facade out over several sources.

    The resolver takes a list by itself; everything else (viewer, MCP tools,
    web routes) expects exactly one source. This facade routes each request to
    the first library that serves the id.
    """

    def __init__(self, libraries: list[Library]) -> None:
        if not libraries:
            raise LibraryError("MultiLibrary needs at least one library.")
        self._libraries = list(libraries)

    @property
    def libraries(self) -> list[Library]:
        return list(self._libraries)

    @property
    def via(self) -> str:
        return "multi"

    def serves(self, playbook_id: str) -> bool:
        return any(self._serves(lib, playbook_id) for lib in self._libraries)

    @staticmethod
    def _serves(library: Library, playbook_id: str) -> bool:
        predicate = getattr(library, "serves", None)
        return True if predicate is None else bool(predicate(playbook_id))

    def list_versions(self, playbook_id: str) -> list[Version]:
        for library in self._libraries:
            if not self._serves(library, playbook_id):
                continue
            versions = library.list_versions(playbook_id)
            if versions:
                return versions
        return []

    def fetch(self, playbook_id: str, version: Version) -> Bundle:
        last_error: LibraryError | None = None
        for library in self._libraries:
            if not self._serves(library, playbook_id):
                continue
            try:
                return library.fetch(playbook_id, version)
            except LibraryError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise LibraryError(f"No library serves '{playbook_id}'.")


# Older vocabulary, same objects.
MultiRegistry = MultiLibrary


__all__ = [
    "Bundle",
    "Library",
    "LibraryError",
    "MultiLibrary",
    "MultiRegistry",
    "Registry",
    "RegistryError",
    "Version",
    "bundle_sha256",
    "split_id",
]
