"""`speccify check`: is this playbook still true?

Code has compilers; playbooks have decay. A playbook whose links are dead or
whose sources were last read two years ago is worse than no playbook, because
an agent will follow it confidently. So the health check asks three things:

* **structure** — the same validation `lint` runs (offline, always),
* **age** — how long ago each source was retrieved (offline, always),
* **reachability** — do the URLs still resolve (network, opt-in), including
  hosts that answer `200` for pages that do not exist.

Reachability is deliberately separate: it needs the network, it is slow, and a
flaky corporate proxy should never fail a normal test run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from speccify_core.playbook import (
    STALE_SOURCE_DAYS,
    Playbook,
    parse_playbook,
    validate_playbook,
)

DEFAULT_TIMEOUT = 10.0
# A source with no retrieval date at all is worse than an old one: nothing
# tells you whether it was ever checked.
_UNKNOWN_AGE = "retrieved date is unreadable — the age of this source is unknown"


@dataclass(frozen=True)
class Finding:
    """One health finding. `error` fails a check, `warning` reports."""

    level: str
    path: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.level == "error"

    def format(self) -> str:
        return f"{self.level}: {self.path}: {self.message}"


def check_playbook(
    data: Any,
    *,
    bundle_files: set[str] | None = None,
    today: date | None = None,
    stale_days: int = STALE_SOURCE_DAYS,
) -> list[Finding]:
    """Offline health check: structure plus source age."""
    findings = [
        Finding("error", issue.path, issue.message)
        for issue in validate_playbook(data, bundle_files=bundle_files)
    ]
    if findings:
        # Age checks on a structurally broken playbook would just add noise.
        return findings

    playbook = parse_playbook(data)
    findings.extend(check_source_age(playbook, today=today or date.today(), stale_days=stale_days))
    return findings


def check_source_age(
    playbook: Playbook,
    *,
    today: date,
    stale_days: int = STALE_SOURCE_DAYS,
) -> list[Finding]:
    """Warn about sources that have not been re-read in a long time."""
    findings: list[Finding] = []
    for index, source in enumerate(playbook.sources):
        path = f"$.sources[{index}]"
        age = source.age_days(today=today)
        if age is None:
            findings.append(Finding("error", path, _UNKNOWN_AGE))
            continue
        if age < 0:
            findings.append(
                Finding("warning", path, f"retrieved date is {abs(age)} days in the future")
            )
        elif age > stale_days:
            findings.append(
                Finding(
                    "warning",
                    path,
                    f"last retrieved {age} days ago ({source.retrieved}) — re-read "
                    f"'{source.title}' and update the date, or fix what changed",
                )
            )
    return findings


def check_links(
    sources: Any,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    transport: Any = None,
    path_prefix: str = "$.sources",
) -> list[Finding]:
    """Network check: are the sources still reachable?

    Takes anything iterable of objects with a `.url` — a playbook's sources or
    a skill's. The format has never mattered here.

    A redirect is fine, a 404 is not. Servers that dislike HEAD get a second
    chance with GET before being reported.

    Some hosts answer `200` for pages that do not exist and put "Page Not
    Found" in the body — a documentation site built as a single application
    does this routinely. Status codes are blind to that, so hosts are
    calibrated once against an invented URL; see `_probe_soft_404`.

    `transport` is an httpx transport for tests, so this is exercisable
    without the network.
    """
    import httpx

    findings: list[Finding] = []
    probes: dict[str, _SoftNotFound | None] = {}
    with httpx.Client(timeout=timeout, follow_redirects=True, transport=transport) as client:
        for index, source in enumerate(sources):
            path = f"{path_prefix}[{index}]"
            host = _host_key(source.url)
            if host not in probes:
                probes[host] = _probe_soft_404(client, source.url)
            probe = probes[host]
            try:
                if probe is None:
                    response = client.head(source.url)
                    if response.status_code >= 400:
                        response = client.get(source.url)
                else:
                    # HEAD has no body to compare, and the body is the only
                    # thing that distinguishes a real page on such a host.
                    response = client.get(source.url)
            except httpx.HTTPError as exc:
                findings.append(
                    Finding("error", path, f"{source.url} is unreachable: {type(exc).__name__}")
                )
                continue
            if response.status_code == 404:
                findings.append(Finding("error", path, f"{source.url} is gone (404)"))
            elif response.status_code >= 400:
                findings.append(
                    Finding("warning", path, f"{source.url} answered {response.status_code}")
                )
            elif probe is not None and probe.matches(response.text):
                findings.append(
                    Finding(
                        "error",
                        path,
                        f"{source.url} answered 200 but the page says it does not exist "
                        f"(this host serves the same '{probe.title}' page for URLs that "
                        f"cannot exist) — the source moved or was never there",
                    )
                )
    return findings


# --- Soft 404s ------------------------------------------------------------------
#
# A host that answers 200 for a URL that cannot exist is lying about the status,
# and `--links` would happily pass a source that has moved. Detecting that by
# grepping every page for "not found" would flag pages that legitimately discuss
# 404s, so two independent signals are required instead:
#
#   1. a URL we invented renders a page that announces itself as missing
#      (calibration — one request per host), and
#   2. the source's own page is that same page, by title or by body.
#
# The canary's *status code* is deliberately ignored. developer.apple.com, for
# instance, answers an honest 404 at the site root and a 200 for missing pages
# inside its help section — while serving the identical "Page Not Found" body
# for both. What calibration needs is what a missing page looks like on this
# host, not what it is labelled.
#
# A host whose canary shows no not-found marker is never compared: one shell
# served for every path (real ones included) cannot be told apart, and guessing
# there would reject an entire site.

_CANARY_PATH = "/speccify-link-check-this-path-does-not-exist"
_NOT_FOUND_MARKERS = ("not found", "404", "doesn't exist", "does not exist", "no longer exists")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class _SoftNotFound:
    """How one host renders a page that does not exist."""

    title: str
    body: str

    def matches(self, text: str) -> bool:
        """Is this response that host's not-found page?

        Title first: it survives the nonces and timestamps that make whole
        bodies differ between two requests. Body equality catches hosts whose
        not-found page has no title of its own.
        """
        title = _page_title(text)
        if title is not None and title == self.title:
            return True
        return _normalize(text) == self.body


def _host_key(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _page_title(text: str) -> str | None:
    match = _TITLE_RE.search(text) or _H1_RE.search(text)
    if match is None:
        return None
    stripped = _WS_RE.sub(" ", _TAG_RE.sub(" ", match.group(1))).strip().lower()
    return stripped or None


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", text).strip().lower()


def _probe_soft_404(client: Any, url: str) -> _SoftNotFound | None:
    """Learn what a missing page looks like on this host.

    Returns `None` — meaning "believe this host's status codes" — unless the
    invented URL renders a page that announces itself as missing. The status
    code of that response is ignored on purpose: a host may 404 honestly here
    and still answer 200 for missing pages elsewhere, and it is the rendered
    page, not the label, that lets us recognise those.
    """
    import httpx

    try:
        response = client.get(_host_key(url) + _CANARY_PATH)
    except httpx.HTTPError:
        return None
    title = _page_title(response.text)
    if title is None or not any(marker in title for marker in _NOT_FOUND_MARKERS):
        return None
    return _SoftNotFound(title=title, body=_normalize(response.text))


__all__ = [
    "DEFAULT_TIMEOUT",
    "Finding",
    "check_links",
    "check_playbook",
    "check_source_age",
]
