"""Runtime settings for the web backend.

Everything defaults to the repository checkout, so the backend works from a
fresh `uv sync` without environment plumbing. Overrides via env vars:

- `SPECCIFY_PROJECT_ROOT`: project root for `speccify.yaml` / `speccify.lock`.
- `SPECCIFY_LIBRARY_PATH`: the playbook library `GET /api/v1/skills` lists.
  Defaults to `<repo>/skills`.
- `SPECCIFY_COMPOSER_DIST`: the built viewer SPA, served under `/ui` when present.
- `SPECCIFY_GIT_CACHE`: bare-clone cache for git playbook sources and index
  repos. Defaults to `~/.cache/speccify/git` (same convention as the CLI).
- `SPECCIFY_INDEX`: comma-separated discovery index sources (local directories
  or `git+<url>`) served by `GET /api/v1/index`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from speccify_core import DEFAULT_GIT_CACHE_DIR, GitLibrary, Library, MultiLibrary
from speccify_core.skill_library import LocalSkillLibrary

# This file lives at apps/web/backend/src/speccify_web_backend/settings.py
# parents[5] resolves to the repository root (one level deeper than the test
# files under apps/web/backend/tests/, which correctly use parents[4]).
_REPO_ROOT = Path(__file__).resolve().parents[5]

DEFAULT_PROJECT_ROOT: Path = _REPO_ROOT
DEFAULT_LIBRARY_PATH: Path = _REPO_ROOT / "skills"
DEFAULT_COMPOSER_DIST: Path = _REPO_ROOT / "apps" / "composer" / "dist"

PROJECT_ROOT_ENV = "SPECCIFY_PROJECT_ROOT"
LIBRARY_PATH_ENV = "SPECCIFY_LIBRARY_PATH"
COMPOSER_DIST_ENV = "SPECCIFY_COMPOSER_DIST"
GIT_CACHE_ENV = "SPECCIFY_GIT_CACHE"
INDEX_ENV = "SPECCIFY_INDEX"


@dataclass(frozen=True)
class Settings:
    """Resolved runtime paths for the backend.

    Frozen dataclass so the app factory can stash a single instance on
    `app.state.settings` and routes read from there (FastAPI dependency-free
    access without globals).
    """

    project_root: Path
    library_path: Path
    # The built viewer SPA; served under `/ui` when present (the desktop app's
    # viewer window, same-origin with the API).
    composer_dist: Path = DEFAULT_COMPOSER_DIST
    # Bare-clone cache for git sources and index repositories.
    git_cache_dir: Path = DEFAULT_GIT_CACHE_DIR
    # Discovery index sources (local directories or `git+<url>`).
    index_sources: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> Settings:
        raw_index = os.environ.get(INDEX_ENV, "").strip()
        return cls(
            project_root=_path_from_env(PROJECT_ROOT_ENV, DEFAULT_PROJECT_ROOT),
            library_path=_path_from_env(LIBRARY_PATH_ENV, DEFAULT_LIBRARY_PATH),
            composer_dist=_path_from_env(COMPOSER_DIST_ENV, DEFAULT_COMPOSER_DIST),
            git_cache_dir=_path_from_env(GIT_CACHE_ENV, DEFAULT_GIT_CACHE_DIR),
            index_sources=tuple(part.strip() for part in raw_index.split(",") if part.strip()),
        )

    def library(self) -> Library:
        """The backend's playbook source: local library plus git sources.

        `serves` decides per id who answers, so git playbooks arrive here
        without a special case — exactly like on the CLI path.
        """
        libraries: list[Library] = []
        if self.library_path.is_dir():
            libraries.append(LocalSkillLibrary(self.library_path))
        libraries.append(GitLibrary(cache_dir=self.git_cache_dir))
        return MultiLibrary(libraries)


def _path_from_env(env_var: str, default: Path) -> Path:
    raw = os.environ.get(env_var)
    if raw:
        return Path(raw).resolve()
    return default.resolve()
