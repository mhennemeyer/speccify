"""Unit-Tests für die Phase-1c-Step-2-Tools (`resolve`, `lint`, `render`).

Wir testen die reinen Adapter-Funktionen (`run_resolve`/`run_lint`/
`run_render`) direkt — kein MCP-Subprocess nötig. Damit decken wir
Happy- und Fehlerpfad pro Tool ab, ohne stdio-Roundtrip-Overhead. Die
end-to-end stdio-Verbindung kommt in Step 5 (CI-Smoke).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from speccify_core import CacheMissError, LockfileError, SpecLoaderError
from speccify_mcp.tools import run_lint, run_render, run_resolve

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PROJECT = REPO_ROOT / "example-project"
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
SPECS_DIR = REPO_ROOT / "specs"


def _copy_example_project(target: Path) -> Path:
    """Kopiert `example-project/` + `registry-fixtures/` nach `target`.

    Das Manifest enthält `registry.path: ../registry-fixtures`; wir
    spiegeln das Repo-Layout neben dem kopierten Projekt, damit die
    Auflösung in `tmp_path` ohne weitere Konfiguration funktioniert.
    """
    shutil.copytree(REGISTRY_FIXTURES, target / "registry-fixtures")
    dst = target / "example-project"
    shutil.copytree(EXAMPLE_PROJECT, dst)
    # `out/` ist Codegen-Artefakt und für die Tools irrelevant.
    out_dir = dst / "out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    return dst


# ---------------------------------------------------------------- resolve


def test_run_resolve_happy_path(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    result = run_resolve(project)
    payload = result.to_dict()
    assert payload["target"] == "react"
    ids = sorted(r["spec_id"] for r in payload["resolutions"])
    assert "@org/button" in ids
    assert "@org/onboarding-wizard" in ids
    for r in payload["resolutions"]:
        assert r["spec_sha256"].startswith("sha256:")
        # Version ist als String serialisiert (MCP-JSON-kompatibel).
        assert isinstance(r["version"], str)


def test_run_resolve_missing_manifest(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_resolve(tmp_path)


# ------------------------------------------------------------------- lint


def test_run_lint_valid_spec() -> None:
    result = run_lint(SPECS_DIR / "button.speccify.yaml")
    payload = result.to_dict()
    assert payload["ok"] is True
    assert payload["skipped"] is False
    assert payload["issues"] == []


def test_run_lint_skips_project_manifest(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    result = run_lint(project / "speccify.yaml")
    payload = result.to_dict()
    assert payload["ok"] is True
    assert payload["skipped"] is True


def test_run_lint_reports_schema_issues(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    # `kind` ist gesetzt → kein Skip; aber Pflichtfelder fehlen → Issues.
    bad.write_text("kind: component\nname: Foo\n", encoding="utf-8")
    result = run_lint(bad)
    payload = result.to_dict()
    assert payload["ok"] is False
    assert payload["skipped"] is False
    assert len(payload["issues"]) >= 1
    for issue in payload["issues"]:
        assert "path" in issue and "message" in issue


def test_run_lint_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_lint(tmp_path / "does-not-exist.yaml")


def test_run_lint_invalid_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "broken.yaml"
    bad.write_text("kind: component\n  bad-indent: [\n", encoding="utf-8")
    with pytest.raises(SpecLoaderError):
        run_lint(bad)


# ----------------------------------------------------------------- render


def _project_with_lockfile(tmp_path: Path) -> Path:
    """Kopiert example-project inkl. eingechecktem speccify.lock."""
    return _copy_example_project(tmp_path)


def test_run_render_happy_path_for_button(tmp_path: Path) -> None:
    project = _project_with_lockfile(tmp_path)
    result = run_render(project, "@org/button")
    payload = result.to_dict()
    assert payload["spec_id"] == "@org/button"
    assert payload["target"] == "react"
    assert payload["files"], "render muss mindestens eine Datei liefern"
    for rel_path, content in payload["files"].items():
        assert rel_path.endswith(".tsx")
        assert isinstance(content, str)
        assert content.strip(), f"leerer Inhalt für {rel_path}"
    pin = payload["generator_pin"]
    assert pin is not None
    assert pin["kind"] == "llm"
    assert pin["cache_key"].startswith("sha256:")


def test_run_render_unknown_spec_id(tmp_path: Path) -> None:
    project = _project_with_lockfile(tmp_path)
    with pytest.raises(LookupError):
        run_render(project, "@org/does-not-exist")


def test_run_render_target_mismatch_is_error(tmp_path: Path) -> None:
    project = _project_with_lockfile(tmp_path)
    with pytest.raises(LockfileError):
        run_render(project, "@org/button", target="swiftui")


def test_run_render_missing_lockfile(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    (project / "speccify.lock").unlink()
    with pytest.raises(LockfileError):
        run_render(project, "@org/button")


def test_run_render_offline_cache_miss_raises(tmp_path: Path) -> None:
    project = _project_with_lockfile(tmp_path)
    empty_cache = tmp_path / "empty-cache"
    empty_cache.mkdir()
    with pytest.raises(CacheMissError):
        run_render(project, "@org/button", cache_dir=empty_cache)
