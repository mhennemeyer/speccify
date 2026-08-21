"""Tool specs: read, write and check `TOOL.md`.

A skill used to ship its tools as finished scripts under `scripts/` or
`assets/`. That is where sharing broke: the script assumed a Python version, a
shell, a path separator, a binary on `$PATH` — and the person on the other
machine ended up patching a file they did not write.

A **tool spec** shares the contract instead of the implementation. It says what
a tool takes, what it returns, what it touches and — most importantly — what it
does for concrete inputs. The agent that uses the skill writes the
implementation *on the machine where it runs*, in whatever runs there. The spec
is text, so it travels; the examples are the contract, so the result can be
checked (`speccify tool check`, in T3 of the plan).

Layout, inside a skill:

    <skill>/tools/<name>/TOOL.md       the spec
    <skill>/tools/<name>/reference.*   optional: one implementation, one platform

The file mirrors `SKILL.md`: YAML frontmatter, free Markdown body, structure
*inferred* rather than required. `inputs` and `outputs` are JSON Schema because
every agent already speaks it for tool calls and because it lets the examples
be validated mechanically.

Examples live in the body under `## Examples`, one `###` per case:

    ### signed bundle
    input:  {"bundle": "fixtures/Signed.app"}
    output: {"ok": true, "offenders": []}

`input:`/`output:` take a JSON value on the same line. A case that cannot be
parsed is reported by `validate_tool`, not silently dropped — a broken example
is a broken contract.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from speccify_core.skill import Issue, sections

TOOL_FILENAME = "TOOL.md"
TOOLS_DIR = "tools"

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(?P<yaml>.*?)\r?\n---\r?\n?(?P<body>.*)\Z", re.DOTALL)
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CASE_HEADING_RE = re.compile(r"^###\s+(?P<title>.+?)\s*$", re.MULTILINE)
_CASE_LINE_RE = re.compile(r"^\s*(?P<kind>input|output):\s*(?P<json>.+?)\s*$", re.MULTILINE)
_EXAMPLES_SECTION = "examples"

NAME_MAX = 64
DESCRIPTION_MAX = 1024

_UNPARSED = object()


class ToolError(ValueError):
    """A tool spec could not be parsed."""


@dataclass(frozen=True)
class Example:
    """One contract case: for this input, that output."""

    title: str
    input: Any = None
    output: Any = None
    # Set when `input:` or `output:` was present but not valid JSON; the raw
    # text is kept so the finding can quote it.
    errors: tuple[str, ...] = ()

    @property
    def is_complete(self) -> bool:
        return not self.errors and self.input is not _UNPARSED and self.output is not _UNPARSED


@dataclass(frozen=True)
class Tool:
    """A parsed `TOOL.md`."""

    name: str
    description: str
    body: str
    inputs: Any = None
    outputs: Any = None
    effects: str | None = None
    requires: tuple[str, ...] = ()
    runtime: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def examples(self) -> tuple[Example, ...]:
        return tuple(_parse_examples(self.body))


def parse_tool(text: str) -> Tool:
    """Parse `TOOL.md` text. Raises `ToolError` when the frontmatter is unusable."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise ToolError(f"{TOOL_FILENAME} must start with YAML frontmatter delimited by `---`.")
    try:
        front = yaml.safe_load(match.group("yaml")) or {}
    except yaml.YAMLError as exc:
        raise ToolError(f"Frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(front, dict):
        raise ToolError("Frontmatter must be a mapping.")

    known = {
        "name",
        "description",
        "inputs",
        "outputs",
        "effects",
        "requires",
        "runtime",
        "platforms",
    }
    return Tool(
        name=str(front.get("name", "")),
        description=str(front.get("description", "")),
        body=match.group("body"),
        inputs=front.get("inputs"),
        outputs=front.get("outputs"),
        effects=None if front.get("effects") is None else str(front["effects"]),
        requires=_as_list(front.get("requires")),
        runtime=_as_list(front.get("runtime")),
        platforms=_as_list(front.get("platforms")),
        extra={str(k): v for k, v in front.items() if k not in known},
    )


def validate_tool(tool: Tool) -> list[Issue]:
    """What makes a spec *unusable*: no name, no schema, examples that lie."""
    issues: list[Issue] = []

    if not tool.name:
        issues.append(Issue("name", "is required."))
    else:
        if len(tool.name) > NAME_MAX:
            issues.append(
                Issue("name", f"is {len(tool.name)} characters; the maximum is {NAME_MAX}.")
            )
        if not _NAME_RE.match(tool.name):
            issues.append(
                Issue(
                    "name",
                    "may contain only lowercase letters, numbers and single hyphens, "
                    "and may not start or end with one.",
                )
            )

    if not tool.description.strip():
        issues.append(Issue("description", "is required and must be non-empty."))
    elif len(tool.description) > DESCRIPTION_MAX:
        issues.append(
            Issue(
                "description",
                f"is {len(tool.description)} characters; the maximum is {DESCRIPTION_MAX}.",
            )
        )

    for key, schema in (("inputs", tool.inputs), ("outputs", tool.outputs)):
        if schema is None:
            issues.append(
                Issue(key, "is required — a tool without a declared shape cannot be checked.")
            )
            continue
        if not isinstance(schema, dict):
            issues.append(Issue(key, "must be a JSON Schema (a mapping)."))
            continue
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            issues.append(Issue(key, f"is not a valid JSON Schema: {exc.message}"))

    issues.extend(_validate_examples(tool))
    return issues


def _validate_examples(tool: Tool) -> list[Issue]:
    issues: list[Issue] = []
    inputs_ok = isinstance(tool.inputs, dict) and _schema_ok(tool.inputs)
    outputs_ok = isinstance(tool.outputs, dict) and _schema_ok(tool.outputs)
    for index, example in enumerate(tool.examples):
        path = f"$.examples[{index}]"
        for error in example.errors:
            issues.append(Issue(path, error))
        if example.input is _UNPARSED:
            issues.append(Issue(path, f"'{example.title}' has no `input:` line."))
        if example.output is _UNPARSED:
            issues.append(Issue(path, f"'{example.title}' has no `output:` line."))
        if not example.is_complete:
            continue
        if inputs_ok:
            issues.extend(_against(tool.inputs, example.input, f"{path}.input", example.title))
        if outputs_ok:
            issues.extend(_against(tool.outputs, example.output, f"{path}.output", example.title))
    return issues


def _schema_ok(schema: dict[str, Any]) -> bool:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError:
        return False
    return True


def _against(schema: dict[str, Any], value: Any, path: str, title: str) -> list[Issue]:
    try:
        Draft202012Validator(schema).validate(value)
    except ValidationError as exc:
        return [Issue(path, f"'{title}' does not match the declared schema: {exc.message}")]
    return []


def _as_list(value: Any) -> tuple[str, ...]:
    """`requires: codesign` and `requires: [codesign, xcrun]` both work; so does a comma list."""
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def _parse_examples(body: str) -> list[Example]:
    for title, content in sections(body):
        if title.strip().lower() != _EXAMPLES_SECTION:
            continue
        return [_parse_case(m.group("title"), chunk) for m, chunk in _cases(content)]
    return []


def _cases(content: str) -> list[tuple[re.Match[str], str]]:
    matches = list(_CASE_HEADING_RE.finditer(content))
    cases = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        cases.append((match, content[match.end() : end]))
    return cases


def _parse_case(title: str, chunk: str) -> Example:
    values: dict[str, Any] = {"input": _UNPARSED, "output": _UNPARSED}
    errors: list[str] = []
    for match in _CASE_LINE_RE.finditer(chunk):
        kind, raw = match.group("kind"), match.group("json")
        try:
            values[kind] = json.loads(raw)
        except json.JSONDecodeError as exc:
            values[kind] = None
            errors.append(f"'{title}': `{kind}:` is not valid JSON ({exc.msg}): {raw}")
    return Example(
        title=title.strip(), input=values["input"], output=values["output"], errors=tuple(errors)
    )


__all__ = [
    "TOOL_FILENAME",
    "TOOLS_DIR",
    "Example",
    "Tool",
    "ToolError",
    "parse_tool",
    "validate_tool",
]
