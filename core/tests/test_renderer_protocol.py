"""Tests für `Renderer`-Protocol + `TARGETS`-Registry (Phase 3 Stage 1).

Diese Tests decken nur die neue Codegen-Abstraktion ab; das React-Dispatcher-
Verhalten ist bereits in `test_react_llm.py` getestet und wird hier nicht
dupliziert.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import (
    SUPPORTED_TARGETS,
    TARGETS,
    Renderer,
    TargetRender,
    register_target,
    render_for_target,
    supported_targets,
)
from speccify_core.registry import LocalRegistry, Spec, Version

REGISTRY_FIXTURES = Path(__file__).resolve().parents[2] / "registry-fixtures"


def _load_button() -> Spec:
    registry = LocalRegistry(REGISTRY_FIXTURES)
    return registry.fetch("@org/button", Version.parse("0.1.0"))


# --- TARGETS-Registry ---------------------------------------------------------


def test_targets_registry_contains_react() -> None:
    assert "react" in TARGETS
    assert callable(TARGETS["react"])


def test_supported_targets_is_sorted_view_of_registry() -> None:
    assert supported_targets() == tuple(sorted(TARGETS))


def test_supported_targets_constant_matches_registry_at_import_time() -> None:
    # `SUPPORTED_TARGETS` ist eine Backward-Compat-Konstante (Phase-1b-Aufrufer).
    # Sie spiegelt den Inhalt der Registry zum Import-Zeitpunkt.
    assert "react" in SUPPORTED_TARGETS


# --- register_target ----------------------------------------------------------


def test_register_target_adds_renderer_and_dispatcher_picks_it_up() -> None:
    spec = _load_button()
    sentinel_files = {"sentinel/out.txt": b"hello"}

    def _fake_renderer(spec_: Spec, *, llm_client: object | None = None) -> TargetRender:
        # signature-kompatibel mit `Renderer`-Protocol; ignoriert `llm_client`
        # (Template-Adapter-Stil).
        return TargetRender(files=dict(sentinel_files), cache_key=None)

    name = "test-fake-target"
    try:
        register_target(name, _fake_renderer)
        assert name in supported_targets()

        rendered = render_for_target(spec, name)
        assert isinstance(rendered, TargetRender)
        assert rendered.files == sentinel_files
        assert rendered.cache_key is None
    finally:
        # Test-Isolation: Registry-State zurückgeben.
        TARGETS.pop(name, None)


def test_register_target_rejects_duplicate() -> None:
    with pytest.raises(ValueError):
        register_target("react", TARGETS["react"])


# --- Renderer-Protocol --------------------------------------------------------


def test_react_renderer_satisfies_renderer_protocol() -> None:
    # `Renderer` ist ein `Protocol`; strukturelle Prüfung via `isinstance`-äquivalente
    # Duck-Type-Aufruf­barkeit. Wir prüfen, dass der React-Renderer ohne Adapter
    # aus der Registry direkt callable ist.
    react_renderer: Renderer = TARGETS["react"]
    assert callable(react_renderer)
