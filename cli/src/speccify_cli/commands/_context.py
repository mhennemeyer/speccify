"""Shared project context for the CLI subcommands."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from speccify_core import (
    DEFAULT_GIT_CACHE_DIR,
    GitLibrary,
    Library,
    LibraryError,
    ProjectManifest,
    Version,
)
from speccify_core.skill_library import LocalSkillLibrary
from speccify_core.sources import SourceUnavailable, resolve_source

MANIFEST_FILENAME = "speccify.yaml"
LOCKFILE_FILENAME = "speccify.lock"
GIT_CACHE_ENV = "SPECCIFY_GIT_CACHE"


def git_cache_dir() -> Path:
    override = os.environ.get(GIT_CACHE_ENV)
    return Path(override) if override else DEFAULT_GIT_CACHE_DIR


def build_libraries(
    library_path: Path,
    *,
    sources: tuple[str, ...] = (),
    base: Path | None = None,
    offline: bool = False,
) -> tuple[list[Library], list[str]]:
    """Local skill library, the manifest's sources, then tag-pinned git sources.

    Each library answers only for the ids it serves; the local library and
    the sources are asked in order (first match wins for `@scope/name`). A
    source that is not on disk — a git URL nobody cloned yet — is skipped and
    returned in the second list, so the caller can say so when an id is not
    found.
    """
    libraries: list[Library] = []
    unavailable: list[str] = []
    if library_path.is_dir():
        libraries.append(LocalSkillLibrary(library_path))
    for location in sources:
        try:
            directory = resolve_source(location, base)
        except SourceUnavailable as exc:
            unavailable.append(str(exc))
            continue
        # `via` is the location, so the lockfile records where a skill came from.
        libraries.append(LocalSkillLibrary(directory, via=location.strip()))
    libraries.append(GitLibrary(cache_dir=git_cache_dir(), offline=offline))
    return libraries, unavailable


def fetch_bundle(libraries: list[Library], playbook_id: str, version: Version):
    """Fetch from the first library that serves this id."""
    last_error: LibraryError | None = None
    for library in libraries:
        serves = getattr(library, "serves", None)
        if serves is not None and not serves(playbook_id):
            continue
        try:
            return library.fetch(playbook_id, version)
        except LibraryError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise LibraryError(f"No library serves '{playbook_id}'.")


def list_versions(libraries: list[Library], playbook_id: str) -> list[Version]:
    for library in libraries:
        serves = getattr(library, "serves", None)
        if serves is not None and not serves(playbook_id):
            continue
        versions = library.list_versions(playbook_id)
        if versions:
            return versions
    return []


@dataclass(frozen=True)
class ProjectContext:
    project_dir: Path
    manifest_path: Path
    lockfile_path: Path
    manifest: ProjectManifest
    libraries: list[Library]
    # Sources from the manifest that are not on disk (messages, one per source).
    unavailable_sources: list[str] = field(default_factory=list)

    def not_found_hint(self) -> str:
        """Appended to 'not available' errors: the sources that could not be read."""
        if not self.unavailable_sources:
            return ""
        return " Sources not available: " + " / ".join(self.unavailable_sources)

    @classmethod
    def load(
        cls,
        project_dir: Path,
        library_override: Path | None = None,
        *,
        offline: bool = False,
        extra_source: str | None = None,
    ) -> ProjectContext:
        manifest_path = project_dir / MANIFEST_FILENAME
        if manifest_path.is_file():
            manifest = ProjectManifest.load(manifest_path)
        elif library_override is not None:
            # Pointed straight at a library, so there is nothing a manifest
            # would still have to answer. Demanding one here would mean an
            # agent cannot read a playbook that simply lives in some
            # repository — which is most of them.
            manifest = ProjectManifest()
        else:
            raise FileNotFoundError(
                f"No {MANIFEST_FILENAME} in {project_dir}. "
                f"Run `speccify init`, or pass --library to read a library directly."
            )
        library_path = (
            library_override.resolve()
            if library_override is not None
            else manifest.resolved_library_path()
        )
        sources = manifest.sources
        if extra_source and extra_source.strip() not in sources:
            sources = (*sources, extra_source.strip())
        libraries, unavailable = build_libraries(
            library_path, sources=sources, base=manifest.base_dir, offline=offline
        )
        return cls(
            project_dir=project_dir,
            manifest_path=manifest_path,
            lockfile_path=project_dir / LOCKFILE_FILENAME,
            manifest=manifest,
            libraries=libraries,
            unavailable_sources=unavailable,
        )
