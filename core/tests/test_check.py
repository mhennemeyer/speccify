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
        findings = check_links(parse_playbook(bundle.parsed()).sources)
        errors = [f.format() for f in findings if f.is_error]
        assert errors == [], f"{playbook_id}: {errors}"


# --- Soft 404s ------------------------------------------------------------------
#
# Hermetic: an httpx MockTransport plays the host, so these run in the default
# suite rather than behind the `links` marker.


def _sources_playbook(*urls: str) -> Any:
    """A valid playbook whose steps reference one source per URL."""
    return {
        "schema_version": 1,
        "id": "@org/thing",
        "version": "1.0.0",
        "title": "Do the thing",
        "summary": "Get from A to B.",
        "steps": [
            {
                "id": "first",
                "title": "First",
                "detail": "Do this.",
                "sources": [f"s{i}" for i, _ in enumerate(urls)],
            }
        ],
        "sources": [
            {
                "id": f"s{i}",
                "title": f"Source {i}",
                "url": url,
                "retrieved": "2026-08-06",
            }
            for i, url in enumerate(urls)
        ],
    }


_NOT_FOUND_PAGE = (
    "<html><head><title>Page Not Found - Example</title></head>"
    "<body><p>Sorry, we could not find that.</p></body></html>"
)
_REAL_PAGE = (
    "<html><head><title>In-app purchase types - Example</title></head>"
    "<body><p>A consumable is used once.</p></body></html>"
)


def _transport(handler: Any) -> Any:
    import httpx

    return httpx.MockTransport(handler)


def _check(playbook_data: Any, handler: Any) -> list[Any]:
    from speccify_core import check_links

    return check_links(parse_playbook(playbook_data).sources, transport=_transport(handler))


def test_soft_404_is_reported_even_though_the_status_is_200() -> None:
    """A host that answers 200 for everything must not pass a dead source."""
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        # This host never 404s — including for the canary.
        if request.url.path == "/real":
            return httpx.Response(200, html=_REAL_PAGE)
        return httpx.Response(200, html=_NOT_FOUND_PAGE)

    findings = _check(
        _sources_playbook("https://example.com/real", "https://example.com/moved"), handler
    )
    messages = [f.format() for f in findings]
    assert len(findings) == 1, messages
    assert findings[0].is_error
    assert "$.sources[1]" in findings[0].path
    assert "answered 200 but the page says it does not exist" in findings[0].message


def test_canary_without_a_recognisable_page_keeps_the_cheap_head_path() -> None:
    """Nothing to calibrate on means: believe the status codes, use HEAD."""
    import httpx

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.method} {request.url.path}")
        if request.url.path.startswith("/speccify-link-check"):
            return httpx.Response(404)  # bare 404, no page to learn from
        return httpx.Response(200, html=_REAL_PAGE)

    findings = _check(_sources_playbook("https://example.com/fine"), handler)
    assert findings == [], [f.format() for f in findings]
    assert "HEAD /fine" in seen, seen


def test_honest_at_the_root_but_soft_404_deeper_is_still_caught() -> None:
    """The shape developer.apple.com actually has.

    The site root answers an honest 404 for an invented path, while a missing
    page *inside* the help section answers 200 — both rendering the identical
    "Page Not Found" body. Calibrating on the canary's status code would give
    up right here, which is why only its rendered page is used.
    """
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/speccify-link-check"):
            return httpx.Response(404, html=_NOT_FOUND_PAGE)  # honest status, telling body
        if request.url.path == "/help/real-page":
            return httpx.Response(200, html=_REAL_PAGE)
        return httpx.Response(200, html=_NOT_FOUND_PAGE)  # soft 404

    findings = _check(
        _sources_playbook("https://example.com/help/real-page", "https://example.com/help/gone"),
        handler,
    )
    assert [f.path for f in findings] == ["$.sources[1]"], [f.format() for f in findings]
    assert findings[0].is_error


def test_uninformative_200_does_not_calibrate() -> None:
    """A host serving one shell for every path must not flag its whole site.

    Without a not-found marker there is no way to tell a real page from a
    missing one, and guessing would reject every source on such a host.
    """
    import httpx

    shell = "<html><head><title>Example Docs</title></head><body><div id='app'></div></body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html=shell)

    findings = _check(_sources_playbook("https://spa.example/a", "https://spa.example/b"), handler)
    assert findings == [], [f.format() for f in findings]


def test_probe_runs_once_per_host() -> None:
    import httpx

    canary_hits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/speccify-link-check"):
            canary_hits.append(str(request.url))
            return httpx.Response(200, html=_NOT_FOUND_PAGE)
        return httpx.Response(200, html=_REAL_PAGE)

    _check(
        _sources_playbook(
            "https://a.example/one", "https://a.example/two", "https://b.example/three"
        ),
        handler,
    )
    assert len(canary_hits) == 2, canary_hits


def test_body_match_catches_a_not_found_page_without_its_own_title() -> None:
    """Some hosts keep one title for the whole site; compare bodies then."""
    import httpx

    titled_missing = "<html><head><h1>404 not found</h1></head><body>gone</body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/real":
            return httpx.Response(200, html=_REAL_PAGE)
        return httpx.Response(200, html=titled_missing)

    findings = _check(
        _sources_playbook("https://example.com/real", "https://example.com/gone"), handler
    )
    assert [f.path for f in findings] == ["$.sources[1]"], [f.format() for f in findings]


def test_unreachable_canary_falls_back_to_status_codes() -> None:
    """A probe that cannot run must not break the check it is helping."""
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/speccify-link-check"):
            raise httpx.ConnectError("probe failed")
        return httpx.Response(200, html=_REAL_PAGE)

    findings = _check(_sources_playbook("https://example.com/real"), handler)
    assert findings == [], [f.format() for f in findings]
