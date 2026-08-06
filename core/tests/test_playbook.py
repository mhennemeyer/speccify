"""Tests for the playbook model and its validation rules."""

from __future__ import annotations

import copy
from datetime import date
from typing import Any

import pytest
import yaml
from speccify_core import (
    LocalLibrary,
    Version,
    parse_playbook,
    validate_playbook,
)

FIXTURES = "playbooks"


def _minimal() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "@org/thing",
        "version": "1.0.0",
        "title": "Do the thing",
        "summary": "Get from A to B without the detours.",
        "steps": [
            {
                "id": "first",
                "title": "First step",
                "detail": "Do this.",
                "sources": ["doc"],
            }
        ],
        "sources": [
            {
                "id": "doc",
                "title": "The docs",
                "url": "https://example.com/docs",
                "retrieved": "2026-08-06",
            }
        ],
    }


def test_parse_reads_the_workflow() -> None:
    playbook = parse_playbook(_minimal())
    assert playbook.id == "@org/thing"
    assert [step.id for step in playbook.steps] == ["first"]
    assert playbook.source("doc") is not None
    assert playbook.step("first").sources == ("doc",)


def test_unquoted_yaml_dates_are_accepted() -> None:
    """Authors write `retrieved: 2026-08-06`; PyYAML makes that a date object."""
    raw = yaml.safe_load(
        "schema_version: 1\n"
        "id: '@org/thing'\n"
        "version: 1.0.0\n"
        "title: T\n"
        "summary: S\n"
        "steps:\n"
        "  - id: first\n"
        "    title: First\n"
        "    detail: Do this.\n"
        "    sources: [doc]\n"
        "sources:\n"
        "  - id: doc\n"
        "    title: Docs\n"
        "    url: https://example.com\n"
        "    retrieved: 2026-08-06\n"
    )
    assert validate_playbook(raw) == []
    assert parse_playbook(raw).source("doc").retrieved == "2026-08-06"


def test_source_age_is_measurable() -> None:
    source = parse_playbook(_minimal()).source("doc")
    assert source.age_days(today=date(2026, 8, 16)) == 10


def test_uses_marks_a_step_as_delegated() -> None:
    data = copy.deepcopy(_minimal())
    data["steps"].append({"id": "child", "title": "Reuse", "uses": "@org/other@^1.0"})
    playbook = parse_playbook(data)
    assert playbook.uses == ("@org/other@^1.0",)
    assert playbook.step("child").is_delegated
    assert not playbook.step("first").is_delegated


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        pytest.param(
            lambda d: d["steps"].append({"id": "first", "title": "Dup", "detail": "x"}),
            "Duplicate step id",
            id="duplicate-step-id",
        ),
        pytest.param(
            lambda d: d["steps"].append({"id": "empty", "title": "Empty"}),
            "either `detail` or `uses`",
            id="empty-step",
        ),
        pytest.param(
            lambda d: d["steps"].append(
                {"id": "both", "title": "Both", "detail": "x", "uses": "@org/other@^1.0"}
            ),
            "not both",
            id="detail-and-uses",
        ),
        pytest.param(
            lambda d: d["steps"][0]["sources"].append("ghost"),
            "Unknown source 'ghost'",
            id="unknown-source",
        ),
        pytest.param(
            lambda d: d["sources"].append(
                {
                    "id": "orphan",
                    "title": "Unused",
                    "url": "https://example.com/x",
                    "retrieved": "2026-08-06",
                }
            ),
            "not referenced by any step",
            id="orphan-source",
        ),
    ],
)
def test_cross_reference_rules(mutate, expected: str) -> None:
    data = copy.deepcopy(_minimal())
    mutate(data)
    messages = " ".join(issue.message for issue in validate_playbook(data))
    assert expected in messages


def test_assets_are_checked_against_the_bundle() -> None:
    data = copy.deepcopy(_minimal())
    data["steps"][0]["assets"] = ["assets/script.sh"]
    assert validate_playbook(data, bundle_files={"playbook.yaml"})[0].message.startswith(
        "Asset 'assets/script.sh' is not part"
    )
    assert validate_playbook(data, bundle_files={"playbook.yaml", "assets/script.sh"}) == []


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda d: d.__setitem__("schema_version", 2), id="wrong-schema-version"),
        pytest.param(lambda d: d.__setitem__("id", "no-scope"), id="unscoped-id"),
        pytest.param(lambda d: d.__setitem__("version", "1.0"), id="not-semver"),
        pytest.param(lambda d: d.__setitem__("steps", []), id="no-steps"),
        pytest.param(lambda d: d.__setitem__("owner", "me"), id="unknown-key"),
        pytest.param(
            lambda d: d["steps"][0].__setitem__("assets", ["../escape.sh"]), id="asset-escape"
        ),
        pytest.param(
            lambda d: d["sources"][0].__setitem__("url", "ftp://example.com"), id="non-http-source"
        ),
        pytest.param(lambda d: d["sources"][0].__setitem__("retrieved", "gestern"), id="bad-date"),
    ],
)
def test_schema_rejects_broken_playbooks(mutate) -> None:
    data = copy.deepcopy(_minimal())
    mutate(data)
    assert validate_playbook(data) != []


def test_reference_playbooks_are_valid() -> None:
    """The playbooks shipped in this repo must always validate."""
    library = LocalLibrary(FIXTURES)
    found = library.list_playbooks()
    assert found, "no reference playbooks found"
    for playbook_id, version in found:
        bundle = library.fetch(playbook_id, version)
        issues = validate_playbook(bundle.parsed(), bundle_files=set(bundle.files))
        assert issues == [], f"{playbook_id}@{version}: {[i.format() for i in issues]}"


def test_reference_playbook_reuses_a_child() -> None:
    bundle = LocalLibrary(FIXTURES).fetch("@speccify/macos-notarize-tauri", Version.parse("1.0.0"))
    playbook = parse_playbook(bundle.parsed())
    assert playbook.uses == ("@speccify/apple-developer-id-cert@^1.0",)
    assert playbook.asset_paths == ("assets/verify-signatures.sh",)
