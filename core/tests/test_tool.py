"""Tests for tool specs: `TOOL.md` parsing, validation and the `check` findings.

The spec replaces a shipped script with a contract. What these tests pin down
is that the contract is actually checkable: schemas must be valid, examples
must parse and must match the schemas — a lying example is worse than none,
because an agent on another machine would implement against it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core.skill_check import check_skill_directory, check_tools, load_tools
from speccify_core.tool import ToolError, parse_tool, validate_tool

GOOD = """---
name: verify-signatures
description: Checks every Mach-O in a bundle is signed; reports offenders.
inputs:
  type: object
  required: [bundle]
  properties:
    bundle: {type: string}
outputs:
  type: object
  required: [ok]
  properties:
    ok: {type: boolean}
    offenders: {type: array, items: {type: string}}
effects: reads the filesystem; runs codesign; writes nothing
requires: codesign
runtime: any
platforms: macos
---

## Behaviour

Walks the bundle.

## Examples

### signed bundle
input:  {"bundle": "fixtures/Signed.app"}
output: {"ok": true, "offenders": []}

### one unsigned helper
input: {"bundle": "fixtures/Broken.app"}
output: {"ok": false, "offenders": ["Contents/MacOS/helper"]}
"""


def _tool(text: str = GOOD):
    return parse_tool(text)


# --- Parsing ----------------------------------------------------------------------


def test_parses_frontmatter_and_examples() -> None:
    tool = _tool()
    assert tool.name == "verify-signatures"
    assert tool.requires == ("codesign",)
    assert tool.platforms == ("macos",)
    assert [e.title for e in tool.examples] == ["signed bundle", "one unsigned helper"]
    assert tool.examples[1].output == {"ok": False, "offenders": ["Contents/MacOS/helper"]}


def test_lists_accept_yaml_lists_and_comma_text() -> None:
    as_list = _tool(GOOD.replace("requires: codesign", "requires: [codesign, xcrun]"))
    as_text = _tool(GOOD.replace("requires: codesign", "requires: codesign, xcrun"))
    assert as_list.requires == as_text.requires == ("codesign", "xcrun")


def test_without_frontmatter_is_an_error() -> None:
    with pytest.raises(ToolError):
        parse_tool("# just a heading\n")


# --- Validation ---------------------------------------------------------------------


def test_good_spec_has_no_issues() -> None:
    assert validate_tool(_tool()) == []


def test_missing_schema_is_an_issue() -> None:
    text = GOOD.replace("outputs:\n  type: object\n  required: [ok]\n", "outputs_gone:\n")
    paths = [i.path for i in validate_tool(_tool(text))]
    assert "outputs" in paths


def test_invalid_json_schema_is_an_issue() -> None:
    text = GOOD.replace("bundle: {type: string}", "bundle: {type: strng}")
    issues = validate_tool(_tool(text))
    assert any(i.path == "inputs" and "not a valid JSON Schema" in i.message for i in issues)


def test_example_that_violates_the_schema_is_an_issue() -> None:
    """The example is the contract; a contract that contradicts the schema is broken."""
    text = GOOD.replace('output: {"ok": true, "offenders": []}', 'output: {"offenders": []}')
    issues = validate_tool(_tool(text))
    assert [i.path for i in issues] == ["$.examples[0].output"]
    assert "'ok' is a required property" in issues[0].message


def test_example_with_broken_json_is_reported_not_dropped() -> None:
    text = GOOD.replace('input:  {"bundle": "fixtures/Signed.app"}', "input: {bundle: nope}")
    issues = validate_tool(_tool(text))
    assert len(issues) == 1
    assert "not valid JSON" in issues[0].message


def test_example_missing_a_line_is_reported() -> None:
    text = GOOD.replace('output: {"ok": true, "offenders": []}\n', "")
    issues = validate_tool(_tool(text))
    assert [i.message for i in issues] == ["'signed bundle' has no `output:` line."]


# --- check ----------------------------------------------------------------------------


def _skill_with_tool(tmp_path: Path, tool_text: str, dir_name: str = "verify-signatures") -> Path:
    skill = tmp_path / "a-skill"
    (skill / "tools" / dir_name).mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: a-skill\ndescription: Does a thing. Use when a thing needs doing.\n---\n",
        encoding="utf-8",
    )
    (skill / "tools" / dir_name / "TOOL.md").write_text(tool_text, encoding="utf-8")
    return skill


def test_check_finds_tools_in_a_skill_directory(tmp_path: Path) -> None:
    skill = _skill_with_tool(tmp_path, GOOD)
    assert list(load_tools(skill)) == ["verify-signatures"]
    assert check_skill_directory(skill) == []


def test_tool_without_examples_is_a_warning(tmp_path: Path) -> None:
    skill = _skill_with_tool(tmp_path, GOOD.split("## Examples")[0])
    findings = check_skill_directory(skill)
    assert [(f.level, f.path) for f in findings] == [("warning", "tools/verify-signatures/$")]


def test_tool_without_effects_is_a_warning() -> None:
    tool = _tool(GOOD.replace("effects: reads the filesystem; runs codesign; writes nothing\n", ""))
    findings = check_tools({"verify-signatures": tool})
    assert [f.path for f in findings] == ["tools/verify-signatures/effects"]


def test_tool_directory_must_match_name(tmp_path: Path) -> None:
    skill = _skill_with_tool(tmp_path, GOOD, dir_name="verify")
    findings = check_skill_directory(skill)
    assert [f.level for f in findings] == ["error"]
    assert "directory is 'verify'" in findings[0].message


def test_unparseable_tool_is_an_error_at_its_path(tmp_path: Path) -> None:
    skill = _skill_with_tool(tmp_path, "no frontmatter here\n")
    findings = check_skill_directory(skill)
    assert [(f.level, f.path) for f in findings] == [("error", "tools/verify-signatures")]


def test_shipped_script_without_a_spec_is_a_warning(tmp_path: Path) -> None:
    """A script is what does not travel; the warning points at the fix."""
    skill = _skill_with_tool(tmp_path, GOOD)
    (skill / "assets").mkdir()
    (skill / "assets" / "verify-signatures.sh").write_text("#!/bin/sh\n")  # has a spec
    (skill / "assets" / "build.sh").write_text("#!/bin/sh\n")  # has none
    (skill / "assets" / "notes.md").write_text("# not a script\n")
    findings = check_skill_directory(skill)
    assert [(f.level, f.path) for f in findings] == [("warning", "assets/build.sh")]
    assert "tools/build/TOOL.md" in findings[0].message
