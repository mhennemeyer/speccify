"""Lokale Pseudo-Registry für Phase 1a.

Layout: `<root>/<scope>/<name>/<version>/spec.speccify.yaml`. Spec-IDs sind in der Form
`@<scope>/<name>` erwartet (siehe Manifest-Schema). `spec://`-IDs werden in 1a nicht
verwendet, weil das lokale Registry-Layout zwingend einen Scope braucht.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable
from urllib.parse import urlparse

import httpx
import yaml

_SPEC_FILENAME = "spec.speccify.yaml"
_SCOPED_ID_PATTERN = re.compile(r"^@([a-z0-9][a-z0-9-]*)/([a-z0-9][a-z0-9-]*)$")
_SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class RegistryError(Exception):
    """Registry-Lookup ist fehlgeschlagen (Spec/Version fehlt, Layout kaputt)."""


@dataclass(frozen=True, order=True)
class Version:
    """Semver-Version (Phase 1a: nur major.minor.patch, ohne Pre-Release/Build)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, raw: str) -> Version:
        match = _SEMVER_PATTERN.match(raw)
        if not match:
            raise ValueError(
                f"Ungültige Version '{raw}': Phase 1a erlaubt nur major.minor.patch ohne Suffix."
            )
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class Spec:
    """Geladene Spec inkl. Original-Bytes (für stabile Hashes) und Pfad."""

    spec_id: str
    version: Version
    raw_bytes: bytes
    path: Path
    # Nur bei Git-Quellen (Phase P5) gesetzt: der Commit hinter dem Tag —
    # der Pin, den das Lockfile festhält (Entscheidung D18).
    source_commit: str | None = None

    def parsed(self) -> dict:
        """Lazy parse: PyYAML auf den Original-Bytes."""
        return yaml.safe_load(self.raw_bytes.decode("utf-8")) or {}

    @property
    def name_id(self) -> str:
        """Die **in der Spec deklarierte** Id — Grundlage für Namen und Pfade im Codegen.

        Für Registry-Specs ist das dieselbe Id wie `spec_id`. Bei Git-Quellen
        (Phase P5) ist `spec_id` die Quelle (`git+<url>#<pfad>`), während die
        Spec selbst weiterhin `@scope/name` heißt — generierte Dateien sollen
        nach der Komponente heißen, nicht nach ihrem Fundort. Die Herkunft
        hält das Lockfile fest.
        """
        declared = str(self.parsed().get("id", "")).strip()
        if not declared:
            return self.spec_id
        # Optionales `@<version>`-Suffix aus der Id entfernen (`@org/button@0.1.0`).
        match = re.match(r"^(?P<id>spec://[^@]+|@[^/]+/[^@]+)(?:@.+)?$", declared)
        return match.group("id") if match else declared


@runtime_checkable
class Registry(Protocol):
    """Gemeinsames Protokoll für lokale (`LocalRegistry`) und remote (`RemoteRegistry`)
    Spec-Quellen. Stage 6 (Phase 2) führt es ein, damit der Resolver eine Liste
    heterogener Registries gleichmäßig verarbeiten kann.

    Implementierungen müssen ``via`` als stabile, im Lockfile speicherbare Quell-Id
    bereitstellen (lokaler Pfad oder absolute URL). Der Resolver schreibt diesen Wert
    in ``LockEntry.resolved_via``.
    """

    @property
    def via(self) -> str: ...

    def list_versions(self, spec_id: str) -> list[Version]: ...

    def fetch(self, spec_id: str, version: Version) -> Spec: ...


