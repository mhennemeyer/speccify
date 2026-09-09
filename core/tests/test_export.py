"""Tests for `generalise_skill`: a project skill becomes a library bundle again.

Pinned here: the project section goes, tool links point into the bundle, the
skill gets an id, implementations become a reference, and the suspects report
finds what a reader must generalise by hand.
"""

from __future__ import annotations

import yaml
from speccify_core.export import (
    find_suspects,
    generalise_skill,
    referenced_tools,
    strip_project_section,
)
from speccify_core.skill import parse_skill

PROJECT_SKILL = """---
name: notarize
description: Notarizes a bundle. Use when shipping a .dmg.
license: MIT
metadata:
  author: someone
---

## 1 — Sign

Sign `<path to .app>` with your identity, then run
[verify](../../tools/verify/TOOL.md) on /Users/me/Work/App/build/App.app.
Bundle id com.acme.app, upload via https://gitlab.acme.internal/ci.

## Sources

- [Apple](https://developer.apple.com/notarization) — retrieved 2026-08-01

## In this project

- Team id: ABCDE12345, contact me@acme.example.
- Tool [verify](../../tools/verify/TOOL.md) — implemented for this platform.
"""

TOOLS = {
    "verify": {
        "TOOL.md": b"---\nname: verify\n---\n\n## Examples\n",
        "macos.sh": b'#!/bin/sh\nspctl -a "$1"\n',
        "windows.ps1": b"Write-Output ok\n",
        "fixtures/Signed.app": b"",
    }
}


def test_referenced_tools_reads_links_into_the_project_tools() -> None:
    assert referenced_tools(PROJECT_SKILL) == ("verify",)


def test_strip_project_section_keeps_only_the_upstream_part() -> None:
    body = parse_skill(PROJECT_SKILL).body
    stripped = strip_project_section(body)
    assert "## In this project" not in stripped
    assert "## Sources" in stripped
    assert strip_project_section("## In this project\n\n- only this\n") == ""
    assert strip_project_section("## Only upstream\n") == "## Only upstream\n"


def test_generalise_sets_id_drops_section_and_rewrites_links() -> None:
    exported = generalise_skill(
        PROJECT_SKILL, version="1.0.0", scope="acme", tools=TOOLS, platform="macos"
    )
    text = exported.files["SKILL.md"].decode()
    front = yaml.safe_load(text.split("---\n")[1])
    assert front["name"] == "notarize"
    assert front["license"] == "MIT"
    assert front["metadata"] == {
        "speccify.version": "1.0.0",
        "speccify.scope": "acme",
        "author": "someone",
    }
    assert "## In this project" not in text
    assert "Team id" not in text
    assert "[verify](tools/verify/TOOL.md)" in text
    assert "../../tools" not in text
    # The result is a valid library skill with an addressable id.
    skill = parse_skill(text)
    assert skill.qualified_id == "@acme/notarize"
    assert skill.version == "1.0.0"
    assert exported.placeholders == ("<path to .app>",)


def test_generalise_ships_contracts_and_one_reference_only() -> None:
    exported = generalise_skill(
        PROJECT_SKILL, version="1.0.0", scope="acme", tools=TOOLS, platform="macos"
    )
    assert exported.tools == ("verify",)
    assert set(exported.files) == {
        "SKILL.md",
        "tools/verify/TOOL.md",
        "tools/verify/reference.sh",
        "tools/verify/fixtures/Signed.app",
    }
    assert exported.files["tools/verify/reference.sh"] == TOOLS["verify"]["macos.sh"]

    # Another platform's implementation is the reference when asked for.
    windows = generalise_skill(
        PROJECT_SKILL, version="1.0.0", scope="acme", tools=TOOLS, platform="windows"
    )
    assert "tools/verify/reference.ps1" in windows.files
    assert "tools/verify/reference.sh" not in windows.files

    # A reference that came with the skill is kept, implementations stay home.
    with_reference = {"verify": {**TOOLS["verify"], "reference.rb": b"puts 1\n"}}
    kept = generalise_skill(
        PROJECT_SKILL, version="1.0.0", scope="acme", tools=with_reference, platform="macos"
    )
    assert "tools/verify/reference.rb" in kept.files
    assert "tools/verify/reference.sh" not in kept.files


def test_generalise_records_uses_as_comma_separated_metadata() -> None:
    exported = generalise_skill(
        PROJECT_SKILL,
        version="2.1.0",
        scope=None,
        tools={},
        uses=("@acme/sign-cert@^1.0", "@acme/keychain@^2.0"),
    )
    front = yaml.safe_load(exported.files["SKILL.md"].decode().split("---\n")[1])
    assert front["metadata"]["speccify.uses"] == "@acme/sign-cert@^1.0, @acme/keychain@^2.0"
    assert "speccify.scope" not in front["metadata"]


def test_suspects_point_at_paths_ids_private_hosts_and_secrets() -> None:
    exported = generalise_skill(
        PROJECT_SKILL, version="1.0.0", scope="acme", tools=TOOLS, platform="macos"
    )
    kinds = {(s.kind, s.text) for s in exported.suspects}
    assert ("path", "/Users/me/Work/App/build/App.app") in kinds
    assert ("bundle-id", "com.acme.app") in kinds
    assert ("host", "https://gitlab.acme.internal/ci") in kinds
    # Public documentation links are not suspects; the project section is gone.
    assert not any("developer.apple.com" in s.text for s in exported.suspects)
    assert not any("ABCDE12345" in s.text for s in exported.suspects)
    assert all(s.file == "SKILL.md" for s in exported.suspects)
    first = exported.suspects[0]
    assert first.format().startswith("SKILL.md:")

    secrets = find_suspects(
        {"tools/x/reference.sh": b"export API_KEY=abc123\nurl=http://localhost:8765/mcp\n"}
    )
    assert {(s.kind, s.line) for s in secrets} == {("secret", 1), ("host", 2)}
    # Binary or unknown files are skipped, placeholders are not suspects.
    assert find_suspects({"tools/x/fixtures/App.app": b"/Users/me/"}) == ()
    assert find_suspects({"SKILL.md": b"Copy it to ~/<vendor-dir>/bin.\n"}) == ()
