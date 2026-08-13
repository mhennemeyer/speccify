"""Tests for the network half of `speccify check`.

The offline checks live in `test_skill_check.py`. What is pinned here is the
soft-404 detection: a host that answers `200` for a page that does not exist,
which status codes alone cannot see.
"""

from __future__ import annotations

from typing import Any

from speccify_core import check_links
from speccify_core.skill import parse_skill


def _sources(*urls: str) -> Any:
    """A skill whose Sources section lists each URL."""
    lines = "\n".join(f"- [Source {i}]({url}) — retrieved 2026-08-06" for i, url in enumerate(urls))
    return parse_skill(
        "---\nname: a-skill\ndescription: Something. Use when something.\n---\n\n"
        f"## Sources\n\n{lines}\n"
    ).sources


# --- Soft 404s ------------------------------------------------------------------
#
# Hermetic: an httpx MockTransport plays the host, so these run in the default
# suite rather than behind the `links` marker.


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


def _check(sources: Any, handler: Any) -> list[Any]:
    return check_links(sources, transport=_transport(handler))


def test_soft_404_is_reported_even_though_the_status_is_200() -> None:
    """A host that answers 200 for everything must not pass a dead source."""
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        # This host never 404s — including for the canary.
        if request.url.path == "/real":
            return httpx.Response(200, html=_REAL_PAGE)
        return httpx.Response(200, html=_NOT_FOUND_PAGE)

    findings = _check(_sources("https://example.com/real", "https://example.com/moved"), handler)
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

    findings = _check(_sources("https://example.com/fine"), handler)
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
        _sources("https://example.com/help/real-page", "https://example.com/help/gone"),
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

    findings = _check(_sources("https://spa.example/a", "https://spa.example/b"), handler)
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
        _sources("https://a.example/one", "https://a.example/two", "https://b.example/three"),
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

    findings = _check(_sources("https://example.com/real", "https://example.com/gone"), handler)
    assert [f.path for f in findings] == ["$.sources[1]"], [f.format() for f in findings]


def test_unreachable_canary_falls_back_to_status_codes() -> None:
    """A probe that cannot run must not break the check it is helping."""
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/speccify-link-check"):
            raise httpx.ConnectError("probe failed")
        return httpx.Response(200, html=_REAL_PAGE)

    findings = _check(_sources("https://example.com/real"), handler)
    assert findings == [], [f.format() for f in findings]
