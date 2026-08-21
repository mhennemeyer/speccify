"""Tests for the conformance runner: examples in, implementation out, verdict.

The runner is the mechanical half of Evaluate. What matters is that it is
honest in both directions — a correct implementation in any language passes,
and every way an implementation can fall short (wrong value, missing key,
no JSON, crash, timeout, schema violation) is named, not hidden.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from speccify_core.tool_check import (
    FAILED,
    MISSING_REQUIREMENT,
    NO_EXAMPLES,
    NOT_APPLICABLE,
    NOT_IMPLEMENTED,
    PASSED,
    check_tool,
    differences,
)

SPEC = """---
name: add
description: Adds two numbers and says whether the sum is positive.
inputs:
  type: object
  required: [a, b]
  properties:
    a: {type: number}
    b: {type: number}
outputs:
  type: object
  required: [ok, sum]
  properties:
    ok: {type: boolean}
    sum: {type: number}
    note: {type: string}
effects: none
{extra}---

## Examples

### two positives
input: {"a": 1, "b": 2}
output: {"ok": true, "sum": 3}

### a negative sum
input: {"a": 1, "b": -5}
output: {"ok": false, "sum": -4}
"""

CORRECT = """import json, sys
data = json.load(sys.stdin)
total = data["a"] + data["b"]
print(json.dumps({"ok": total > 0, "sum": total, "note": "extra fields are fine"}))
sys.exit(0 if total > 0 else 2)
"""


def _tool(tmp_path: Path, implementation: str | None = CORRECT, *, extra: str = "") -> Path:
    tool_dir = tmp_path / "add"
    tool_dir.mkdir()
    (tool_dir / "TOOL.md").write_text(SPEC.replace("{extra}", extra), encoding="utf-8")
    if implementation is not None:
        (tool_dir / "linux.py").write_text(implementation, encoding="utf-8")
    return tool_dir


def test_a_correct_implementation_is_verified(tmp_path: Path) -> None:
    result = check_tool(_tool(tmp_path), platform="linux")
    assert result.status == PASSED, [c.to_dict() for c in result.cases]
    assert result.verified
    assert result.implementation == "linux.py"
    assert [c.title for c in result.cases] == ["two positives", "a negative sum"]


def test_extra_output_fields_are_tolerated_missing_ones_are_not(tmp_path: Path) -> None:
    assert differences({"ok": True}, {"ok": True, "more": 1}) == []
    assert differences({"ok": True, "sum": 3}, {"ok": True}) == ["$.sum: missing"]
    assert differences([1, 2], [1]) == ["$: expected 2 item(s), got 1"]
    assert differences({"a": [{"x": 1}]}, {"a": [{"x": 2}]}) == ["$.a[0].x: expected 1, got 2"]
    # JSON booleans are not numbers, even though Python thinks so.
    assert differences(True, 1) == ["$: expected true, got 1"]


def test_a_wrong_value_names_the_path(tmp_path: Path) -> None:
    wrong = CORRECT.replace('total = data["a"] + data["b"]', 'total = data["a"] - data["b"]')
    result = check_tool(_tool(tmp_path, wrong), platform="linux")
    assert result.status == FAILED
    failed = [c for c in result.cases if not c.passed]
    assert [c.title for c in failed] == ["two positives", "a negative sum"]
    assert "$.sum: expected 3, got -1" in failed[0].detail
    assert failed[0].actual["sum"] == -1
    # 1 - (-5) = 6: the sum is wrong *and* so is `ok` — both are named.
    assert "$.ok: expected false, got true" in failed[1].detail
    assert "$.sum: expected -4, got 6" in failed[1].detail


def test_ok_true_requires_exit_zero(tmp_path: Path) -> None:
    always_one = CORRECT.replace("sys.exit(0 if total > 0 else 2)", "sys.exit(1)")
    result = check_tool(_tool(tmp_path, always_one), platform="linux")
    assert result.status == FAILED
    by_title = {c.title: c for c in result.cases}
    assert "exit code is 1, expected 0" in by_title["two positives"].detail
    # An `ok: false` example does not care how the tool signalled it.
    assert by_title["a negative sum"].passed


def test_output_must_satisfy_the_outputs_schema(tmp_path: Path) -> None:
    stringly = CORRECT.replace('"sum": total', '"sum": str(total)')
    result = check_tool(_tool(tmp_path, stringly), platform="linux")
    assert result.status == FAILED
    assert "outputs schema at $.sum" in result.cases[0].detail


def test_a_crash_reports_stderr(tmp_path: Path) -> None:
    crash = "import sys\nsys.stderr.write('boom: no such bundle\\n')\nsys.exit(3)\n"
    result = check_tool(_tool(tmp_path, crash), platform="linux")
    assert result.status == FAILED
    assert result.cases[0].detail == "no output on stdout (exit 3): boom: no such bundle"
    assert result.cases[0].exit_code == 3


def test_non_json_output_is_a_failure(tmp_path: Path) -> None:
    result = check_tool(_tool(tmp_path, "print('three')\n"), platform="linux")
    assert result.status == FAILED
    assert "stdout is not JSON" in result.cases[0].detail


def test_a_timeout_is_a_failure_not_a_hang(tmp_path: Path) -> None:
    result = check_tool(
        _tool(tmp_path, "import time\ntime.sleep(5)\n"), platform="linux", timeout=0.5
    )
    assert result.status == FAILED
    assert all("timed out after 0.5s" in c.detail for c in result.cases)


def test_examples_run_with_the_tool_dir_as_cwd(tmp_path: Path) -> None:
    reads_fixture = (
        "import json, sys, pathlib\n"
        "data = json.load(sys.stdin)\n"
        "total = int(pathlib.Path('fixtures/offset').read_text()) + data['a'] + data['b']\n"
        "print(json.dumps({'ok': total > 0, 'sum': total}))\n"
    )
    tool_dir = _tool(tmp_path, reads_fixture)
    (tool_dir / "fixtures").mkdir()
    (tool_dir / "fixtures" / "offset").write_text("0")
    assert check_tool(tool_dir, platform="linux").status == PASSED


def test_without_an_implementation_nothing_runs(tmp_path: Path) -> None:
    result = check_tool(_tool(tmp_path, None), platform="linux")
    assert result.status == NOT_IMPLEMENTED
    assert not result.verified
    assert "linux.<ext>" in result.detail


def test_a_spec_for_another_platform_is_not_applicable(tmp_path: Path) -> None:
    result = check_tool(_tool(tmp_path, extra="platforms: windows\n"), platform="linux")
    assert result.status == NOT_APPLICABLE


def test_a_missing_requirement_is_named_before_anything_runs(tmp_path: Path) -> None:
    result = check_tool(
        _tool(tmp_path, extra="requires: [definitely-not-a-binary-on-this-machine]\n"),
        platform="linux",
    )
    assert result.status == MISSING_REQUIREMENT
    assert "definitely-not-a-binary-on-this-machine" in result.detail


def test_no_examples_means_nothing_to_verify(tmp_path: Path) -> None:
    tool_dir = _tool(tmp_path)
    spec = (tool_dir / "TOOL.md").read_text()
    (tool_dir / "TOOL.md").write_text(spec.split("## Examples")[0])
    result = check_tool(tool_dir, platform="linux")
    assert result.status == NO_EXAMPLES
    assert not result.verified


@pytest.mark.skipif(sys.platform.startswith("win"), reason="shell scripts")
def test_an_executable_runs_directly_whatever_its_language(tmp_path: Path) -> None:
    tool_dir = _tool(tmp_path, None)
    script = tool_dir / "linux.sh"
    script.write_text(
        "#!/bin/sh\n"
        "read -r line\n"
        "a=$(printf '%s' \"$line\" | sed -E 's/.*\"a\": *(-?[0-9]+).*/\\1/')\n"
        "b=$(printf '%s' \"$line\" | sed -E 's/.*\"b\": *(-?[0-9]+).*/\\1/')\n"
        "sum=$((a + b))\n"
        'if [ "$sum" -gt 0 ]; then ok=true; code=0; else ok=false; code=1; fi\n'
        'printf \'{"ok": %s, "sum": %s}\\n\' "$ok" "$sum"\n'
        "exit $code\n"
    )
    script.chmod(0o755)
    result = check_tool(tool_dir, platform="linux")
    assert result.status == PASSED, [c.to_dict() for c in result.cases]
