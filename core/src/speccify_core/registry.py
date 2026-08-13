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
from pathlib import Path
from typing import Protocol, runtime_checkable

from speccify_core.playbook import ASSET_DIR, PLAYBOOK_FILENAME
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
    def playbook_bytes(self) -> bytes:
        try:
            return self.files[PLAYBOOK_FILENAME]
        except KeyError as exc:
            raise LibraryError(
                f"{self.source_id}@{self.version}: bundle has no {PLAYBOOK_FILENAME}."
            ) from exc

    def parsed(self) -> dict:
        import yaml

        return yaml.safe_load(self.playbook_bytes.decode("utf-8")) or {}

    @property
    def is_skill(self) -> bool:
        """A bundle is a skill when it carries a `SKILL.md`."""
        return SKILL_FILENAME in self.files

    def skill(self) -> Skill:
        return parse_skill(self.files[SKILL_FILENAME].decode("utf-8"))

    @property
    def declared_id(self) -> str:
        """The id written inside the bundle; falls back to the source id."""
        if self.is_skill:
            return self.skill().qualified_id or self.source_id
        return str(self.parsed().get("id", "")) or self.source_id

    @property
    def uses(self) -> tuple[str, ...]:
        """What this bundle builds on — the one thing the resolver needs from it.

        A skill declares it in `metadata.speccify.uses`, a playbook in
        `steps[].uses`. Keeping both readings here means the resolver never has
        to know which format it is looking at.
        """
        if self.is_skill:
            return self.skill().uses
        from speccify_core.playbook import parse_playbook

        return tuple(parse_playbook(self.parsed()).uses)

    @property
    def asset_paths(self) -> tuple[str, ...]:
        return tuple(sorted(p for p in self.files if p.startswith(f"{ASSET_DIR}/")))

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


class LocalLibrary:
    """Directory-backed playbook library (read-only).

    Layout: `<root>/<scope>/<name>/<version>/playbook.yaml` plus `assets/`.
    """

    def __init__(self, root: str | Path, *, via: str | None = None) -> None:
        self._root = Path(root)
        if not self._root.exists():
            raise LibraryError(f"Playbook library does not exist: {self._root}")
        if not self._root.is_dir():
            raise LibraryError(f"Playbook library is not a directory: {self._root}")
        self._via = via if via is not None else "local"

    @property
    def root(self) -> Path:
        return self._root

    @property
    def via(self) -> str:
        return self._via

    def serves(self, playbook_id: str) -> bool:
        return bool(_SCOPED_ID_PATTERN.match(playbook_id))

    def list_versions(self, playbook_id: str) -> list[Version]:
        scope, name = split_id(playbook_id)
        directory = self._root / scope / name
        if not directory.is_dir():
            return []
        versions: list[Version] = []
        for entry in directory.iterdir():
            if not entry.is_dir() or not (entry / PLAYBOOK_FILENAME).is_file():
                continue
            try:
                versions.append(Version.parse(entry.name))
            except ValueError:
                continue
        return sorted(versions)

    def list_playbooks(self) -> list[tuple[str, Version]]:
        """Every playbook in this library, sorted — used by the viewer and `search`."""
        found: list[tuple[str, Version]] = []
        for scope_dir in sorted(p for p in self._root.iterdir() if p.is_dir()):
            for name_dir in sorted(p for p in scope_dir.iterdir() if p.is_dir()):
                playbook_id = f"@{scope_dir.name}/{name_dir.name}"
                for version in self.list_versions(playbook_id):
                    found.append((playbook_id, version))
        return found

    def fetch(self, playbook_id: str, version: Version) -> Bundle:
        scope, name = split_id(playbook_id)
        directory = self._root / scope / name / str(version)
        if not (directory / PLAYBOOK_FILENAME).is_file():
            available = [str(v) for v in self.list_versions(playbook_id)]
            raise LibraryError(
                f"Playbook '{playbook_id}@{version}' not found in {self._root}. "
                f"Available: {available or 'none'}."
            )
        files: dict[str, bytes] = {PLAYBOOK_FILENAME: (directory / PLAYBOOK_FILENAME).read_bytes()}
        asset_root = directory / ASSET_DIR
        if asset_root.is_dir():
            for asset in sorted(asset_root.rglob("*")):
                if asset.is_file():
                    files[asset.relative_to(directory).as_posix()] = asset.read_bytes()
        return Bundle(
            source_id=playbook_id,
            version=version,
            files=files,
            origin=str(directory),
        )


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
LocalRegistry = LocalLibrary
MultiRegistry = MultiLibrary


__all__ = [
    "Bundle",
    "Library",
    "LibraryError",
    "LocalLibrary",
    "LocalRegistry",
    "MultiLibrary",
    "MultiRegistry",
    "Registry",
    "RegistryError",
    "Version",
    "bundle_sha256",
    "split_id",
]
