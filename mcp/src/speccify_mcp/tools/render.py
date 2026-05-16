"""`render`-Tool: rendert eine Spec aus dem Lockfile, ohne auf Disk zu schreiben.

Spiegelt den Render-Schritt von `speccify pull` für eine einzelne Spec.
- Liest `speccify.lock`, sucht den Eintrag `spec_id`.
- Fetcht die Spec über die Registry (Resolution aus Lockfile).
- Ruft `render_for_target` mit `ReplayCacheClient` (Default: offline).
- Gibt `{path: text}`-Dict + optional `generator_pin` zurück.

Bytes werden als utf-8-Text zurückgegeben — TSX (React) und Markdown
(Stub) sind beide Text. Nicht-utf-8-Targets (z.B. binäre Assets in
späteren Phasen) müssen das Tool erweitern (Base64-Variante).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speccify_core import (
    LocalRegistry,
    Lockfile,
    LockfileError,
    ProjectManifest,
    ReplayCache,
    ReplayCacheClient,
    Version,
    render_for_target,
)

MANIFEST_FILENAME = "speccify.yaml"
LOCKFILE_FILENAME = "speccify.lock"
CACHE_DIR_ENV = "SPECCIFY_CACHE_DIR"

# Repo-lokaler Default-Cache (gleiche Konvention wie cli/_llm_client.py).
# mcp/src/speccify_mcp/tools/render.py → parents[4] == Repo-Root.
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CACHE_DIR: Path = _REPO_ROOT / "tests" / "fixtures" / "llm-cache"


def _resolve_cache_dir(override: Path | None) -> Path:
    if override is not None:
        return override.resolve()
    env = os.environ.get(CACHE_DIR_ENV)
    if env:
        return Path(env).resolve()
    return DEFAULT_CACHE_DIR


@dataclass(frozen=True)
class RenderResult:
    spec_id: str
    target: str
    files: dict[str, str]
    generator_pin: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "target": self.target,
            "files": dict(self.files),
            "generator_pin": (dict(self.generator_pin) if self.generator_pin is not None else None),
        }


def run_render(
    project_root: Path,
    spec_id: str,
    *,
    target: str | None = None,
    offline: bool = True,
    cache_dir: Path | None = None,
) -> RenderResult:
    """Rendert eine einzelne Spec aus dem Lockfile.

    - `project_root`: Verzeichnis mit `speccify.yaml` + `speccify.lock`.
    - `spec_id`: z.B. `@org/button` — muss im Lockfile vorkommen.
    - `target` (optional): überschreibt nichts, dient nur dem Cross-Check
      gegen das Lockfile-Target (Drift wird als Fehler signalisiert).
    - `offline=True`: Cache-Miss → `CacheMissError`.
    """
    manifest_path = project_root / MANIFEST_FILENAME
    lockfile_path = project_root / LOCKFILE_FILENAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Kein Manifest gefunden: {manifest_path}")
    if not lockfile_path.is_file():
        raise LockfileError(
            f"Kein Lockfile gefunden: {lockfile_path}. Bitte zuerst `lock` aufrufen."
        )

    manifest = ProjectManifest.load(manifest_path)
    lockfile = Lockfile.load(lockfile_path)

    if target is not None and target != lockfile.target:
        raise LockfileError(
            f"target '{target}' weicht vom Lockfile-Target "
            f"'{lockfile.target}' ab. Bitte zuerst `lock` mit gewünschtem "
            f"Target ausführen."
        )

    entry = next((e for e in lockfile.entries if e.id == spec_id), None)
    if entry is None:
        known = ", ".join(sorted(e.id for e in lockfile.entries)) or "<keine>"
        raise LookupError(f"spec_id '{spec_id}' nicht im Lockfile. Bekannte IDs: {known}.")

    registry = LocalRegistry(manifest.resolved_registry_path())
    spec = registry.fetch(entry.id, Version.parse(entry.version))

    cache = ReplayCache(_resolve_cache_dir(cache_dir))
    llm_client = ReplayCacheClient(cache, offline=offline)

    rendered = render_for_target(spec, lockfile.target, llm_client=llm_client)

    files = {rel_path: data.decode("utf-8") for rel_path, data in sorted(rendered.files.items())}
    generator_pin: dict[str, Any] | None = None
    if rendered.cache_key is not None:
        generator_pin = {
            "kind": "llm",
            "model": rendered.cache_key.model,
            "prompt_version": rendered.cache_key.prompt_version,
            "cache_key": f"sha256:{rendered.cache_key.digest()}",
            "seed": rendered.cache_key.seed,
        }
    return RenderResult(
        spec_id=spec_id,
        target=lockfile.target,
        files=files,
        generator_pin=generator_pin,
    )
