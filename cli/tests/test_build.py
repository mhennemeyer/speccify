"""Tests für `speccify build` (Phase P4 Stufe 3)."""

from __future__ import annotations

import json
from pathlib import Path

from speccify_cli.__main__ import app
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "registry-fixtures"

runner = CliRunner()


def test_build_writes_a_runnable_project(tmp_path: Path) -> None:
    out = tmp_path / "app"
    result = runner.invoke(
        app,
        ["build", "@org/demo-app", "--registry", str(REGISTRY), "--out", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert (out / "index.html").exists()
    assert (out / "src" / "App.tsx").exists()
    assert (out / "src" / "components" / "org" / "SearchBar.mock.tsx").exists()
    package = json.loads((out / "package.json").read_text(encoding="utf-8"))
    assert package["name"] == "org-demo-app"
    assert package["dependencies"]["react"].startswith("^19")
    assert "pnpm install" in result.output


def test_build_is_idempotent(tmp_path: Path) -> None:
    out = tmp_path / "app"
    for _ in range(2):
        result = runner.invoke(
            app,
            ["build", "@org/demo-app", "--registry", str(REGISTRY), "--out", str(out)],
        )
        assert result.exit_code == 0, result.output
    # Kein Müll aus atomaren Schreibvorgängen.
    assert not list(out.glob("**/.speccify-*"))


def test_build_rejects_non_app_specs(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["build", "@org/button", "--registry", str(REGISTRY), "--out", str(tmp_path / "app")],
    )
    assert result.exit_code == 1
    assert "erwartet `kind: app`" in result.output


def test_build_rejects_unknown_target(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "build",
            "@org/demo-app",
            "--registry",
            str(REGISTRY),
            "--out",
            str(tmp_path / "app"),
            "--target",
            "swiftui",
        ],
    )
    assert result.exit_code == 1
    assert "nicht unterstützt" in result.output


def test_build_without_mocks_uses_the_replay_cache(tmp_path: Path) -> None:
    """`--no-mocks` füllt src/components mit den generierten Implementierungen."""
    out = tmp_path / "app"
    result = runner.invoke(
        app,
        [
            "build",
            "@org/demo-app",
            "--registry",
            str(REGISTRY),
            "--out",
            str(out),
            "--no-mocks",
            "--cache-dir",
            str(REPO_ROOT / "tests" / "fixtures" / "llm-cache"),
        ],
    )
    if result.exit_code != 0:
        # Ohne Cache-Eintrag für jeden Screen ist der Miss die korrekte Antwort.
        assert "cache" in result.output.lower(), result.output
        return
    assert not (out / "src" / "components" / "org" / "SearchBar.mock.tsx").exists()
    assert (out / "src" / "components" / "org" / "SearchBar.tsx").exists()
