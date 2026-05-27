"""Unit-Tests für die Phase-1c-Step-3-Tools (`lock`, `pull`, `verify`).

Wir testen die reinen Adapter-Funktionen (`run_lock`/`run_pull`/
`run_verify`) direkt — gleiche Strategie wie `test_tools_readonly.py`.
Zusätzlich enthält dieses File einen Cross-Consistency-Test, der die
CLI-`run_pull` und die MCP-`run_pull` gegen dieselbe Projektkopie
fährt und beide Output-Bytes + Lockfile-Inhalte vergleicht.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from speccify_cli.commands.pull import run_pull as cli_run_pull
from speccify_core import CacheMissError, Lockfile, LockfileError
from speccify_mcp.tools import run_lock, run_pull, run_verify

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PROJECT = REPO_ROOT / "example-project"
EXAMPLE_WORKSPACE = REPO_ROOT / "example-workspace"
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"


def _copy_example_project(target: Path) -> Path:
    """Kopiert `example-project/` + `registry-fixtures/` nach `target`."""
    shutil.copytree(REGISTRY_FIXTURES, target / "registry-fixtures")
    dst = target / "example-project"
    shutil.copytree(EXAMPLE_PROJECT, dst)
    out_dir = dst / "out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    return dst


# -------------------------------------------------------------------- lock


def test_run_lock_writes_lockfile(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    lockfile_path = project / "speccify.lock"
    lockfile_path.unlink()  # neu erzeugen

    result = run_lock(project)
    payload = result.to_dict()

    assert payload["target"] == "react"
    assert lockfile_path.is_file()
    assert Path(payload["lockfile_path"]) == lockfile_path
    ids = sorted(e["spec_id"] for e in payload["entries"])
    assert "@org/button" in ids
    for e in payload["entries"]:
        assert e["spec_sha256"].startswith("sha256:")


def test_run_lock_missing_manifest(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_lock(tmp_path)


# -------------------------------------------------------------------- pull


def test_run_pull_writes_files_and_updates_lockfile(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    out_dir = project / "out"

    result = run_pull(project, out_dir)
    payload = result.to_dict()

    assert payload["target"] == "react"
    assert payload["files_written"], "es muss mindestens eine Datei geschrieben werden"
    for rel_path in payload["files_written"]:
        assert (out_dir / rel_path).is_file()
        assert rel_path.endswith(".tsx")

    # Lockfile enthält jetzt generated_files_sha256 + LLM-Pin pro Eintrag.
    lockfile = Lockfile.load(project / "speccify.lock")
    for entry in lockfile.entries:
        assert entry.generated_files_sha256, f"Eintrag {entry.id} hat keine Dateien"
        for f in entry.generated_files_sha256:
            assert f.sha256.startswith("sha256:")


def test_run_pull_missing_lockfile(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    (project / "speccify.lock").unlink()
    with pytest.raises(LockfileError):
        run_pull(project, project / "out")


def test_run_pull_target_mismatch(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    with pytest.raises(LockfileError):
        run_pull(project, project / "out", target="swiftui")


def test_run_pull_offline_cache_miss(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    empty_cache = tmp_path / "empty-cache"
    empty_cache.mkdir()
    with pytest.raises(CacheMissError):
        run_pull(project, project / "out", cache_dir=empty_cache)


# ------------------------------------------------------------------ verify


def test_run_verify_green_after_pull(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    out_dir = project / "out"
    run_pull(project, out_dir)

    result = run_verify(project, out_dir)
    payload = result.to_dict()
    assert payload["ok"] is True, payload["problems"]
    assert payload["problems"] == []


def test_run_verify_detects_disk_drift(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    out_dir = project / "out"
    run_pull(project, out_dir)

    # eine erzeugte Datei manipulieren
    tsx_files = sorted(out_dir.rglob("*.tsx"))
    assert tsx_files, "pull sollte TSX-Dateien erzeugt haben"
    tsx_files[0].write_text("// tampered\n", encoding="utf-8")

    result = run_verify(project, out_dir)
    payload = result.to_dict()
    assert payload["ok"] is False
    assert any("Disk-Drift" in p for p in payload["problems"]), payload["problems"]


def test_run_verify_missing_lockfile_reports_problem(tmp_path: Path) -> None:
    project = _copy_example_project(tmp_path)
    (project / "speccify.lock").unlink()
    result = run_verify(project, project / "out")
    payload = result.to_dict()
    assert payload["ok"] is False
    assert any("Kein Lockfile" in p for p in payload["problems"])


# -------------------------------------------------- cross-consistency CLI ↔ MCP


def test_cli_and_mcp_pull_produce_identical_output(tmp_path: Path) -> None:
    """Cross-Consistency: CLI-`run_pull` und MCP-`run_pull` müssen
    byte-identische Output-Dateien + Lockfile produzieren. Sicherheitsnetz
    gegen Drift zwischen den beiden Aufrufpfaden (vgl. Phase-1c-Plan,
    Decision 4: Tools spiegeln CLI 1:1)."""
    cli_project = _copy_example_project(tmp_path / "cli")
    mcp_project = _copy_example_project(tmp_path / "mcp")
    cli_out = cli_project / "out"
    mcp_out = mcp_project / "out"

    cli_run_pull(cli_project, cli_out)
    run_pull(mcp_project, mcp_out)

    cli_files = {
        p.relative_to(cli_out).as_posix(): p.read_bytes()
        for p in sorted(cli_out.rglob("*"))
        if p.is_file()
    }
    mcp_files = {
        p.relative_to(mcp_out).as_posix(): p.read_bytes()
        for p in sorted(mcp_out.rglob("*"))
        if p.is_file()
    }
    assert cli_files.keys() == mcp_files.keys(), (
        f"Dateilisten unterschiedlich: CLI={sorted(cli_files)}, MCP={sorted(mcp_files)}"
    )
    for rel_path in cli_files:
        assert cli_files[rel_path] == mcp_files[rel_path], (
            f"Inhalt von {rel_path} weicht zwischen CLI und MCP ab"
        )

    # Lockfile-Inhalt muss ebenfalls byte-identisch sein
    # (deterministischer YAML-Dump im Core).
    cli_lock = (cli_project / "speccify.lock").read_bytes()
    mcp_lock = (mcp_project / "speccify.lock").read_bytes()
    assert cli_lock == mcp_lock


# -------------------------------------------------- Phase 4: Workspace-Mode


def test_mcp_workspace_lock_pull_verify_smoke(tmp_path: Path) -> None:
    """Phase 4 Stage 6: MCP-Tools mit `workspace_root=...` durchlaufen lock+pull+verify.

    `project_root` zeigt aus historischen Gründen auf einen Dummy-Pfad — der
    Workspace-Pfad wird allein durch `workspace_root` aktiviert.
    """
    project = tmp_path / "ws"
    shutil.copytree(EXAMPLE_WORKSPACE, project)
    dummy = tmp_path / "irrelevant"
    dummy.mkdir()

    # 1) lock
    lock_result = run_lock(
        project_root=dummy,
        registry_path=REGISTRY_FIXTURES,
        workspace_root=project,
    )
    assert lock_result.workspace is True
    assert lock_result.targets == ("react",)
    spec_ids = {e["spec_id"] for e in lock_result.entries}
    assert spec_ids == {"@org/button", "@org/contact-form"}

    # 2) pull
    pull_result = run_pull(
        project_root=dummy,
        out_dir=tmp_path / "unused",
        registry_path=REGISTRY_FIXTURES,
        workspace_root=project,
    )
    assert pull_result.workspace is True
    # ui hat nur Button, forms hat beide → ContactForm taucht nur einmal in der Union auf
    assert "org/Button.tsx" in pull_result.files_written
    assert "org/ContactForm.tsx" in pull_result.files_written

    # Outputs landen pro Member unter `<member>/speccify_generated/<target>/`.
    assert (
        project / "packages" / "ui" / "speccify_generated" / "react" / "org" / "Button.tsx"
    ).is_file()
    assert (
        project / "packages" / "forms" / "speccify_generated" / "react" / "org" / "ContactForm.tsx"
    ).is_file()

    # 3) verify
    verify_result = run_verify(
        project_root=dummy,
        out_dir=tmp_path / "unused",
        registry_path=REGISTRY_FIXTURES,
        workspace_root=project,
    )
    assert verify_result.workspace is True
    assert verify_result.ok is True, verify_result.problems
    assert verify_result.problems == []


def test_mcp_workspace_pull_rejects_target_arg(tmp_path: Path) -> None:
    """Im Workspace-Modus ist `target` nicht zulässig."""
    project = tmp_path / "ws"
    shutil.copytree(EXAMPLE_WORKSPACE, project)
    dummy = tmp_path / "irrelevant"
    dummy.mkdir()

    run_lock(project_root=dummy, registry_path=REGISTRY_FIXTURES, workspace_root=project)
    with pytest.raises(LockfileError, match="Workspace-Modus"):
        run_pull(
            project_root=dummy,
            out_dir=tmp_path / "unused",
            target="react",
            registry_path=REGISTRY_FIXTURES,
            workspace_root=project,
        )
