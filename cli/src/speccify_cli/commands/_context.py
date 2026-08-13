"""Shared project context for the CLI subcommands."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from speccify_core import (
    DEFAULT_GIT_CACHE_DIR,
    GitLibrary,
    Library,
    LibraryError,
    LocalLibrary,
    ProjectManifest,
    Version,
)
from speccify_core.skill import SKILL_FILENAME
from speccify_core.skill_library import LocalSkillLibrary

MANIFEST_FILENAME = "speccify.yaml"
LOCKFILE_FILENAME = "speccify.lock"
GIT_CACHE_ENV = "SPECCIFY_GIT_CACHE"


def git_cache_dir() -> Path:
    override = os.environ.get(GIT_CACHE_ENV)
    return Path(override) if override else DEFAULT_GIT_CACHE_DIR


def build_libraries(library_path: Path, *, offline: bool = False) -> list[Library]:
    """Local skill library plus git sources.

    Each library answers only for the ids it serves, so the order does not
    matter and local-only projects behave exactly as before.

    Which local library depends on what is actually in the directory. The
    `playbook.yaml` branch is a migration leftover and goes away with the last
    one in the tree.
    """
    libraries: list[Library] = []
    if library_path.is_dir():
        if any(library_path.rglob(SKILL_FILENAME)):
            libraries.append(LocalSkillLibrary(library_path))
        else:
            libraries.append(LocalLibrary(library_path))
    libraries.append(GitLibrary(cache_dir=git_cache_dir(), offline=offline))
    return libraries


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

    @classmethod
    def load(
        cls,
        project_dir: Path,
        library_override: Path | None = None,
        *,
        offline: bool = False,
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
        return cls(
            project_dir=project_dir,
            manifest_path=manifest_path,
            lockfile_path=project_dir / LOCKFILE_FILENAME,
            manifest=manifest,
            libraries=build_libraries(library_path, offline=offline),
        )
