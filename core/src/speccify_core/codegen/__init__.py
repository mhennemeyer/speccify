"""Codegen-Pipeline für Speccify.

Phase 1a: deterministisches Stub-Target (`speccify_core.codegen.stub`) — Markdown
als Platzhalter. Phase 1b Step 3: Replay-Cache + `LlmClient`-Protokoll
(`speccify_core.codegen.replay`). Phase 1b Step 4: React-LLM-Adapter
(`speccify_core.codegen.react_llm`) + Dispatcher `render_for_target`.

`render_for_target` ist die zentrale Eintrittsstelle für Codegen über alle Targets
hinweg; bestehende `render`/`render_to_files`-Re-Exports zeigen weiterhin auf den
Stub-Adapter (Phase-1a-Aufrufer). Die Umstellung von `pull`/`verify` auf den
Dispatcher folgt in Step 5.
"""

from dataclasses import dataclass

from speccify_core.codegen import react_llm as _react_llm
from speccify_core.codegen.react_llm import CodegenError
from speccify_core.codegen.replay import (
    CacheKey,
    CacheMissError,
    LlmClient,
    ReplayCache,
    ReplayCacheClient,
)
from speccify_core.codegen.stub import (
    TEMPLATE_SET,
    TEMPLATE_VERSION,
    render,
    render_to_files,
)
from speccify_core.registry import Spec

# Bekannte Targets, die `render_for_target` bedient. Erweiterung in Phase 3+
# (SwiftUI/Angular) erfolgt durch Hinzufügen weiterer Adapter-Module.
SUPPORTED_TARGETS: tuple[str, ...] = ("react",)


@dataclass(frozen=True)
class TargetRender:
    """Ergebnis eines Codegen-Aufrufs für ein Target.

    `cache_key` ist nur für LLM-basierte Targets gesetzt; Template-Targets liefern
    `None`. Aufrufer (z.B. `speccify pull`) entscheiden anhand des Wertes, welcher
    Generator-Pin (`template` vs. `llm`) ins Lockfile geschrieben wird.
    """

    files: dict[str, bytes]
    cache_key: CacheKey | None


def render_for_target(
    spec: Spec,
    target: str,
    *,
    llm_client: LlmClient | None = None,
) -> TargetRender:
    """Dispatcher: rendert eine Spec für `target` mit dem passenden Adapter.

    - `target == "react"` → `react_llm.render_to_files` (braucht `llm_client`).
    - andere Targets → `NotImplementedError` (1b deckt nur React ab).
    """
    if target == "react":
        if llm_client is None:
            raise CodegenError(
                "Codegen-Target 'react' benötigt einen llm_client (z.B. ReplayCacheClient)."
            )
        files, cache_key = _react_llm.render_to_files(spec, llm_client)
        return TargetRender(files=files, cache_key=cache_key)
    raise NotImplementedError(
        f"Codegen-Target '{target}' wird in Phase 1b nicht unterstützt. "
        f"Erwartet eines von: {', '.join(SUPPORTED_TARGETS)}."
    )


__all__ = [
    "CacheKey",
    "CacheMissError",
    "CodegenError",
    "LlmClient",
    "ReplayCache",
    "ReplayCacheClient",
    "SUPPORTED_TARGETS",
    "TEMPLATE_SET",
    "TEMPLATE_VERSION",
    "TargetRender",
    "render",
    "render_for_target",
    "render_to_files",
]
