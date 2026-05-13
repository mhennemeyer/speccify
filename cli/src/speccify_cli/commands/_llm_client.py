"""Gemeinsamer CLI-Helfer für den Replay-LLM-Client (Phase 1b Step 5b).

`pull` und `verify` rufen den Codegen-Dispatcher `render_for_target`, der für
`target == "react"` einen `LlmClient` braucht. In CI/Tests ist das immer ein
`ReplayCacheClient` über dem eingecheckten Cache (`tests/fixtures/llm-cache/`);
mit `--offline` (Default) schlägt ein Cache-Miss hart fehl. Ohne `--offline`
kann ein optionaler Live-Bedrock-Client `inner` gesetzt werden, der bei
Cache-Miss eine Live-Antwort holt und in den Cache schreibt.
"""

from __future__ import annotations

import os
from pathlib import Path

from speccify_core import LlmClient, ReplayCache, ReplayCacheClient

# Repo-lokaler Default-Cache: passt zum eingecheckten Pfad aus Step 5a.
# core/src/speccify_core/... wird hier *nicht* angefasst; der Default ist
# bewusst CLI-spezifisch und kommt aus dem Repo-Layout.
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CACHE_DIR: Path = _REPO_ROOT / "tests" / "fixtures" / "llm-cache"
CACHE_DIR_ENV: str = "SPECCIFY_CACHE_DIR"


def resolve_cache_dir(override: Path | None) -> Path:
    """CLI-Override > Env-Var (`SPECCIFY_CACHE_DIR`) > Default-Repo-Pfad."""
    if override is not None:
        return override.resolve()
    env = os.environ.get(CACHE_DIR_ENV)
    if env:
        return Path(env).resolve()
    return DEFAULT_CACHE_DIR


def build_replay_client(
    *,
    offline: bool,
    cache_dir: Path | None,
    inner: LlmClient | None = None,
) -> ReplayCacheClient:
    """Baut einen `ReplayCacheClient` aus den CLI-Flags.

    - `offline=True` (Default): Cache-Miss → `CacheMissError`, kein Live-Call.
    - `offline=False`: Cache-Miss delegiert an `inner` (falls gesetzt, sonst
      ebenfalls Cache-Miss). `inner` ist hier nicht verdrahtet — Step 5b
      bleibt Pure-Replay; Live-Aufnahme passiert weiterhin nur über
      `scripts/record_llm_cache.py`.
    """
    cache = ReplayCache(resolve_cache_dir(cache_dir))
    return ReplayCacheClient(cache, offline=offline, inner=inner)