class LocalRegistry:
    """Verzeichnis-basierte Pseudo-Registry. Read-only in Phase 1a.

    Der Stage-6-Multi-Registry-Refactor hat ``via`` als Lockfile-Quell-Id eingeführt;
    für lokale Registries bleibt der stabile Default-Marker ``"registry-fixtures"``
    erhalten (damit existierende Lockfile-Snapshots aus Phase 1 weiter passen).
    Wer eine mehrdeutige Multi-Registry-Konfiguration baut, kann beim Konstruktor
    ein eigenes ``via`` mitgeben.
    """

    def __init__(self, root: str | Path, *, via: str | None = None) -> None:
        self._root = Path(root)
        if not self._root.exists():
            raise RegistryError(f"Registry-Pfad existiert nicht: {self._root}")
        if not self._root.is_dir():
            raise RegistryError(f"Registry-Pfad ist kein Verzeichnis: {self._root}")
        self._via = via if via is not None else "registry-fixtures"

    @property
    def root(self) -> Path:
        return self._root

    @property
    def via(self) -> str:
        return self._via

    def serves(self, spec_id: str) -> bool:
        """Nur scoped Ids (`@scope/name`) — Git-Quellen bedient die `GitRegistry`."""
        return bool(_SCOPED_ID_PATTERN.match(spec_id))

    def list_versions(self, spec_id: str) -> list[Version]:
        """Sortiert aufsteigend; ignoriert Verzeichnisse mit ungültiger Version."""
        scope, name = _split_id(spec_id)
        spec_dir = self._root / scope / name
        if not spec_dir.is_dir():
            return []
        versions: list[Version] = []
        for entry in spec_dir.iterdir():
            if not entry.is_dir():
                continue
            if not (entry / _SPEC_FILENAME).is_file():
                continue
            try:
                versions.append(Version.parse(entry.name))
            except ValueError:
                continue
        return sorted(versions)

    def fetch(self, spec_id: str, version: Version) -> Spec:
        scope, name = _split_id(spec_id)
        spec_path = self._root / scope / name / str(version) / _SPEC_FILENAME
        if not spec_path.is_file():
            available = self.list_versions(spec_id)
            raise RegistryError(
                f"Spec '{spec_id}@{version}' nicht in Registry {self._root} gefunden. "
                f"Verfügbare Versionen: {[str(v) for v in available] or '∅'}."
            )
        raw = spec_path.read_bytes()
        return Spec(spec_id=spec_id, version=version, raw_bytes=raw, path=spec_path)


def _split_id(spec_id: str) -> tuple[str, str]:
    match = _SCOPED_ID_PATTERN.match(spec_id)
    if not match:
        raise RegistryError(
            f"Spec-Id '{spec_id}' ist nicht im erwarteten Format '@scope/name' "
            f"(Phase 1a unterstützt nur scoped IDs in der lokalen Registry)."
        )
    return match.group(1), match.group(2)


