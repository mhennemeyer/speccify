"""MVS-Resolver für Phase 1a.

Strikt nach Go-Vorbild: pro Spec-Id wird das Maximum aller geforderten Mindestversionen
gewählt. Anschließend wird verifiziert, dass die gewählte Version mit allen Ranges
kompatibel ist. Phase 1a unterstützt nur exakte Versionen und Caret-Ranges
(`^X.Y` / `^X.Y.Z`); Pre-Releases werden ignoriert (mit Warnung).
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import deque
from dataclasses import dataclass, field

from speccify_core.manifest import ProjectManifest
from speccify_core.registry import LocalRegistry, Registry, RegistryError, Spec, Version

logger = logging.getLogger(__name__)

_RANGE_PATTERN = re.compile(
    r"^(?P<op>\^?)(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)(?:\.(?P<patch>0|[1-9]\d*))?$"
)
_USES_PATTERN = re.compile(r"^(?P<id>@[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*)(?:@(?P<range>.+))?$")


class ResolverError(Exception):
    """Resolver konnte das Dependency-Closure nicht auflösen."""


class VersionNotFoundError(ResolverError):
    """Keine Version im Registry erfüllt die geforderte Range."""


class RangeConflictError(ResolverError):
    """Die geforderten Ranges sind untereinander inkompatibel."""


class ScopeRegistryConflictError(ResolverError):
    """Derselbe ``@scope`` taucht in mehr als einer Registry auf.

    Phase 2 verlangt registry-gebundene Scopes als Schutz gegen Dependency-Confusion
    (siehe Master-Plan; Begründung in :file:`docs/package-manager-comparison.md`):
    ein Scope darf zu **genau einer** Registry gehören. Liefert eine zweite Registry
    eine Spec für einen bereits bei einer anderen Registry gesehenen Scope, lehnt
    der Resolver hart ab statt zu „mergen".
    """


@dataclass(frozen=True)
class Range:
    """Versions-Range. Phase 1a: exakt (`exact=True`) oder Caret (`exact=False`).

    Caret `^X.Y[.Z]` => `>= X.Y.Z, < (X+1).0.0` (für X >= 1)
    bzw. `^0.Y[.Z]` => `>= 0.Y.Z, < 0.(Y+1).0` (Caret-Konvention für 0.x).
    Exakte Range: nur die genannte Version.
    """

    raw: str
    exact: bool
    min_version: Version
    upper_exclusive: Version | None  # None nur bei exact

    @classmethod
    def parse(cls, raw: str) -> Range:
        match = _RANGE_PATTERN.match(raw)
        if not match:
            raise ResolverError(
                f"Ungültige Range '{raw}': Phase 1a erlaubt nur '^X.Y', '^X.Y.Z' "
                f"oder exakte 'X.Y.Z'."
            )
        major = int(match.group("major"))
        minor = int(match.group("minor"))
        patch_raw = match.group("patch")
        op = match.group("op")
        if op == "^":
            patch = int(patch_raw) if patch_raw is not None else 0
            min_v = Version(major, minor, patch)
            if major > 0:
                upper = Version(major + 1, 0, 0)
            else:
                upper = Version(0, minor + 1, 0)
            return cls(raw=raw, exact=False, min_version=min_v, upper_exclusive=upper)
        # exact
        if patch_raw is None:
            raise ResolverError(f"Ungültige Range '{raw}': exakte Versionen brauchen 'X.Y.Z'.")
        v = Version(major, minor, int(patch_raw))
        return cls(raw=raw, exact=True, min_version=v, upper_exclusive=None)

    def contains(self, version: Version) -> bool:
        if self.exact:
            return version == self.min_version
        if version < self.min_version:
            return False
        assert self.upper_exclusive is not None
        return version < self.upper_exclusive


@dataclass(frozen=True)
class Resolution:
    spec_id: str
    version: Version
    spec_sha256: str
    via: str = "registry-fixtures"


@dataclass(frozen=True)
class ResolvedGraph:
    target: str
    resolutions: list[Resolution] = field(default_factory=list)


@dataclass(frozen=True)
class _Constraint:
    spec_id: str
    range: Range
    source: str  # Trace-Quelle, z.B. "<root>" oder "@org/onboarding-wizard@0.1.0"


def _sha256_hex(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


_SCOPE_PREFIX_PATTERN = re.compile(r"^@([a-z0-9][a-z0-9-]*)/")


def _scope_of(spec_id: str) -> str:
    """Extrahiert ``scope`` aus ``@scope/name`` (ohne führendes ``@``).

    Phase 2 Stage 6 nutzt das für Cross-Registry-Scope-Konflikt-Detection.
    """
    match = _SCOPE_PREFIX_PATTERN.match(spec_id)
    if not match:
        raise ResolverError(f"Spec-Id '{spec_id}' hat keinen erkennbaren @scope-Präfix.")
    return match.group(1)


def _parse_uses_entry(entry: str) -> tuple[str, str]:
    match = _USES_PATTERN.match(entry)
    if not match:
        raise ResolverError(f"Ungültiger uses-Eintrag '{entry}': erwartet '@scope/name[@<range>]'.")
    spec_id = match.group("id")
    range_raw = match.group("range") or "^0.0"  # Fallback, sollte selten vorkommen
    return spec_id, range_raw


class Resolver:
    """MVS-Resolver gegen eine oder mehrere Registries.

    Phase 1a-Aufrufer übergeben weiterhin ein einzelnes ``LocalRegistry`` —
    Phase-2 Stage 6 erlaubt zusätzlich eine **Liste** heterogener Registries
    (lokal + remote). Bei mehreren Registries wird pro Spec-Id die erste Registry
    benutzt, die mindestens eine Version anbietet. Pro ``@scope`` wird gespeichert,
    welche Registry ihn bediente; ein zweiter Treffer aus einer anderen Registry
    löst :class:`ScopeRegistryConflictError` aus.
    """

    def __init__(self, registry: LocalRegistry | Registry | list[Registry]) -> None:
        if isinstance(registry, list):
            if not registry:
                raise ResolverError("Resolver braucht mindestens eine Registry.")
            self._registries: list[Registry] = list(registry)
        else:
            self._registries = [registry]  # type: ignore[list-item]
        # Scope → ``Registry.via``-Marker, der den Scope zuerst bedient hat.
        # Wird pro ``resolve``-Aufruf zurückgesetzt.
        self._scope_owner: dict[str, str] = {}

    @property
    def registries(self) -> list[Registry]:
        return list(self._registries)

    def resolve(self, manifest: ProjectManifest) -> ResolvedGraph:
        initial: dict[str, list[tuple[str, str]]] = {
            spec_id: [(raw_range, "<root>")] for spec_id, raw_range in manifest.dependencies.items()
        }
        targets = manifest.targets if manifest.targets else ()
        target = targets[0] if len(targets) == 1 else ""
        return self._resolve_from_constraints(initial, target=target)

    def resolve_workspace(
        self,
        aggregated_dependencies: dict[str, list[tuple[str, str]]],
    ) -> ResolvedGraph:
        """Phase 3 Stage 5: globale MVS-Auflösung über Workspace-Member.

        ``aggregated_dependencies`` ist die Map aus
        :meth:`speccify_core.workspace.Workspace.aggregated_dependencies` —
        d. h. pro Spec-Id eine Liste ``(range, source)``-Tupel, wobei
        ``source`` der Member-Pfad ist.
        """
        return self._resolve_from_constraints(aggregated_dependencies, target="")

    def _resolve_from_constraints(
        self,
        initial: dict[str, list[tuple[str, str]]],
        *,
        target: str,
    ) -> ResolvedGraph:
        self._scope_owner = {}
        constraints: dict[str, list[_Constraint]] = {}
        for spec_id, items in initial.items():
            for raw_range, source in items:
                constraints.setdefault(spec_id, []).append(
                    _Constraint(spec_id=spec_id, range=Range.parse(raw_range), source=source)
                )

        resolved: dict[str, tuple[Version, Spec]] = {}
        queue: deque[str] = deque(constraints.keys())

        # Pro Spec-Id wird die Registry gemerkt, die sie liefert — damit `fetch`
        # und `Resolution.via` konsistent zur Version-Auswahl bleiben.
        registry_for: dict[str, Registry] = {}

        while queue:
            spec_id = queue.popleft()
            if spec_id not in constraints:
                continue
            registry, chosen = self._select_version_and_registry(spec_id, constraints[spec_id])
            previous = resolved.get(spec_id)
            if previous is not None and previous[0] == chosen:
                continue
            spec = registry.fetch(spec_id, chosen)
            registry_for[spec_id] = registry
            resolved[spec_id] = (chosen, spec)

            # Neue transitive Constraints aus uses: + composition.uses aufnehmen
            # (Kompositions-Kinder sind vollwertige Dependencies, Phase P2).
            data = spec.parsed()
            uses = list(data.get("uses") or [])
            composition_raw = data.get("composition")
            if isinstance(composition_raw, dict):
                composition_uses = composition_raw.get("uses")
                if isinstance(composition_uses, dict):
                    uses.extend(str(ref) for ref in composition_uses.values())
            source = f"{spec_id}@{chosen}"
            changed_ids: set[str] = set()
            for entry in uses:
                if not isinstance(entry, str):
                    continue
                dep_id, range_raw = _parse_uses_entry(entry)
                try:
                    dep_range = Range.parse(range_raw)
                except ResolverError as exc:
                    raise ResolverError(f"Ungültige Range in {source} → {entry}: {exc}") from exc
                bucket = constraints.setdefault(dep_id, [])
                already = any(c.range.raw == dep_range.raw and c.source == source for c in bucket)
                if not already:
                    bucket.append(_Constraint(spec_id=dep_id, range=dep_range, source=source))
                    changed_ids.add(dep_id)

            for changed in changed_ids:
                queue.append(changed)
            # Wenn sich Constraints für bereits aufgelöste Specs ändern, neu evaluieren.
            for cid in list(resolved.keys()):
                if cid in changed_ids:
                    queue.append(cid)

        resolutions = [
            Resolution(
                spec_id=spec_id,
                version=ver,
                spec_sha256=_sha256_hex(spec.raw_bytes),
                via=registry_for[spec_id].via,
            )
            for spec_id, (ver, spec) in sorted(resolved.items())
        ]
        return ResolvedGraph(target=target, resolutions=resolutions)

    # --- intern ---------------------------------------------------------

    def _select_version_and_registry(
        self, spec_id: str, constraints: list[_Constraint]
    ) -> tuple[Registry, Version]:
        """Wählt die erste Registry mit verfügbaren Versionen und liefert das MVS-Maximum.

        Prüft Scope-Registry-Eindeutigkeit: ein Scope, der bereits von Registry A
        bedient wurde, darf in derselben ``resolve``-Runde nicht plötzlich von
        Registry B kommen — andernfalls :class:`ScopeRegistryConflictError`.
        """
        scope = _scope_of(spec_id)
        owner_via = self._scope_owner.get(scope)

        selected_registry: Registry | None = None
        available: list[Version] = []
        for registry in self._registries:
            if owner_via is not None and registry.via != owner_via:
                # Bereits an eine andere Registry gebunden — diese hier überspringen.
                continue
            try:
                versions = registry.list_versions(spec_id)
            except RegistryError as exc:
                raise ResolverError(str(exc)) from exc
            if versions:
                selected_registry = registry
                available = versions
                break

        if selected_registry is None:
            # Wenn der Scope gebunden ist und dort nichts gefunden wurde, aber eine andere
            # Registry liefern *würde*, ist das ein Cross-Registry-Konflikt.
            if owner_via is not None:
                for registry in self._registries:
                    if registry.via == owner_via:
                        continue
                    try:
                        other_versions = registry.list_versions(spec_id)
                    except RegistryError:
                        continue
                    if other_versions:
                        raise ScopeRegistryConflictError(
                            f"Scope '@{scope}' ist bereits an Registry '{owner_via}' "
                            f"gebunden, aber '{registry.via}' liefert ebenfalls eine Spec "
                            f"für '{spec_id}'. Dependency-Confusion-Schutz: ein Scope darf "
                            f"zu genau einer Registry gehören."
                        )
            sources = ", ".join(f"{c.source} ({c.range.raw})" for c in constraints)
            raise VersionNotFoundError(
                f"Keine Versionen für '{spec_id}' im Registry-Set gefunden. "
                f"Geforderte Ranges: {sources}."
            )

        # Cross-Registry-Konflikt: weitere Registries dürfen denselben Scope nicht bedienen.
        for registry in self._registries:
            if registry is selected_registry:
                continue
            if registry.via == selected_registry.via:
                continue
            try:
                other_versions = registry.list_versions(spec_id)
            except RegistryError:
                continue
            if other_versions:
                raise ScopeRegistryConflictError(
                    f"Scope '@{scope}' wird von zwei Registries angeboten: "
                    f"'{selected_registry.via}' und '{registry.via}'. "
                    f"Dependency-Confusion-Schutz: ein Scope darf zu genau einer Registry gehören."
                )

        self._scope_owner[scope] = selected_registry.via
        version = self._pick_version(spec_id, available, constraints)
        return selected_registry, version

    def _pick_version(
        self, spec_id: str, available: list[Version], constraints: list[_Constraint]
    ) -> Version:
        # Pre-Releases sind in Phase 1a per Version.parse bereits ausgeschlossen.
        # ``available`` ist non-empty (Aufrufer hat das geprüft).
        # Maximum aller Mindestversionen.
        min_required = max(c.range.min_version for c in constraints)

        # Kandidaten: alle verfügbaren Versionen, die >= min_required sind und alle Ranges erfüllen.
        candidates = [
            v
            for v in available
            if v >= min_required and all(c.range.contains(v) for c in constraints)
        ]
        if not candidates:
            sources = "; ".join(
                f"{c.source} fordert {c.range.raw} (min {c.range.min_version})" for c in constraints
            )
            avail = ", ".join(str(v) for v in available)
            raise RangeConflictError(
                f"Konnte keine Version für '{spec_id}' finden, die alle Constraints erfüllt. "
                f"{sources}. Verfügbar: [{avail}]."
            )
        # MVS: kleinster Kandidat ab Mindestversion.
        return min(candidates)
