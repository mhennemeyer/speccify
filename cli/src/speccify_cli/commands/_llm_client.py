"""Gemeinsamer CLI-Helfer für den Replay-LLM-Client (Phase 1b Step 5b).

`pull` und `verify` rufen den Codegen-Dispatcher `render_for_target`, der für
`target == "react"` einen `LlmClient` braucht. In CI/Tests ist das immer ein
`ReplayCacheClient` über dem eingecheckten Cache (`tests/fixtures/llm-cache/`);
mit `--offline` (Default) schlägt ein Cache-Miss hart fehl.

Mit `--no-offline` (lokales Dogfooding) wird automatisch ein Live-Bedrock-Client
als `inner` verdrahtet: bei Cache-Miss holt er eine Live-Antwort über AWS
Bedrock und legt sie im Replay-Cache ab. Die AWS-Credentials kommen aus der
Umgebung bzw. aus einer `.env` am Repo-Root (analog `scripts/record_llm_cache.py`).
CI ruft `pull`/`verify` immer mit `--offline` — der Live-Pfad wird dort nie
betreten.
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


def _load_dotenv(path: Path) -> None:
    """Minimaler `.env`-Loader: `KEY=VALUE` → `os.environ` (Shell-Exports gewinnen).

    Bewusst ohne `python-dotenv`-Dependency und identisch zur Semantik in
    `scripts/record_llm_cache.py`: Kommentare/Leerzeilen werden ignoriert,
    umschließende Quotes entfernt, eine fehlende Datei ist ein No-Op.
    """
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def build_live_bedrock_client() -> LlmClient:
    """Baut den Live-`BedrockClient` für den `--no-offline`-Pfad.

    Lädt zuerst eine `.env` am Repo-Root (falls vorhanden), löst die Region aus
    `AWS_REGION`/`AWS_DEFAULT_REGION` auf und delegiert ansonsten an die
    AWS-Standard-Credential-Chain. `boto3` wird erst beim ersten `complete`
    lazy importiert — das Konstruieren bleibt billig und dependency-frei.
    """
    # Lazy-Import: hält den Modul-Load schlank und vermeidet eine harte
    # Kopplung an die optionale `bedrock`-Extra, solange offline gefahren wird.
    from speccify_core.codegen.bedrock_client import BedrockClient

    _load_dotenv(_REPO_ROOT / ".env")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    return BedrockClient(region=region)


def build_replay_client(
    *,
    offline: bool,
    cache_dir: Path | None,
    inner: LlmClient | None = None,
) -> ReplayCacheClient:
    """Baut einen `ReplayCacheClient` aus den CLI-Flags.

    - `offline=True` (Default): Cache-Miss → `CacheMissError`, kein Live-Call.
    - `offline=False`: Cache-Miss delegiert an `inner`. Ist kein `inner`
      gesetzt, wird automatisch ein Live-`BedrockClient` verdrahtet
      (lokales Dogfooding, Credentials aus Umgebung/`.env`). Die Live-Antwort
      wird anschließend in den Replay-Cache geschrieben.
    """
    cache = ReplayCache(resolve_cache_dir(cache_dir))
    if not offline and inner is None:
        inner = build_live_bedrock_client()
    return ReplayCacheClient(cache, offline=offline, inner=inner)
