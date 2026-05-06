"""Stub-Codegen-Tests: Determinismus, Output-Pfade, Inhalt."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core.codegen.stub import (
    TEMPLATE_SET,
    TEMPLATE_VERSION,
    render,
    render_to_files,
)
from speccify_core.registry import LocalRegistry, Version

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"


@pytest.fixture
def registry() -> LocalRegistry:
    return LocalRegistry(FIXTURES)


def test_render_is_deterministic(registry: LocalRegistry) -> None:
    spec = registry.fetch("@org/button", Version.parse("0.1.0"))
    first = render(spec, target="react")
    second = render(spec, target="react")
    assert first == second


def test_render_to_files_uses_scope_path(registry: LocalRegistry) -> None:
    spec = registry.fetch("@org/button", Version.parse("0.1.0"))
    files = render_to_files(spec, target="react")
    assert list(files.keys()) == ["org/button.md"]
    content = files["org/button.md"].decode("utf-8")
    assert "# Button" in content
    assert "@org/button@0.1.0" in content
    assert f"template_set: {TEMPLATE_SET}" in content
    assert f"template_version: {TEMPLATE_VERSION}" in content
    assert "## Acceptance" in content


def test_render_includes_target_frontmatter(registry: LocalRegistry) -> None:
    spec = registry.fetch("@org/button", Version.parse("0.1.0"))
    text = render(spec, target="swiftui")
    assert text.startswith("---\n")
    assert "target: swiftui" in text


def test_render_includes_uses_for_workflow(registry: LocalRegistry) -> None:
    spec = registry.fetch("@org/onboarding-wizard", Version.parse("0.1.0"))
    text = render(spec, target="react")
    assert "## Uses" in text
    assert "@org/button" in text
