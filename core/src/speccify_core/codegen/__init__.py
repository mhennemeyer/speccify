"""Codegen-Pipeline für Speccify.

Phase 1a: deterministisches Stub-Target (`speccify_core.codegen.stub`) — Markdown
als Platzhalter. Phase 1b Step 3: Replay-Cache + `LlmClient`-Protokoll
(`speccify_core.codegen.replay`). Phase 1b Step 4: React-LLM-Adapter
(`speccify_core.codegen.react_llm`) + Dispatcher `render_for_target`.

Phase 3 Stage 1: `Renderer`-Protocol + `TARGETS`-Registry — target-agnostische
Abstraktion über alle Codegen-Adapter. `render_for_target` delegiert ab jetzt an
die Registry; neue Targets (SwiftUI/Angular in Phase 3 Stage 2/3) registrieren
sich, ohne den Dispatcher zu verändern. Bestehende React-Semantik bleibt
byte-identisch — keine Verhaltens­änderung für Phase-1b/2-Aufrufer.
"""

from dataclasses import dataclass
from typing import Protocol

from speccify_core.codegen import angular_llm as _angular_llm
from speccify_core.codegen import react_llm as _react_llm
from speccify_core.codegen import swiftui_llm as _swiftui_llm
from speccify_core.codegen.app_react import (
    APP_TEMPLATE_SET,
    APP_TEMPLATE_VERSION,
    AppCodegenError,
    AppRender,
    render_app_project,
)
from speccify_core.codegen.mock_react import (
    MOCK_TEMPLATE_SET,
    MOCK_TEMPLATE_VERSION,
    MockCodegenError,
    MockRender,
    MockUnavailableError,
    mock_output_path,
    render_mock_closure,
    render_mock_files,
)
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


@dataclass(frozen=True)
class TargetRender:
    """Ergebnis eines Codegen-Aufrufs für ein Target.

    `cache_key` ist nur für LLM-basierte Targets gesetzt; Template-Targets liefern
    `None`. Aufrufer (z.B. `speccify pull`) entscheiden anhand des Wertes, welcher
    Generator-Pin (`template` vs. `llm`) ins Lockfile geschrieben wird.
    """

    files: dict[str, bytes]
    cache_key: CacheKey | None


class Renderer(Protocol):
    """Target-agnostische Codegen-Schnittstelle.

    Adapter (React/SwiftUI/Angular/...) implementieren diese Funktion und werden
    in `TARGETS` registriert. `llm_client` ist optional: Template-Adapter
    ignorieren ihn, LLM-Adapter erwarten ihn und sollen einen `CodegenError`
    werfen, wenn er fehlt.
    """

    def __call__(self, spec: Spec, *, llm_client: LlmClient | None = None) -> TargetRender: ...


def _render_react(spec: Spec, *, llm_client: LlmClient | None = None) -> TargetRender:
    """Renderer-Adapter für React (`kind: llm` mit Replay-Cache)."""
    if llm_client is None:
        raise CodegenError(
            "Codegen-Target 'react' benötigt einen llm_client (z.B. ReplayCacheClient)."
        )
    files, cache_key = _react_llm.render_to_files(spec, llm_client)
    return TargetRender(files=files, cache_key=cache_key)


def _render_swiftui(spec: Spec, *, llm_client: LlmClient | None = None) -> TargetRender:
    """Renderer-Adapter für SwiftUI (`kind: llm` mit Replay-Cache)."""
    if llm_client is None:
        raise CodegenError(
            "Codegen-Target 'swiftui' benötigt einen llm_client (z.B. ReplayCacheClient)."
        )
    files, cache_key = _swiftui_llm.render_to_files(spec, llm_client)
    return TargetRender(files=files, cache_key=cache_key)


def _render_angular(spec: Spec, *, llm_client: LlmClient | None = None) -> TargetRender:
    """Renderer-Adapter für Angular (`kind: llm` mit Replay-Cache)."""
    if llm_client is None:
        raise CodegenError(
            "Codegen-Target 'angular' benötigt einen llm_client (z.B. ReplayCacheClient)."
        )
    files, cache_key = _angular_llm.render_to_files(spec, llm_client)
    return TargetRender(files=files, cache_key=cache_key)


# Registry aller bekannten Targets. Phase 3 Stage 3 schliesst Angular an;
# weitere Targets (Jetpack Compose etc.) tragen sich hier ein. Dispatcher und
# `SUPPORTED_TARGETS` lesen ausschließlich aus dieser Map.
TARGETS: dict[str, Renderer] = {
    "react": _render_react,
    "swiftui": _render_swiftui,
    "angular": _render_angular,
}


def register_target(name: str, renderer: Renderer) -> None:
    """Registriert einen Renderer unter `name`. Doppelregistrierung → `ValueError`."""
    if name in TARGETS:
        raise ValueError(f"Codegen-Target '{name}' ist bereits registriert.")
    TARGETS[name] = renderer


def supported_targets() -> tuple[str, ...]:
    """Stabile Sicht (sortiert) auf die aktuell registrierten Targets."""
    return tuple(sorted(TARGETS))


# Backward-Compat: bestehende Aufrufer importieren `SUPPORTED_TARGETS` als
# Konstante. Sie spiegelt den Inhalt der Registry zum Import-Zeitpunkt; neue
# Targets sollten `supported_targets()` aufrufen.
SUPPORTED_TARGETS: tuple[str, ...] = supported_targets()


def render_for_target(
    spec: Spec,
    target: str,
    *,
    llm_client: LlmClient | None = None,
) -> TargetRender:
    """Dispatcher: rendert eine Spec für `target` über die `TARGETS`-Registry."""
    renderer = TARGETS.get(target)
    if renderer is None:
        known = ", ".join(supported_targets())
        raise NotImplementedError(
            f"Codegen-Target '{target}' wird nicht unterstützt. Erwartet eines von: {known}."
        )
    return renderer(spec, llm_client=llm_client)


__all__ = [
    "APP_TEMPLATE_SET",
    "APP_TEMPLATE_VERSION",
    "AppCodegenError",
    "AppRender",
    "render_app_project",
    "CacheKey",
    "CacheMissError",
    "CodegenError",
    "MOCK_TEMPLATE_SET",
    "MOCK_TEMPLATE_VERSION",
    "MockCodegenError",
    "MockRender",
    "MockUnavailableError",
    "mock_output_path",
    "render_mock_closure",
    "render_mock_files",
    "LlmClient",
    "Renderer",
    "ReplayCache",
    "ReplayCacheClient",
    "SUPPORTED_TARGETS",
    "TARGETS",
    "TEMPLATE_SET",
    "TEMPLATE_VERSION",
    "TargetRender",
    "register_target",
    "render",
    "render_for_target",
    "render_to_files",
    "supported_targets",
]
