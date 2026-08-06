"""Minimal version solver over playbook sources (MVS, Go-style).

Every constraint is a range; the resolver picks the **lowest version that
satisfies all of them** and walks `steps[].uses` transitively. Deterministic and
boring on purpose: the lockfile has to be reproducible months later.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field

from speccify_core.manifest import ProjectManifest
from speccify_core.playbook import parse_playbook
from speccify_core.registry import Bundle, Library, LibraryError, Version, bundle_sha256

_RANGE_PATTERN = re.compile(
    r"^(?P<op>\^?)(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)(?:\.(?P<patch>0|[1-9]\d*))?$"
)
_LOCAL_USES_PATTERN = re.compile(
    r"^(?P<id>@[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*)(?:@(?P<range>.+))?$"
)
# Ranges are numeric, so splitting at the last `@` stays unambiguous for URLs.
_GIT_USES_PATTERN = re.compile(r"^(?P<id>git\+[^\s]+?)(?:@(?P<range>\^?\d+\.\d+(?:\.\d+)?))?$")


class ResolverError(Exception):
    """The dependency closure could not be resolved."""


class VersionNotFoundError(ResolverError):
    """No available version satisfies the requested range."""


class RangeConflictError(ResolverError):
    """The requested ranges contradict each other."""


@dataclass(frozen=True)
class Range:
    """Exact (`1.2.0`) or caret (`^1.2`, `^1.2.3`) range."""

    raw: str
    exact: bool
    min_version: Version
    upper_exclusive: Version | None

    @classmethod
    def parse(cls, raw: str) -> Range:
        match = _RANGE_PATTERN.match(raw.strip())
        if not match:
            raise ResolverError(f"Invalid range '{raw}': expected 'X.Y.Z' or '^X.Y[.Z]'.")
        major = int(match.group("major"))
        minor = int(match.group("minor"))
        patch = int(match.group("patch") or 0)
        minimum = Version(major, minor, patch)
        if not match.group("op"):
            if match.group("patch") is None:
                raise ResolverError(f"Invalid range '{raw}': exact ranges need a patch level.")
            return cls(raw=raw, exact=True, min_version=minimum, upper_exclusive=None)
        upper = Version(major + 1, 0, 0) if major > 0 else Version(0, minor + 1, 0)
        return cls(raw=raw, exact=False, min_version=minimum, upper_exclusive=upper)

    def contains(self, version: Version) -> bool:
        if version < self.min_version:
            return False
        if self.exact:
            return version == self.min_version
        return self.upper_exclusive is None or version < self.upper_exclusive


@dataclass(frozen=True)
class Resolution:
    playbook_id: str
    version: Version
    bundle_sha256: str
    via: str = "local"
    source_commit: str | None = None


@dataclass(frozen=True)
class ResolvedGraph:
    resolutions: list[Resolution] = field(default_factory=list)


@dataclass(frozen=True)
class _Constraint:
    playbook_id: str
    range: Range
    source: str  # where it came from: "<root>" or "<id>@<version>"


def parse_uses_entry(entry: str) -> tuple[str, str]:
    """`@org/x@^1.0` or `git+https://host/repo@^1.0` -> (id, range)."""
    pattern = _GIT_USES_PATTERN if entry.startswith("git+") else _LOCAL_USES_PATTERN
    match = pattern.match(entry)
    if not match:
        raise ResolverError(
            f"Invalid reference '{entry}': expected '@scope/name[@range]' "
            f"or 'git+<url>[#<path>][@range]'."
        )
    return match.group("id"), match.group("range") or "^0.0"


def _serves(library: Library, playbook_id: str) -> bool:
    predicate = getattr(library, "serves", None)
    return True if predicate is None else bool(predicate(playbook_id))


class Resolver:
    """Resolves a manifest (or a set of constraints) against one or more libraries."""

    def __init__(self, libraries: Library | list[Library]) -> None:
        self._libraries: list[Library] = (
            list(libraries) if isinstance(libraries, list) else [libraries]
        )
        if not self._libraries:
            raise ResolverError("The resolver needs at least one library.")

    @property
    def libraries(self) -> list[Library]:
        return list(self._libraries)

    def resolve(self, manifest: ProjectManifest) -> ResolvedGraph:
        initial = {
            playbook_id: [(range_raw, "<root>")]
            for playbook_id, range_raw in manifest.dependencies.items()
        }
        return self.resolve_constraints(initial)

    def resolve_constraints(self, initial: dict[str, list[tuple[str, str]]]) -> ResolvedGraph:
        constraints: dict[str, list[_Constraint]] = {}
        for playbook_id, items in initial.items():
            for range_raw, source in items:
                constraints.setdefault(playbook_id, []).append(
                    _Constraint(playbook_id, Range.parse(range_raw), source)
                )

        resolved: dict[str, tuple[Version, Bundle]] = {}
        library_for: dict[str, Library] = {}
        queue: deque[str] = deque(constraints)

        while queue:
            playbook_id = queue.popleft()
            if playbook_id not in constraints:
                continue
            library, chosen = self._select(playbook_id, constraints[playbook_id])
            previous = resolved.get(playbook_id)
            if previous is not None and previous[0] == chosen:
                continue
            bundle = library.fetch(playbook_id, chosen)
            library_for[playbook_id] = library
            resolved[playbook_id] = (chosen, bundle)

            source = f"{playbook_id}@{chosen}"
            changed: set[str] = set()
            for reference in _uses_of(bundle):
                dependency_id, range_raw = parse_uses_entry(reference)
                dependency_range = Range.parse(range_raw)
                bucket = constraints.setdefault(dependency_id, [])
                already = any(
                    c.range.raw == dependency_range.raw and c.source == source for c in bucket
                )
                if not already:
                    bucket.append(_Constraint(dependency_id, dependency_range, source))
                    changed.add(dependency_id)
            queue.extend(changed)
            queue.extend(cid for cid in resolved if cid in changed)

        return ResolvedGraph(
            resolutions=[
                Resolution(
                    playbook_id=playbook_id,
                    version=version,
                    bundle_sha256=bundle_sha256(bundle.files),
                    via=library_for[playbook_id].via,
                    source_commit=bundle.source_commit,
                )
                for playbook_id, (version, bundle) in sorted(resolved.items())
            ]
        )

    # --- internals ---------------------------------------------------------

    def _select(self, playbook_id: str, constraints: list[_Constraint]) -> tuple[Library, Version]:
        available: list[Version] = []
        selected: Library | None = None
        for library in self._libraries:
            if not _serves(library, playbook_id):
                continue
            try:
                versions = library.list_versions(playbook_id)
            except LibraryError as exc:
                raise ResolverError(str(exc)) from exc
            if versions:
                selected, available = library, versions
                break

        if selected is None:
            wanted = ", ".join(f"{c.source} ({c.range.raw})" for c in constraints)
            raise VersionNotFoundError(
                f"No versions found for '{playbook_id}'. Requested: {wanted}."
            )

        candidates = [v for v in available if all(c.range.contains(v) for c in constraints)]
        if not candidates:
            wanted = ", ".join(f"{c.source} wants {c.range.raw}" for c in constraints)
            have = ", ".join(str(v) for v in available)
            raise RangeConflictError(
                f"No version of '{playbook_id}' satisfies all constraints "
                f"({wanted}); available: {have}."
            )
        # MVS: the lowest version that satisfies everyone.
        return selected, min(candidates)


def _uses_of(bundle: Bundle) -> list[str]:
    """References to other playbooks, read from the bundle's steps."""
    try:
        playbook = parse_playbook(bundle.parsed())
    except Exception as exc:  # noqa: BLE001 - surfaced as a resolver error
        raise ResolverError(f"{bundle.source_id}@{bundle.version}: {exc}") from exc
    return list(playbook.uses)


__all__ = [
    "Range",
    "RangeConflictError",
    "ResolvedGraph",
    "Resolution",
    "Resolver",
    "ResolverError",
    "VersionNotFoundError",
    "parse_uses_entry",
]
