from __future__ import annotations

from pathlib import Path

from speccify_cli.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()

VALID = "id: spec://x\nversion: 1.0.0\nkind: ui-component\ntitle: X\nsummary: y\n"

INVALID = "id: NOT_VALID\nversion: 1.0\nkind: ui-component\ntitle: X\nsummary: y\n"


def test_lint_passes_for_valid_spec(tmp_path: Path) -> None:
    p = tmp_path / "ok.yaml"
    p.write_text(VALID, encoding="utf-8")
    result = runner.invoke(app, ["lint", str(p)])
    assert result.exit_code == 0, result.output
    assert "✓" in result.output


def test_lint_fails_for_invalid_spec(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(INVALID, encoding="utf-8")
    result = runner.invoke(app, ["lint", str(p)])
    assert result.exit_code == 1, result.output
    assert "✗" in result.output