class RemoteRegistry:
    """HTTP-Client gegen ein Speccify-Registry-Backend (Phase 2 Stage 6).

    Spricht mit der REST-API unter ``/api/v1/registry/specs/<scope>/<name>`` und
    ``/api/v1/registry/specs/<scope>/<name>/<version>`` (siehe ``registry/`` Backend).

    Caching: Erfolgreich gefetchte Specs werden unter
    ``<cache_dir>/<host>/<scope>/<name>/<version>/spec.speccify.yaml`` gespiegelt;
    bei späteren Fetches wird der Cache **ohne** Netz-Roundtrip benutzt — das hält
    ``speccify verify`` offline-reproduzierbar, wie in den Non-Functional Requirements
    von Phase 2 verlangt.

    Hash-Konsistenz: Beim Fetch wird der vom Server gelieferte ``sha256`` mit dem
    sha256 der heruntergeladenen Bytes verglichen — Mismatch ist ein harter
    ``RegistryError`` (möglicher MITM oder Server-Bug).

    ``yanked`` Versionen werden in ``list_versions`` **nicht** ausgeblendet —
    das Lockfile-/`verify`-System (Stage 5) markiert sie eigenständig und ein
    bereits gelocktes Set soll auch nach einem Yank reproduzierbar bleiben.
    """

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        cache_dir: Path | str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        if not base_url:
            raise RegistryError("RemoteRegistry braucht eine non-empty base_url.")
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https"):
            raise RegistryError(f"RemoteRegistry base_url muss http(s) sein, war: {base_url!r}.")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._owned_client = client is None
        self._client = client or httpx.Client(timeout=timeout)
        # Host für Cache-Layout (z.B. ``registry.speccify.io_443``).
        host = parsed.hostname or "unknown"
        port_suffix = f"_{parsed.port}" if parsed.port else ""
        self._host_dir = f"{host}{port_suffix}"

    @property
    def via(self) -> str:
        """Lockfile-Quell-Identifier: die Basis-URL der Remote-Registry."""
        return self._base_url

    @property
    def base_url(self) -> str:
        return self._base_url

    def serves(self, spec_id: str) -> bool:
        """Nur scoped Ids (`@scope/name`) — Git-Quellen bedient die `GitRegistry`."""
        return bool(_SCOPED_ID_PATTERN.match(spec_id))

    def close(self) -> None:
        if self._owned_client:
            self._client.close()

    def __enter__(self) -> RemoteRegistry:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # --- Lookup --------------------------------------------------------

    def list_versions(self, spec_id: str) -> list[Version]:
        scope, name = _split_id(spec_id)
        url = f"{self._base_url}/api/v1/registry/specs/{scope}/{name}"
        try:
            resp = self._client.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise RegistryError(
                f"Netzwerk-Fehler beim list_versions({spec_id}) gegen {url}: {exc}"
            ) from exc
        if resp.status_code == 404:
            return []
        if resp.status_code != 200:
            raise RegistryError(
                f"Unerwarteter Status {resp.status_code} bei list_versions({spec_id}) "
                f"gegen {url}: {resp.text[:200]}"
            )
        data = resp.json()
        versions: list[Version] = []
        for v in data.get("versions") or []:
            raw = v.get("version") if isinstance(v, dict) else None
            if not isinstance(raw, str):
                continue
            try:
                versions.append(Version.parse(raw))
            except ValueError:
                # Pre-Releases / non-SemVer werden konsistent mit LocalRegistry ignoriert.
                continue
        return sorted(versions)

    def fetch(self, spec_id: str, version: Version) -> Spec:
        scope, name = _split_id(spec_id)
        cached = self._read_cache(scope, name, version)
        if cached is not None:
            raw, cache_path = cached
            return Spec(spec_id=spec_id, version=version, raw_bytes=raw, path=cache_path)

        url = f"{self._base_url}/api/v1/registry/specs/{scope}/{name}/{version}"
        try:
            resp = self._client.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise RegistryError(
                f"Netzwerk-Fehler beim fetch({spec_id}@{version}) gegen {url}: {exc}"
            ) from exc
        if resp.status_code == 404:
            raise RegistryError(
                f"Spec '{spec_id}@{version}' nicht in Registry {self._base_url} gefunden."
            )
        if resp.status_code != 200:
            raise RegistryError(
                f"Unerwarteter Status {resp.status_code} bei fetch({spec_id}@{version}) "
                f"gegen {url}: {resp.text[:200]}"
            )
        payload = resp.json()
        yaml_str = payload.get("yaml")
        server_sha = payload.get("sha256")
        if not isinstance(yaml_str, str) or not isinstance(server_sha, str):
            raise RegistryError(f"Antwort von {url} fehlt ``yaml`` oder ``sha256``: {payload!r}")
        raw = yaml_str.encode("utf-8")
        local_sha = hashlib.sha256(raw).hexdigest()
        # Server liefert hex-Digest ohne ``sha256:``-Präfix (siehe registry/api).
        if local_sha != server_sha:
            raise RegistryError(
                f"sha256-Mismatch beim Fetch von {spec_id}@{version}: "
                f"Server={server_sha}, lokal={local_sha}."
            )
        cache_path = self._write_cache(scope, name, version, raw)
        return Spec(
            spec_id=spec_id,
            version=version,
            raw_bytes=raw,
            path=cache_path if cache_path is not None else Path(url),
        )

    # --- intern --------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _cache_path(self, scope: str, name: str, version: Version) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / self._host_dir / scope / name / str(version) / _SPEC_FILENAME

    def _read_cache(self, scope: str, name: str, version: Version) -> tuple[bytes, Path] | None:
        p = self._cache_path(scope, name, version)
        if p is None or not p.is_file():
            return None
        return p.read_bytes(), p

    def _write_cache(self, scope: str, name: str, version: Version, raw: bytes) -> Path | None:
        p = self._cache_path(scope, name, version)
        if p is None:
            return None
        p.parent.mkdir(parents=True, exist_ok=True)
        # Atomarer Write via temp file in selbem Verzeichnis.
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(raw)
        tmp.replace(p)
        return p
