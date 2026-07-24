"""Runtime settings for the web backend.

Phase 1d defaults all paths to the repository checkout so the backend works
out-of-the-box from a fresh `uv sync` without any environment plumbing.
Overrides via env vars:

- `SPECCIFY_PROJECT_ROOT`: project root used for `speccify.yaml`/`speccify.lock`
  resolution (not used by the MVP routes yet — reserved for parity with the
  CLI/MCP adapters in later steps).
- `SPECCIFY_REGISTRY_PATH`: directory of the local pseudo-registry from which
  `GET /api/v1/specs` lists reference specs. Defaults to `<repo>/registry-fixtures`.
- `SPECCIFY_CACHE_DIR`: replay-cache directory. Defaults to
  `<repo>/tests/fixtures/llm-cache` (same convention as CLI/MCP).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# This file lives at apps/web/backend/src/speccify_web_backend/settings.py
# parents[5] resolves to the repository root (one level deeper than the test
# files under apps/web/backend/tests/, which correctly use parents[4]).
_REPO_ROOT = Path(__file__).resolve().parents[5]

DEFAULT_PROJECT_ROOT: Path = _REPO_ROOT
DEFAULT_REGISTRY_PATH: Path = _REPO_ROOT / "registry-fixtures"
DEFAULT_CACHE_DIR: Path = _REPO_ROOT / "tests" / "fixtures" / "llm-cache"
DEFAULT_COMPOSER_DIST: Path = _REPO_ROOT / "apps" / "composer" / "dist"

PROJECT_ROOT_ENV = "SPECCIFY_PROJECT_ROOT"
REGISTRY_PATH_ENV = "SPECCIFY_REGISTRY_PATH"
CACHE_DIR_ENV = "SPECCIFY_CACHE_DIR"
COMPOSER_DIST_ENV = "SPECCIFY_COMPOSER_DIST"


@dataclass(frozen=True)
class Settings:
    """Resolved runtime paths for the backend.

    Frozen dataclass so the app factory can stash a single instance on
    `app.state.settings` and routes read from there (FastAPI dependency-free
    access without globals).
    """

    project_root: Path
    registry_path: Path
    cache_dir: Path
    # Gebaute Composer-SPA; wird — falls vorhanden — unter `/ui` mitserviert
    # (Composer-Fenster der Desktop-App, same-origin zur API).
    composer_dist: Path = DEFAULT_COMPOSER_DIST

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            project_root=_path_from_env(PROJECT_ROOT_ENV, DEFAULT_PROJECT_ROOT),
            registry_path=_path_from_env(REGISTRY_PATH_ENV, DEFAULT_REGISTRY_PATH),
            cache_dir=_path_from_env(CACHE_DIR_ENV, DEFAULT_CACHE_DIR),
            composer_dist=_path_from_env(COMPOSER_DIST_ENV, DEFAULT_COMPOSER_DIST),
        )


def _path_from_env(env_var: str, default: Path) -> Path:
    raw = os.environ.get(env_var)
    if raw:
        return Path(raw).resolve()
    return default.resolve()
