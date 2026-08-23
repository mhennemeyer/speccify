"""Conformance: run a tool spec's examples against the implementation for this platform.

The contract of a tool is its `## Examples` (D10). The calling convention is
the one thing Speccify prescribes (D7): an executable that reads one JSON
value on stdin, writes one JSON value on stdout, and exits 0 when it did its
job. This module feeds each example's `input` to `<platform>.<ext>` and
compares what comes back with the example's `output`. Green or red, no
judgement — the judgement (the *fachliche* layer of Evaluate) is the agent's.

What counts as a pass, per example:

* stdout parses as JSON;
* the parsed value **covers** the expected one — every key the example names
  is present with the same value, recursively; keys the example does not name
  are allowed (an implementation may report more than the contract demands,
  never less); lists must match in length and element-wise;
* the parsed value validates against the spec's `outputs` schema;
* when the expected output says `ok: true`, the exit code is 0. When it says
  `ok: false` the exit code is not inspected: both readings of D7 — "0 means
  it ran" and "0 means ok" — are accepted, because both are honest.

A non-zero exit with no JSON on stdout is a crash; stderr becomes the detail.

Examples are run with the tool directory as working directory, so relative
paths such as `fixtures/Signed.app` resolve next to the implementation.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from speccify_core.expansion import current_platform, implementation_for
from speccify_core.tool import TOOL_FILENAME, Example, Tool, ToolError, parse_tool

DEFAULT_TIMEOUT = 60.0

# How to start an implementation that is not itself executable. The stem is
# the platform; the suffix says what runs it.
_INTERPRETERS: dict[str, tuple[str, ...]] = {
    ".sh": ("bash", "sh"),
    ".bash": ("bash",),
    ".zsh": ("zsh",),
    ".py": (sys.executable, "python3", "python"),
    ".js": ("node",),
    ".mjs": ("node",),
    ".ts": ("bun", "deno", "tsx"),
    ".rb": ("ruby",),
    ".pl": ("perl",),
    ".ps1": ("pwsh", "powershell"),
}

# Outcomes of one example.
PASSED = "passed"
FAILED = "failed"
# Outcomes of one tool, beyond pass/fail.
NOT_IMPLEMENTED = "not-implemented"
NOT_APPLICABLE = "not-applicable"
NO_EXAMPLES = "no-examples"
MISSING_REQUIREMENT = "missing-requirement"
INVALID_SPEC = "invalid-spec"


@dataclass(frozen=True)
class CaseResult:
    """One example, run."""

    title: str
    status: str  # passed | failed
    detail: str = ""
    expected: Any = None
    actual: Any = None
    exit_code: int | None = None
    stderr: str = ""

    @property
    def passed(self) -> bool:
        return self.status == PASSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "expected": self.expected,
            "actual": self.actual,
            "exit_code": self.exit_code,
            "stderr": self.stderr,
        }


@dataclass(frozen=True)
class ToolCheckResult:
    """One tool, checked on one platform."""

    name: str
    platform: str
    status: str  # passed | failed | not-implemented | not-applicable | no-examples | …
    implementation: str | None = None
    cases: tuple[CaseResult, ...] = ()
    detail: str = ""

    @property
    def verified(self) -> bool:
        """Only a tool that ran its examples and passed all of them is verified."""
        return self.status == PASSED and bool(self.cases)

    @property
    def ran(self) -> bool:
        return self.status in (PASSED, FAILED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "platform": self.platform,
            "status": self.status,
            "implementation": self.implementation,
            "detail": self.detail,
            "cases": [case.to_dict() for case in self.cases],
        }


def check_tool(
    tool_dir: Path,
    *,
    platform: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    env: dict[str, str] | None = None,
) -> ToolCheckResult:
    """Run every example in `tool_dir/TOOL.md` against `tool_dir/<platform>.<ext>`."""
    platform = platform or current_platform()
    name = tool_dir.name
    spec_path = tool_dir / TOOL_FILENAME
    if not spec_path.is_file():
        return ToolCheckResult(
            name, platform, INVALID_SPEC, detail=f"no {TOOL_FILENAME} in {tool_dir}"
        )
    try:
        tool = parse_tool(spec_path.read_text(encoding="utf-8"))
    except ToolError as exc:
        return ToolCheckResult(name, platform, INVALID_SPEC, detail=str(exc))
    if tool.name:
        name = tool.name

    if tool.platforms and platform not in tool.platforms:
        return ToolCheckResult(
            name,
            platform,
            NOT_APPLICABLE,
            detail=f"spec is for {', '.join(tool.platforms)}, not {platform}",
        )

    implementation = implementation_for(tool_dir, platform)
    if implementation is None:
        return ToolCheckResult(
            name, platform, NOT_IMPLEMENTED, detail=f"no {platform}.<ext> beside {TOOL_FILENAME}"
        )

    examples = [example for example in tool.examples if example.is_complete]
    if not examples:
        return ToolCheckResult(
            name,
            platform,
            NO_EXAMPLES,
            implementation=implementation.name,
            detail="the spec has no complete examples — nothing to check mechanically",
        )

    missing = [binary for binary in tool.requires if shutil.which(binary) is None]
    if missing:
        return ToolCheckResult(
            name,
            platform,
            MISSING_REQUIREMENT,
            implementation=implementation.name,
            detail=f"not on PATH: {', '.join(missing)}",
        )

    command = launch_command(implementation)
    if command is None:
        return ToolCheckResult(
            name,
            platform,
            MISSING_REQUIREMENT,
            implementation=implementation.name,
            detail=f"{implementation.name} is not executable and no interpreter for "
            f"'{implementation.suffix}' is on PATH",
        )

    cases = tuple(
        _run_case(command, example, tool, cwd=tool_dir, timeout=timeout, env=env)
        for example in examples
    )
    status = PASSED if all(case.passed for case in cases) else FAILED
    return ToolCheckResult(name, platform, status, implementation=implementation.name, cases=cases)


@dataclass(frozen=True)
class ToolRunResult:
    """Ein einzelner Lauf mit freier Eingabe (D7): was die App im Tools-Tab zeigt."""

    name: str
    platform: str
    ok: bool
    output: Any = None
    exit_code: int | None = None
    stderr: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "platform": self.platform,
            "ok": self.ok,
            "output": self.output,
            "exit_code": self.exit_code,
            "stderr": self.stderr,
            "detail": self.detail,
        }


def run_tool(
    tool_dir: Path,
    input_value: Any,
    *,
    platform: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    env: dict[str, str] | None = None,
) -> ToolRunResult:
    """Startet `tool_dir/<platform>.<ext>` nach D7 mit `input_value` auf stdin.

    Kein Vergleich mit Beispielen — das ist `check_tool`. Hier geht es um
    den Knopf „Ausführen" in einer App: JSON rein, JSON raus, oder eine
    Erklärung, warum nicht.
    """
    platform = platform or current_platform()
    name = tool_dir.name
    implementation = implementation_for(tool_dir, platform)
    if implementation is None:
        return ToolRunResult(
            name, platform, False, detail=f"no {platform}.<ext> beside {TOOL_FILENAME}"
        )
    command = launch_command(implementation)
    if command is None:
        return ToolRunResult(
            name,
            platform,
            False,
            detail=f"no interpreter for {implementation.name} on this machine",
        )
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(input_value),
            capture_output=True,
            text=True,
            cwd=tool_dir,
            timeout=timeout,
            env={**os.environ, **(env or {})},
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ToolRunResult(name, platform, False, detail=f"timed out after {timeout:g}s")
    except OSError as exc:
        return ToolRunResult(name, platform, False, detail=f"could not start: {exc}")
    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    if not stdout:
        return ToolRunResult(
            name,
            platform,
            False,
            exit_code=completed.returncode,
            stderr=stderr,
            detail=f"no output on stdout (exit {completed.returncode})",
        )
    try:
        output = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return ToolRunResult(
            name,
            platform,
            False,
            output=stdout,
            exit_code=completed.returncode,
            stderr=stderr,
            detail=f"stdout is not JSON ({exc.msg})",
        )
    ok = completed.returncode == 0 and not (isinstance(output, dict) and output.get("ok") is False)
    return ToolRunResult(
        name, platform, ok, output=output, exit_code=completed.returncode, stderr=stderr
    )


def launch_command(implementation: Path) -> list[str] | None:
    """How to start the implementation: directly if executable, else via its interpreter."""
    path = str(implementation.resolve())
    if os.access(implementation, os.X_OK) and not implementation.suffix == ".ps1":
        return [path]
    for candidate in _INTERPRETERS.get(implementation.suffix.lower(), ()):
        found = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if found:
            if implementation.suffix.lower() == ".ps1":
                return [found, "-NoProfile", "-File", path]
            return [found, path]
    return None


def _run_case(
    command: list[str],
    example: Example,
    tool: Tool,
    *,
    cwd: Path,
    timeout: float,
    env: dict[str, str] | None,
) -> CaseResult:
    stdin = json.dumps(example.input)
    try:
        completed = subprocess.run(
            command,
            input=stdin,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            env={**os.environ, **(env or {})},
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CaseResult(
            example.title, FAILED, detail=f"timed out after {timeout:g}s", expected=example.output
        )
    except OSError as exc:
        return CaseResult(
            example.title, FAILED, detail=f"could not start: {exc}", expected=example.output
        )

    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    if not stdout:
        detail = f"no output on stdout (exit {completed.returncode})"
        if stderr:
            detail += f": {stderr.splitlines()[-1]}"
        return CaseResult(
            example.title,
            FAILED,
            detail=detail,
            expected=example.output,
            exit_code=completed.returncode,
            stderr=stderr,
        )
    try:
        actual = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return CaseResult(
            example.title,
            FAILED,
            detail=f"stdout is not JSON ({exc.msg}): {stdout[:200]}",
            expected=example.output,
            actual=stdout,
            exit_code=completed.returncode,
            stderr=stderr,
        )

    problems: list[str] = []
    problems.extend(differences(example.output, actual))
    problems.extend(_schema_problems(tool.outputs, actual))
    expects_ok = isinstance(example.output, dict) and example.output.get("ok") is True
    if expects_ok and completed.returncode != 0:
        problems.append(f"exit code is {completed.returncode}, expected 0 for an ok result")

    return CaseResult(
        example.title,
        PASSED if not problems else FAILED,
        detail="; ".join(problems),
        expected=example.output,
        actual=actual,
        exit_code=completed.returncode,
        stderr=stderr,
    )


def differences(expected: Any, actual: Any, path: str = "$") -> list[str]:
    """Where `actual` fails to cover `expected`. Empty means it does.

    Objects: every expected key must be present and cover; extra keys are fine.
    Lists: same length, element-wise. Scalars: equal (an int and the same
    float are equal, `True` and `1` are not).
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected an object, got {_kind(actual)}"]
        out: list[str] = []
        for key, value in expected.items():
            if key not in actual:
                out.append(f"{path}.{key}: missing")
            else:
                out.extend(differences(value, actual[key], f"{path}.{key}"))
        return out
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: expected an array, got {_kind(actual)}"]
        if len(expected) != len(actual):
            return [f"{path}: expected {len(expected)} item(s), got {len(actual)}"]
        out = []
        for index, (want, got) in enumerate(zip(expected, actual, strict=True)):
            out.extend(differences(want, got, f"{path}[{index}]"))
        return out
    if isinstance(expected, bool) or isinstance(actual, bool):
        if expected is not actual:
            return [f"{path}: expected {json.dumps(expected)}, got {json.dumps(actual)}"]
        return []
    if expected != actual:
        return [f"{path}: expected {json.dumps(expected)}, got {json.dumps(actual)}"]
    return []


def _schema_problems(schema: Any, value: Any) -> list[str]:
    if not isinstance(schema, dict):
        return []
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)
    except SchemaError:
        return []
    except ValidationError as exc:
        where = "$" + "".join(
            f"[{p}]" if isinstance(p, int) else f".{p}" for p in exc.absolute_path
        )
        return [f"output violates the outputs schema at {where}: {exc.message}"]
    return []


def _kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, list):
        return "an array"
    return "an object"


__all__ = [
    "DEFAULT_TIMEOUT",
    "FAILED",
    "INVALID_SPEC",
    "MISSING_REQUIREMENT",
    "NOT_APPLICABLE",
    "NOT_IMPLEMENTED",
    "NO_EXAMPLES",
    "PASSED",
    "CaseResult",
    "ToolCheckResult",
    "check_tool",
    "differences",
    "launch_command",
]
