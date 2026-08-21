"""Tests for `expand_skill`: a source skill becomes a normal project skill.

What is pinned here is the contract that makes re-expansion cheap: upstream
text is replaced, the `## In this project` section is kept, and nothing
Speccify-specific survives in the result.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from speccify_core.expansion import (
    PROJECT_HEADING,
    Expansions,
    SkillRecord,
    ToolRecord,
    expand_skill,
    find_placeholders,
    implementation_for,
)
from speccify_core.skill import parse_skill

SOURCE = """---
name: notarize
description: Notarizes a bundle. Use when shipping a .dmg.
license: MIT
metadata:
  speccify.version: 1.2.0
  speccify.scope: speccify
  speccify.uses: '@speccify/sign-cert@^1.0'
  author: someone
---

## 1 — Sign

Sign `<path to .app>` with your identity. See [verify](tools/verify/TOOL.md).

## Sources

- [Apple](https://example.com) — retrieved 2026-08-01
"""

FILES = {
    "SKILL.md": SOURCE.encode(),
    "tools/verify/TOOL.md": b"---\nname: verify\n---\n",
    "tools/verify/reference.sh": b"#!/bin/sh\n",
    "assets/x.swift": b"// swift\n",
}


def _expand(existing: str | None = None):
    return expand_skill(
        parse_skill(SOURCE),
        FILES,
        sibling_names={"@speccify/sign-cert@^1.0": "sign-cert"},
        existing_markdown=existing,
    )


def test_speccify_metadata_is_stripped_but_the_rest_survives() -> None:
    front = yaml.safe_load(_expand().skill_markdown.split("---")[1])
    assert front["name"] == "notarize"
    assert front["license"] == "MIT"
    assert front["metadata"] == {"author": "someone"}
    assert not any(k.startswith("speccify.") for k in front["metadata"])


def test_tool_links_move_up_to_the_project_tools_directory() -> None:
    markdown = _expand().skill_markdown
    assert "](../../tools/verify/TOOL.md)" in markdown
    assert "](tools/" not in markdown


def test_uses_becomes_a_relative_link_to_the_sibling_skill() -> None:
    markdown = _expand().skill_markdown
    assert "[sign-cert](../sign-cert/SKILL.md)" in markdown
    assert markdown.count(PROJECT_HEADING) == 1


def test_tools_are_split_off_and_named() -> None:
    expanded = _expand()
    assert expanded.tool_names == ("verify",)
    assert set(expanded.tool_files) == {"tools/verify/TOOL.md", "tools/verify/reference.sh"}


def test_placeholders_are_reported() -> None:
    assert _expand().placeholders == ("<path to .app>",)
    assert find_placeholders("use <br> and <https://x> and YOUR_TEAM_ID") == ["YOUR_TEAM_ID"]


def test_re_expansion_keeps_the_project_section_and_replaces_upstream() -> None:
    """The whole reason the project part is appended, never merged."""
    first = _expand().skill_markdown
    edited = first.replace("- Builds on", "- Bundle id: com.example.app\n- Builds on")
    assert "com.example.app" in edited

    again = _expand(existing=edited).skill_markdown
    assert "com.example.app" in again
    assert again.count(PROJECT_HEADING) == 1
    # Upstream part is regenerated from source, not copied from the old file.
    assert again.split(PROJECT_HEADING)[0] == first.split(PROJECT_HEADING)[0]


def test_expansions_round_trip(tmp_path: Path) -> None:
    record = Expansions(
        skills={
            "notarize": SkillRecord(
                source="@speccify/notarize",
                version="1.2.0",
                bundle_sha256="sha256:abc",
                expanded="2026-08-21",
                requested=True,
                tools=("verify",),
            )
        },
        tools={
            "verify": ToolRecord(
                from_skills=("notarize",),
                spec_sha256="def",
                platforms={"macos": {"status": "implemented", "file": "macos.sh"}},
            )
        },
    )
    path = tmp_path / "expansions.yaml"
    record.write(path)
    loaded = Expansions.load(path)
    assert loaded == record
    assert loaded.tools["verify"].status("macos") == "implemented"
    assert loaded.tools["verify"].status("windows") == "specified"


def test_implementation_is_found_by_platform_stem(tmp_path: Path) -> None:
    (tmp_path / "macos.sh").write_text("#!/bin/sh\n")
    (tmp_path / "TOOL.md").write_text("---\n---\n")
    (tmp_path / "reference.sh").write_text("#!/bin/sh\n")
    assert implementation_for(tmp_path, "macos") == tmp_path / "macos.sh"
    assert implementation_for(tmp_path, "windows") is None
