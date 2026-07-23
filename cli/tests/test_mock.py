"""Tests für `speccify mock` (P2 Stage 3)."""

from __future__ import annotations

from pathlib import Path

from speccify_cli.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"


def test_mock_writes_closure_files(tmp_path: Path) -> None:
    out = tmp_path / "mocks"
    result = runner.invoke(
        app,
        ["mock", "@org/search-bar", "--registry", str(FIXTURES), "--out", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert (out / "org" / "SearchBar.mock.tsx").is_file()
    assert (out / "org" / "TextInput.mock.tsx").is_file()
    assert (out / "org" / "Button.mock.tsx").is_file()
    assert "3 Mock-Datei(en)" in result.output


def test_mock_resolves_latest_version_by_default(tmp_path: Path) -> None:
    out = tmp_path / "mocks"
    result = runner.invoke(
        app,
        ["mock", "@org/button", "--registry", str(FIXTURES), "--out", str(out)],
    )
    assert result.exit_code == 0, result.output
    source = (out / "org" / "Button.mock.tsx").read_text(encoding="utf-8")
    # Neueste Button-Version ist 0.1.1.
    assert "@org/button@0.1.1" in source


def test_mock_rejects_invalid_ref(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["mock", "not-a-ref", "--registry", str(FIXTURES), "--out", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "Ungültige Spec-Referenz" in result.output


def test_mock_rejects_unknown_target(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "mock",
            "@org/button",
            "--registry",
            str(FIXTURES),
            "--out",
            str(tmp_path),
            "--target",
            "swiftui",
        ],
    )
    assert result.exit_code == 1
    assert "nur 'react'" in result.output
