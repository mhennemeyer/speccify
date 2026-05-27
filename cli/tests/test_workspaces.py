"""CLI-Smoke-Tests für `speccify lock` mit Workspaces (Phase 3 Stage 5)."""

from __future__ import annotations

from pathlib import Path

from speccify_cli.__main__ import app
from speccify_core import Lockfile
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_WORKSPACE = REPO_ROOT / "example-workspace"

runner = CliRunner()


def test_lock_example_workspace_writes_root_lockfile(tmp_path: Path) -> None:
    # Kopiere das Example-Workspace in tmp, damit speccify.lock nicht im Repo landet.
    import shutil

    project = tmp_path / "ws"
    shutil.copytree(EXAMPLE_WORKSPACE, project)
    result = runner.invoke(
        app,
        [
            "lock",
            "--project",
            str(project),
            "--registry",
            str(REPO_ROOT / "registry-fixtures"),
        ],
    )
    assert result.exit_code == 0, result.output
    lockfile_path = project / "speccify.lock"
    assert lockfile_path.is_file()
    lockfile = Lockfile.load(lockfile_path)
    # Globale MVS → genau eine Version pro Spec-Id, x targets-Set (hier {react}).
    spec_ids = {e.id for e in lockfile.entries}
    assert spec_ids == {"@org/button", "@org/contact-form"}
    assert lockfile.targets == ("react",)
    assert len(lockfile.entries) == 2


def test_pull_example_workspace_materializes_per_member(tmp_path: Path) -> None:
    """Phase 4 Stage 3: `speccify pull` im Workspace-Root materialisiert pro Member."""
    import shutil

    project = tmp_path / "ws"
    shutil.copytree(EXAMPLE_WORKSPACE, project)
    # Erst Lock, dann Pull (beides workspace-aware).
    lock_result = runner.invoke(
        app,
        [
            "lock",
            "--project",
            str(project),
            "--registry",
            str(REPO_ROOT / "registry-fixtures"),
        ],
    )
    assert lock_result.exit_code == 0, lock_result.output

    pull_result = runner.invoke(
        app,
        [
            "pull",
            "--project",
            str(project),
            "--registry",
            str(REPO_ROOT / "registry-fixtures"),
        ],
    )
    assert pull_result.exit_code == 0, pull_result.output

    # `ui` hat nur @org/button → Button.tsx, kein ContactForm.tsx.
    ui_out = project / "packages" / "ui" / "speccify_generated" / "react"
    assert (ui_out / "org" / "Button.tsx").is_file()
    assert not (ui_out / "org" / "ContactForm.tsx").exists()

    # `forms` hat @org/button + @org/contact-form → beide Dateien.
    forms_out = project / "packages" / "forms" / "speccify_generated" / "react"
    assert (forms_out / "org" / "Button.tsx").is_file()
    assert (forms_out / "org" / "ContactForm.tsx").is_file()

    # Lockfile-Entries wurden mit generated_files_sha256 + LlmGeneratorPin angereichert.
    lockfile = Lockfile.load(project / "speccify.lock")
    assert all(e.generated_files_sha256 for e in lockfile.entries)


def test_pull_workspace_rejects_target_override(tmp_path: Path) -> None:
    """Im Workspace-Modus ist `--target` nicht zulässig (Members deklarieren Targets selbst)."""
    import shutil

    project = tmp_path / "ws"
    shutil.copytree(EXAMPLE_WORKSPACE, project)
    runner.invoke(
        app,
        ["lock", "--project", str(project), "--registry", str(REPO_ROOT / "registry-fixtures")],
    )
    result = runner.invoke(
        app,
        [
            "pull",
            "--project",
            str(project),
            "--target",
            "react",
            "--registry",
            str(REPO_ROOT / "registry-fixtures"),
        ],
    )
    assert result.exit_code == 1, result.output
    assert "Workspace" in result.output or "workspace" in result.output


def test_lock_workspace_conflicting_ranges_fails(tmp_path: Path) -> None:
    # Zwei Member fordern unvereinbare Caret-Ranges für dieselbe Spec → ResolverError.
    project = tmp_path / "ws"
    project.mkdir()
    (project / "speccify.yaml").write_text(
        "schema_version: 2\n"
        "workspaces:\n  - packages/*\n"
        f"registry:\n  path: {REPO_ROOT / 'registry-fixtures'}\n"
        "dependencies: {}\n",
        encoding="utf-8",
    )
    for name, dep_range in [("a", "^0.1"), ("b", "^0.2")]:
        member = project / "packages" / name
        member.mkdir(parents=True)
        (member / "speccify.yaml").write_text(
            "schema_version: 2\n"
            "targets:\n  - react\n"
            f"registry:\n  path: {REPO_ROOT / 'registry-fixtures'}\n"
            f'dependencies:\n  "@org/button": "{dep_range}"\n',
            encoding="utf-8",
        )
    result = runner.invoke(app, ["lock", "--project", str(project)])
    assert result.exit_code == 1, result.output
    assert "@org/button" in result.output
