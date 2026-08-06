"""Tests for the playbook health check (structure, age, links)."""

from __future__ import annotations

import copy
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from speccify_core import (
    LocalLibrary,
    Version,
    check_playbook,
    check_source_age,
    parse_playbook,
)

FIXTURES = Path("playbooks")


def _playbook(retrieved: str = "2026-08-06") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "@org/thing",
        "version": "1.0.0",
        "title": "Do the thing",
        "summary": "Get from A to B.",
        "steps": [{"id": "first", "title": "First", "detail": "Do this.", "sources": ["doc"]}],
        "sources": [
            {
                "id": "doc",
                "title": "The docs",
                "url": "https://example.com/docs",
                "retrieved": retrieved,
            }
        ],
    }


def test_healthy_playbook_has_no_findings() -> None:
    assert check_playbook(_playbook(), today=date(2026, 8, 10)) == []


def test_old_sources_warn_with_the_age_in_the_message() -> None:
    findings = check_playbook(_playbook("2025-01-01"), today=date(2026, 8, 6))
    assert len(findings) == 1
    assert findings[0].level == "warning"
    assert "582 days ago" in findings[0].message
    assert "The docs" in findings[0].message


def test_stale_threshold_is_configurable() -> None:
    data = _playbook("2026-07-01")
    assert check_playbook(data, today=date(2026, 8, 6)) == []
    findings = check_playbook(data, today=date(2026, 8, 6), stale_days=10)
    assert [f.level for f in findings] == ["warning"]


def test_future_dates_are_suspicious() -> None:
    findings = check_playbook(_playbook("2027-01-01"), today=date(2026, 8, 6))
    assert findings[0].level == "warning"
    assert "in the future" in findings[0].message


def test_structural_errors_shadow_age_warnings() -> None:
    """A broken playbook should report the breakage, not a pile of age noise."""
    data = copy.deepcopy(_playbook("2000-01-01"))
    data["steps"][0]["sources"] = ["ghost"]
    findings = check_playbook(data, today=date(2026, 8, 6))
    assert all(finding.is_error for finding in findings)
    assert any("Unknown source" in finding.message for finding in findings)


def test_unreadable_retrieval_date_is_an_error() -> None:
    playbook = parse_playbook(_playbook())
    broken = type(playbook.sources[0])(
        id="doc", title="Docs", url="https://example.com", retrieved="whenever"
    )
    findings = check_source_age(
        type(playbook)(
            id=playbook.id,
            version=playbook.version,
            title=playbook.title,
            summary=playbook.summary,
            steps=playbook.steps,
            sources=(broken,),
        ),
        today=date(2026, 8, 6),
    )
    assert findings[0].is_error


@pytest.mark.parametrize(
    "playbook_id",
    ["@speccify/macos-notarize-tauri", "@speccify/apple-developer-id-cert"],
)
def test_reference_playbooks_are_healthy(playbook_id: str) -> None:
    bundle = LocalLibrary(FIXTURES).fetch(playbook_id, Version.parse("1.0.0"))
    findings = check_playbook(
        bundle.parsed(),
        bundle_files=set(bundle.files),
        today=date.fromisoformat("2026-08-06"),
    )
    assert findings == [], [f.format() for f in findings]


@pytest.mark.links
def test_reference_sources_still_resolve() -> None:
    """Opt-in: needs the network. `pytest -m links`."""
    from speccify_core import check_links

    library = LocalLibrary(FIXTURES)
    for playbook_id, version in library.list_playbooks():
        bundle = library.fetch(playbook_id, version)
        findings = check_links(parse_playbook(bundle.parsed()))
        errors = [f.format() for f in findings if f.is_error]
        assert errors == [], f"{playbook_id}: {errors}"
