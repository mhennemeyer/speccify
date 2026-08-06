"""`speccify check`: is this playbook still true?

Code has compilers; playbooks have decay. A playbook whose links are dead or
whose sources were last read two years ago is worse than no playbook, because
an agent will follow it confidently. So the health check asks three things:

* **structure** — the same validation `lint` runs (offline, always),
* **age** — how long ago each source was retrieved (offline, always),
* **reachability** — do the URLs still resolve (network, opt-in).

Reachability is deliberately separate: it needs the network, it is slow, and a
flaky corporate proxy should never fail a normal test run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

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


def check_links(playbook: Playbook, *, timeout: float = DEFAULT_TIMEOUT) -> list[Finding]:
    """Network check: are the sources still reachable?

    A redirect is fine, a 404 is not. Servers that dislike HEAD get a second
    chance with GET before being reported.
    """
    import httpx

    findings: list[Finding] = []
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for index, source in enumerate(playbook.sources):
            path = f"$.sources[{index}]"
            try:
                response = client.head(source.url)
                if response.status_code >= 400:
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
    return findings


__all__ = [
    "DEFAULT_TIMEOUT",
    "Finding",
    "check_links",
    "check_playbook",
    "check_source_age",
]
