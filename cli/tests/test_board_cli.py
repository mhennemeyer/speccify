"""`speccify board` writes a self-contained page from a specs folder."""

from __future__ import annotations

from pathlib import Path

from speccify_cli.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_board_renders_specs_folder(tmp_path: Path) -> None:
    specs = tmp_path / ".agent" / "specs" / "007-demo"
    specs.mkdir(parents=True)
    (specs / "SPEC.md").write_text(
        "---\nstation: Doing\norder: 1\n---\n# Demo\n\n- [x] a\n- [ ] b\n", encoding="utf-8"
    )
    out = tmp_path / "site" / "board" / "index.html"
    result = runner.invoke(
        app,
        [
            "board",
            "--project",
            str(tmp_path),
            "--out",
            str(out),
            "--title",
            "Team",
            "--source",
            "specs@abc",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "1 specs, 1/2 tasks" in result.output
    page = out.read_text(encoding="utf-8")
    assert "Team · Team-Board" in page and "Quelle: specs@abc" in page and "Demo" in page


def test_board_fails_without_specs_folder(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["board", "--project", str(tmp_path), "--out", str(tmp_path / "b.html")]
    )
    assert result.exit_code == 1
