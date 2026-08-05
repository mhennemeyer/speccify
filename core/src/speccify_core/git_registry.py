"""Git-Repos als Spec-Quelle (Phase P5): `GitRegistry` nach dem `Registry`-Protocol.

Vorbild sind Go-Module und SwiftPM, nicht npm: die **Repo-URL ist die
Identität**, **Tags sind die Versionen**, und ein Commit-SHA macht das
Ergebnis reproduzierbar. Es gibt keine zentrale Instanz, die Namen vergibt.

Spec-Id (Entscheidung D16)::

    git+https://github.com/acme/rating-stars            # Spec im Repo-Root
    git+https://github.com/acme/kit#specs/button        # Spec in einem Unterordner

Tags (D17): `v<semver>` ohne Pfad, `<pfad>/v<semver>` mit Pfad — damit lassen
sich beliebig viele Specs in einem Repo unabhängig versionieren.

Cache (D19): pro Repo ein **Bare-Clone** unter `<cache>/<hash>/repo.git`. Tags
kommen per `fetch --depth 1`, die Spec-Bytes per `git cat-file blob <tag>:<pfad>`
— kein Working Tree, kein Checkout. Nach einem Fetch ist alles offline
reproduzierbar; `offline=True` verbietet jeden Netz-Zugriff hart, damit
`verify` und CI ohne Netz laufen.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from speccify_core.registry import RegistryError, Spec, Version

SPEC_FILENAME = "spec.speccify.yaml"
DEFAULT_GIT_CACHE_DIR = Path.home() / ".cache" / "speccify" / "git"
DEFAULT_TIMEOUT = 60.0

_GIT_REF_PATTERN = re.compile(r"^git\+(?P<url>[^\s#]+?)(?:#(?P<path>[^\s#]+))?$")
_ALLOWED_SCHEMES = ("https", "file")
_SEMVER_TAG = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")


class GitRegistryError(RegistryError):
    """Git-Quelle war nicht auflösbar (Ref kaputt, git fehlt, Netz gesperrt)."""


@dataclass(frozen=True)
class GitRef:
    """Zerlegte Git-Spec-Id: Repo-URL + optionaler Pfad im Repo."""

    url: str
    path: str = ""

    @property
    def spec_id(self) -> str:
        return f"git+{self.url}#{self.path}" if self.path else f"git+{self.url}"

    @property
    def spec_path(self) -> str:
        """Pfad der Spec-Datei im Repo."""
        return f"{self.path}/{SPEC_FILENAME}" if self.path else SPEC_FILENAME

    @property
    def tag_prefix(self) -> str:
        """`specs/button/` bei gesetztem Pfad, sonst leer (D17)."""
        return f"{self.path}/" if self.path else ""

    def tag_for(self, version: Version) -> str:
        return f"{self.tag_prefix}v{version}"

    def version_for(self, tag: str) -> Version | None:
        """Version eines Tags — `None`, wenn der Tag nicht zu dieser Spec gehört."""
        if not tag.startswith(self.tag_prefix):
            return None
        match = _SEMVER_TAG.match(tag[len(self.tag_prefix) :])
        if match is None:
            return None
        try:
            return Version.parse(match.group("version"))
        except ValueError:  # pragma: no cover - Regex deckt das ab
            return None


def is_git_ref(spec_id: str) -> bool:
    return spec_id.startswith("git+")


def parse_git_ref(spec_id: str) -> GitRef:
    """`git+https://host/org/repo#pfad` → `GitRef`. Wirft bei kaputten Refs."""
    match = _GIT_REF_PATTERN.match(spec_id)
    if match is None:
        raise GitRegistryError(
            f"Ungültige Git-Spec-Id '{spec_id}': erwartet 'git+<url>[#<pfad-im-repo>]'."
        )
    url = match.group("url").rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise GitRegistryError(
            f"Git-Spec-Id '{spec_id}': Schema '{parsed.scheme or '∅'}' wird nicht unterstützt "
            f"(erlaubt: {', '.join(_ALLOWED_SCHEMES)})."
        )
    path = (match.group("path") or "").strip("/")
    if path.startswith("..") or "/../" in path:
        raise GitRegistryError(f"Git-Spec-Id '{spec_id}': Pfad darf nicht aus dem Repo zeigen.")
    return GitRef(url=url, path=path)


class GitRepoCache:
    """Bare-Clone-Cache für Git-Remotes — geteilt von Spec-Quellen und Index-Repos.

    Kapselt das komplette git-Plumbing: ein Bare-Repo pro Remote-URL, Fetch nur
    wenn nötig, Lesen ausschließlich über `cat-file`/`ls-tree`. Kein Working
    Tree, kein Checkout, kein interaktives Credential-Prompting.
    """

    def __init__(
        self,
        *,
        cache_dir: Path | str | None = None,
        offline: bool = False,
        git_binary: str = "git",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_GIT_CACHE_DIR
        self._offline = offline
        self._git = git_binary
        self._timeout = timeout
        self._fetched: set[tuple[str, str]] = set()

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    @property
    def offline(self) -> bool:
        return self._offline

    def run_bytes(self, args: list[str], *, cwd: Path | None = None) -> bytes:
        """Ruft git auf und liefert rohe stdout-Bytes (Hashes müssen exakt bleiben)."""
        if shutil.which(self._git) is None:
            raise GitRegistryError(
                f"`{self._git}` ist nicht im PATH — Git-Quellen brauchen ein installiertes git."
            )
        try:
            proc = subprocess.run(
                [self._git, *args],
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                timeout=self._timeout,
                # Kein interaktives Credential-Prompting: ein privates Repo soll
                # mit einer Fehlermeldung abbrechen, nicht die CI blockieren.
                env={"GIT_TERMINAL_PROMPT": "0", "PATH": os.environ.get("PATH", "")},
            )
        except subprocess.TimeoutExpired as exc:
            raise GitRegistryError(f"git {' '.join(args)}: Timeout nach {exc.timeout}s.") from exc
        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", "replace").strip()
            raise GitRegistryError(
                f"git {' '.join(args)} fehlgeschlagen (rc={proc.returncode}): {detail}"
            )
        return proc.stdout

    def run(self, args: list[str], *, cwd: Path | None = None) -> str:
        return self.run_bytes(args, cwd=cwd).decode("utf-8", "replace")

    def repo_dir(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        # Lesbarer Präfix + Hash: im Cache-Verzeichnis erkennt man das Repo wieder,
        # der Hash hält die Zuordnung eindeutig.
        name = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git") or "repo"
        return self._cache_dir / f"{name}-{digest}" / "repo.git"

    def ensure(self, url: str, *, refspec: str, label: str | None = None) -> Path:
        """Legt den Bare-Clone an (falls nötig) und holt `refspec` einmal pro Lauf."""
        repo = self.repo_dir(url)
        what = label or url
        if not repo.is_dir():
            if self._offline:
                raise GitRegistryError(
                    f"{what}: kein Cache unter {repo} und offline=True — "
                    f"einmal online auflösen oder Cache mitliefern."
                )
            repo.parent.mkdir(parents=True, exist_ok=True)
            self.run(["init", "--bare", "--quiet", str(repo)])
            self.run(["remote", "add", "origin", url], cwd=repo)
        if not self._offline and (url, refspec) not in self._fetched:
            self.run(["fetch", "--quiet", "--depth", "1", "--force", "origin", refspec], cwd=repo)
            self._fetched.add((url, refspec))
        return repo


class GitRegistry:
    """Registry-Protocol-Implementierung über Git-Tags.

    `via` ist bewusst der konstante Marker `"git"` — die Repo-URL steckt bereits
    in der Spec-Id, das Lockfile verliert also nichts.
    """

    def __init__(
        self,
        *,
        cache_dir: Path | str | None = None,
        offline: bool = False,
        git_binary: str = "git",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._cache = GitRepoCache(
            cache_dir=cache_dir, offline=offline, git_binary=git_binary, timeout=timeout
        )

    @property
    def via(self) -> str:
        return "git"

    @property
    def cache(self) -> GitRepoCache:
        return self._cache

    @property
    def cache_dir(self) -> Path:
        return self._cache.cache_dir

    @property
    def offline(self) -> bool:
        return self._cache.offline

    def serves(self, spec_id: str) -> bool:
        """Nur `git+`-Ids — alles andere bedienen Local-/RemoteRegistry."""
        return is_git_ref(spec_id)

    def _repo(self, ref: GitRef) -> Path:
        """Bare-Clone des Repos, Tags aktuell (bzw. nur lokal, wenn offline)."""
        return self._cache.ensure(ref.url, refspec="+refs/tags/*:refs/tags/*", label=ref.spec_id)

    def _run(self, args: list[str], *, cwd: Path) -> str:
        return self._cache.run(args, cwd=cwd)

    # --- Registry-Protocol ----------------------------------------------------

    def list_versions(self, spec_id: str) -> list[Version]:
        """Alle Semver-Tags, die zu dieser Spec-Id gehören (aufsteigend sortiert)."""
        ref = parse_git_ref(spec_id)
        repo = self._repo(ref)
        versions: list[Version] = []
        for tag in self._run(["tag", "--list"], cwd=repo).splitlines():
            version = ref.version_for(tag.strip())
            if version is not None:
                versions.append(version)
        return sorted(set(versions))

    def fetch(self, spec_id: str, version: Version) -> Spec:
        """Liest die Spec-Bytes am passenden Tag — ohne Working Tree."""
        ref = parse_git_ref(spec_id)
        repo = self._repo(ref)
        tag = ref.tag_for(version)
        try:
            commit = self._run(["rev-parse", f"{tag}^{{commit}}"], cwd=repo).strip()
        except GitRegistryError as exc:
            available = ", ".join(str(v) for v in self.list_versions(spec_id)) or "keine"
            raise GitRegistryError(
                f"{spec_id}: Tag '{tag}' existiert nicht (verfügbar: {available})."
            ) from exc
        try:
            blob = self._cache.run_bytes(["cat-file", "blob", f"{tag}:{ref.spec_path}"], cwd=repo)
        except GitRegistryError as exc:
            raise GitRegistryError(
                f"{spec_id}: '{ref.spec_path}' fehlt im Repo bei Tag '{tag}'."
            ) from exc
        return Spec(
            spec_id=spec_id,
            version=version,
            raw_bytes=blob,
            path=Path(f"{ref.url}@{tag}:{ref.spec_path}"),
            source_commit=commit,
        )

    def resolve_commit(self, spec_id: str, version: Version) -> str:
        """Commit-SHA hinter dem Tag — der Pin fürs Lockfile (D18)."""
        ref = parse_git_ref(spec_id)
        repo = self._repo(ref)
        return self._run(["rev-parse", f"{ref.tag_for(version)}^{{commit}}"], cwd=repo).strip()


__all__ = [
    "DEFAULT_GIT_CACHE_DIR",
    "GitRepoCache",
    "SPEC_FILENAME",
    "GitRef",
    "GitRegistry",
    "GitRegistryError",
    "is_git_ref",
    "parse_git_ref",
]
