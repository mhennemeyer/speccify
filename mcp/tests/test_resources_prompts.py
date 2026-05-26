"""Unit-Tests für Phase-1c-Step-4: Resources + Prompt.

Wir testen die registrierten Resources (`speccify://manifest`,
`speccify://lockfile`, `spec://{scope}/{name}@{version}`) und den
Prompt (`add-spec`) direkt über die `FastMCP`-Instanz ohne stdio-
Subprocess (Symmetrie zu Steps 2/3).
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ResourceError
from speccify_mcp import ServerConfig, build_server

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PROJECT = REPO_ROOT / "example-project"
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"


def _copy_example_project(target: Path) -> Path:
    shutil.copytree(REGISTRY_FIXTURES, target / "registry-fixtures")
    dst = target / "example-project"
    shutil.copytree(EXAMPLE_PROJECT, dst)
    out_dir = dst / "out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    return dst


def _read_text(server, uri: str) -> str:
    chunks = asyncio.run(server.read_resource(uri))
    # FastMCP gibt eine Liste von `ReadResourceContents` zurück; wir
    # konkatenieren die Text-Inhalte.
    return "".join(getattr(c, "content", "") for c in chunks)


# ---------------------------------------------------------------- manifest


def test_manifest_resource_returns_yaml(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    server = build_server(ServerConfig(project_root=project))
    text = _read_text(server, "speccify://manifest")
    assert "schema_version: 2" in text
    assert "- react" in text  # targets: [react] als YAML-Liste


def test_manifest_resource_missing_raises(tmp_path: Path) -> None:
    server = build_server(ServerConfig(project_root=tmp_path))
    # FastMCP wraps the underlying `FileNotFoundError` in a
    # `ResourceError` before returning it to the MCP client.
    with pytest.raises(ResourceError):
        _read_text(server, "speccify://manifest")


# ---------------------------------------------------------------- lockfile


def test_lockfile_resource_returns_yaml(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    server = build_server(ServerConfig(project_root=project))
    text = _read_text(server, "speccify://lockfile")
    assert "schema_version: 3" in text
    assert "@org/button" in text


def test_lockfile_resource_returns_hint_when_missing(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    (project / "speccify.lock").unlink()
    server = build_server(ServerConfig(project_root=project))
    text = _read_text(server, "speccify://lockfile")
    assert "No speccify.lock" in text
    assert "lock" in text


# -------------------------------------------------------------------- spec


def test_spec_resource_returns_yaml_bytes(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    server = build_server(ServerConfig(project_root=project))
    text = _read_text(server, "spec://org/button@0.1.0")
    assert 'id: "@org/button"' in text or "id: '@org/button'" in text
    assert "version: 0.1.0" in text
    assert "kind: ui-component" in text


def test_spec_resource_unknown_version_raises(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    server = build_server(ServerConfig(project_root=project))
    # Template-Resources werden vor dem Read instanziiert; FastMCP
    # wickelt RegistryError dabei in einen `ValueError` ein.
    with pytest.raises(ValueError, match="9.9.9"):
        _read_text(server, "spec://org/button@9.9.9")


# ------------------------------------------------------------------ prompt


def test_add_spec_prompt_renders_with_spec_ref(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    server = build_server(ServerConfig(project_root=project))
    result = asyncio.run(server.get_prompt("add-spec", {"spec_ref": "@org/button@0.1.0"}))
    text = result.messages[0].content.text
    assert "@org/button@0.1.0" in text
    assert str(project) in text
    # Default `out_dir`.
    assert "./src/components" in text
    # Workflow-Reihenfolge ist Teil des Vertrags.
    for step in ("resolve", "lock", "pull", "verify"):
        assert f"`{step}`" in text


def test_add_spec_prompt_uses_custom_out_dir(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    server = build_server(ServerConfig(project_root=project))
    result = asyncio.run(
        server.get_prompt(
            "add-spec",
            {"spec_ref": "@org/onboarding-wizard@0.1.0", "out_dir": "./gen"},
        )
    )
    text = result.messages[0].content.text
    assert "out_dir=./gen" in text
    assert "@org/onboarding-wizard@0.1.0" in text
