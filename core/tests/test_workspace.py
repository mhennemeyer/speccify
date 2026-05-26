"""Tests für `speccify_core.workspace` (Phase 3 Stage 5)."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import (
    LocalRegistry,
    Resolver,
    Workspace,
    WorkspaceError,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_WORKSPACE = REPO_ROOT / "example-workspace"
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"


def _write_root(tmp_path: Path, body: str) -> None:
    (tmp_path / "speccify.yaml").write_text(body, encoding="utf-8")


def test_load_example_workspace_discovers_members() -> None:
    ws = Workspace.load(EXAMPLE_WORKSPACE)
    rels = [m.relative_path for m in ws.members]
    assert rels == ["packages/forms/speccify.yaml", "packages/ui/speccify.yaml"]
    assert ws.root_manifest.is_workspace_root
    # Root selbst hat keine Targets, alle Member: react.
    assert ws.aggregated_targets() == ("react",)


def test_aggregated_dependencies_traces_member_source() -> None:
    ws = Workspace.load(EXAMPLE_WORKSPACE)
    deps = ws.aggregated_dependencies()
    # `@org/button` ist in beiden Membern → zwei Constraints mit Member-Trace.
    button_sources = sorted(src for (_r, src) in deps["@org/button"])
    assert button_sources == ["packages/forms/speccify.yaml", "packages/ui/speccify.yaml"]
    # `@org/contact-form` nur in forms.
    assert [src for (_r, src) in deps["@org/contact-form"]] == ["packages/forms/speccify.yaml"]


def test_resolver_workspace_global_mvs_picks_single_version() -> None:
    ws = Workspace.load(EXAMPLE_WORKSPACE)
    resolver = Resolver(LocalRegistry(REGISTRY_FIXTURES))
    graph = resolver.resolve_workspace(ws.aggregated_dependencies())
    # @org/button taucht nur einmal auf (globale MVS — eine Version für ganzen Workspace).
    by_id = {r.spec_id: r for r in graph.resolutions}
    assert "@org/button" in by_id
    assert "@org/contact-form" in by_id
    # Bestimmt nicht doppelt → Diamond aufgelöst.
    assert len([r for r in graph.resolutions if r.spec_id == "@org/button"]) == 1


def test_workspace_root_without_workspaces_field_raises(tmp_path: Path) -> None:
    _write_root(
        tmp_path,
        "schema_version: 2\ntargets:\n  - react\ndependencies: {}\n",
    )
    with pytest.raises(WorkspaceError, match="kein `workspaces:`-Feld"):
        Workspace.load(tmp_path)


def test_workspace_with_unmatched_glob_raises(tmp_path: Path) -> None:
    _write_root(
        tmp_path,
        "schema_version: 2\nworkspaces:\n  - packages/*\ndependencies: {}\n",
    )
    with pytest.raises(WorkspaceError, match="matched keine Member-Verzeichnisse"):
        Workspace.load(tmp_path)


def test_workspace_member_missing_manifest_raises(tmp_path: Path) -> None:
    _write_root(
        tmp_path,
        "schema_version: 2\nworkspaces:\n  - packages/*\ndependencies: {}\n",
    )
    (tmp_path / "packages" / "broken").mkdir(parents=True)
    with pytest.raises(WorkspaceError, match="hat kein speccify.yaml"):
        Workspace.load(tmp_path)


def test_nested_workspaces_are_rejected(tmp_path: Path) -> None:
    _write_root(
        tmp_path,
        "schema_version: 2\nworkspaces:\n  - packages/*\ndependencies: {}\n",
    )
    inner = tmp_path / "packages" / "nested"
    inner.mkdir(parents=True)
    (inner / "speccify.yaml").write_text(
        "schema_version: 2\nworkspaces:\n  - sub/*\ndependencies: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceError, match="verschachtelte Workspaces"):
        Workspace.load(tmp_path)
