"""Tests für `scripts/gen_cli_docs.py` (Phase 6, Stage 3)."""

from __future__ import annotations

import gen_cli_docs as gen


def test_collect_commands_contains_core_subcommands() -> None:
    commands = gen._collect_commands()
    for name in ("lint", "lock", "pull", "verify", "add", "init", "tool check"):
        assert name in commands
    assert "tool" not in commands  # Gruppen erscheinen nur über ihre Unterbefehle


def test_render_command_mdx_is_deterministic() -> None:
    commands = gen._collect_commands()
    first = gen.render_command_mdx("lint", commands["lint"])
    second = gen.render_command_mdx("lint", commands["lint"])
    assert first == second


def test_render_command_mdx_structure() -> None:
    commands = gen._collect_commands()
    rendered = gen.render_command_mdx("show", commands["show"])

    assert 'title: "speccify show"' in rendered
    assert gen._GENERATED_BANNER in rendered
    assert "## Usage" in rendered
    assert "speccify show [OPTIONS] REFERENCE" in rendered
    assert "## Arguments" in rendered
    assert "## Options" in rendered


def test_render_index_lists_all_commands() -> None:
    commands = gen._collect_commands()
    index = gen.render_index_mdx(commands)
    for name in commands:
        assert f"](/cli/{gen._slug(name)}/)" in index


def test_check_is_green_after_write() -> None:
    assert gen.run_gen(check=False) == 0
    assert gen.run_gen(check=True) == 0


def test_check_detects_drift_and_write_heals() -> None:
    dest = gen._CLI_DOCS_DIR / "lint.md"
    original = dest.read_text(encoding="utf-8")
    try:
        dest.write_text(original + "\nDRIFT\n", encoding="utf-8")
        assert gen.run_gen(check=True) == 1
        assert gen.run_gen(check=False) == 0
        assert gen.run_gen(check=True) == 0
    finally:
        gen.run_gen(check=False)
