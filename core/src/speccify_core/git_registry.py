"""Git repositories as playbook sources: `GitLibrary`.

Modelled on Go modules and SwiftPM, not npm: the **repository URL is the
identity**, **tags are the versions**, and a commit SHA makes a resolution
reproducible. Nobody hands out names centrally.

Playbook id::

    git+https://github.com/acme/iap-trial            # bundle at the repo root
    git+https://github.com/acme/kit#playbooks/iap    # bundle in a subdirectory

Tags: `v<semver>` without a path, `<path>/v<semver>` with one — so a monorepo
can version any number of playbooks independently.

Cache: one **bare clone** per repository under `<cache>/<hash>/repo.git`. Tags
arrive via `fetch --depth 1`, bundle files via `ls-tree` + `cat-file` — no
working tree, no checkout. After one fetch everything is readable offline;
`offline=True` forbids network access outright so CI stays hermetic.
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

from speccify_core.registry import Bundle, LibraryError, Version
from speccify_core.skill import BUNDLE_DIRS, SKILL_FILENAME

DEFAULT_GIT_CACHE_DIR = Path.home() / ".cache" / "speccify" / "git"
DEFAULT_TIMEOUT = 60.0

_GIT_REF_PATTERN = re.compile(r"^git\+(?P<url>[^\s#]+?)(?:#(?P<path>[^\s#]+))?$")
_ALLOWED_SCHEMES = ("https", "file")
_SEMVER_TAG = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")


class GitLibraryError(LibraryError):
    """A git source could not be resolved (bad ref, git missing, network blocked)."""


# Older vocabulary, same error.
GitRegistryError = GitLibraryError


@dataclass(frozen=True)
class GitRef:
    """A parsed git playbook id: repository URL plus optional path inside it."""

    url: str
    path: str = ""

    @property
    def playbook_id(self) -> str:
        return f"git+{self.url}#{self.path}" if self.path else f"git+{self.url}"

    @property
    def bundle_prefix(self) -> str:
        """Path prefix of the bundle inside the repository (empty at the root)."""
        return f"{self.path}/" if self.path else ""

    @property
    def skill_path(self) -> str:
        return f"{self.bundle_prefix}{SKILL_FILENAME}"

    @property
    def tag_prefix(self) -> str:
        """`playbooks/iap/` when a path is set, empty otherwise."""
        return f"{self.path}/" if self.path else ""

    def tag_for(self, version: Version) -> str:
        return f"{self.tag_prefix}v{version}"

    def version_for(self, tag: str) -> Version | None:
        """The version a tag encodes — `None` when the tag belongs to another playbook."""
        if not tag.startswith(self.tag_prefix):
            return None
        match = _SEMVER_TAG.match(tag[len(self.tag_prefix) :])
        if match is None:
            return None
        try:
            return Version.parse(match.group("version"))
        except ValueError:  # pragma: no cover - Regex deckt das ab
            return None


def is_git_ref(playbook_id: str) -> bool:
    return playbook_id.startswith("git+")


def parse_git_ref(playbook_id: str) -> GitRef:
    """`git+https://host/org/repo#path` -> `GitRef`; raises on malformed refs."""
    match = _GIT_REF_PATTERN.match(playbook_id)
    if match is None:
        raise GitLibraryError(
            f"Ungültige Git-Spec-Id '{playbook_id}': erwartet 'git+<url>[#<pfad-im-repo>]'."
        )
    url = match.group("url").rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise GitLibraryError(
            f"Git-Spec-Id '{playbook_id}': Schema '{parsed.scheme or '∅'}' wird nicht unterstützt "
            f"(erlaubt: {', '.join(_ALLOWED_SCHEMES)})."
        )
    path = (match.group("path") or "").strip("/")
    if path.startswith("..") or "/../" in path:
        raise GitLibraryError(f"Git-Spec-Id '{playbook_id}': Pfad darf nicht aus dem Repo zeigen.")
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
            raise GitLibraryError(
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
            raise GitLibraryError(f"git {' '.join(args)}: Timeout nach {exc.timeout}s.") from exc
        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", "replace").strip()
            raise GitLibraryError(
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
                raise GitLibraryError(
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


class GitLibrary:
    """`Library` implementation backed by git tags.

    `via` is the constant marker `"git"` on purpose — the repository URL is
    already part of the playbook id, so the lockfile loses nothing.
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

    def serves(self, playbook_id: str) -> bool:
        """Only `git+` ids — everything else belongs to the local library."""
        return is_git_ref(playbook_id)

    def _repo(self, ref: GitRef) -> Path:
        """Bare-Clone des Repos, Tags aktuell (bzw. nur lokal, wenn offline)."""
        return self._cache.ensure(
            ref.url, refspec="+refs/tags/*:refs/tags/*", label=ref.playbook_id
        )

    def _run(self, args: list[str], *, cwd: Path) -> str:
        return self._cache.run(args, cwd=cwd)

    # --- Registry-Protocol ----------------------------------------------------

    def list_versions(self, playbook_id: str) -> list[Version]:
        """Every semver tag belonging to this playbook id, ascending."""
        ref = parse_git_ref(playbook_id)
        repo = self._repo(ref)
        versions: list[Version] = []
        for tag in self._run(["tag", "--list"], cwd=repo).splitlines():
            version = ref.version_for(tag.strip())
            if version is not None:
                versions.append(version)
        return sorted(set(versions))

    def fetch(self, playbook_id: str, version: Version) -> Bundle:
        """Read the whole bundle at the matching tag — no working tree involved."""
        ref = parse_git_ref(playbook_id)
        repo = self._repo(ref)
        tag = ref.tag_for(version)
        try:
            commit = self._run(["rev-parse", f"{tag}^{{commit}}"], cwd=repo).strip()
        except GitLibraryError as exc:
            available = ", ".join(str(v) for v in self.list_versions(playbook_id)) or "none"
            raise GitLibraryError(
                f"{playbook_id}: tag '{tag}' does not exist (available: {available})."
            ) from exc

        files: dict[str, bytes] = {}
        try:
            files[SKILL_FILENAME] = self._cache.run_bytes(
                ["cat-file", "blob", f"{tag}:{ref.skill_path}"], cwd=repo
            )
        except GitLibraryError as exc:
            raise GitLibraryError(
                f"{playbook_id}: '{ref.skill_path}' is missing at tag '{tag}'."
            ) from exc

        # Bundled directories are optional; an empty tree simply lists nothing.
        # The spec names three conventions, Speccify adds `tools/`; a skill
        # may use any or none.
        for directory in BUNDLE_DIRS:
            listing = self._run(
                ["ls-tree", "-r", "--name-only", tag, f"{ref.bundle_prefix}{directory}/"],
                cwd=repo,
            )
            for line in listing.splitlines():
                path = line.strip()
                if not path:
                    continue
                files[path[len(ref.bundle_prefix) :]] = self._cache.run_bytes(
                    ["cat-file", "blob", f"{tag}:{path}"], cwd=repo
                )

        return Bundle(
            source_id=playbook_id,
            version=version,
            files=files,
            origin=f"{ref.url}@{tag}",
            source_commit=commit,
        )

    def resolve_commit(self, playbook_id: str, version: Version) -> str:
        """The commit behind the tag — what the lockfile pins."""
        ref = parse_git_ref(playbook_id)
        repo = self._repo(ref)
        return self._run(["rev-parse", f"{ref.tag_for(version)}^{{commit}}"], cwd=repo).strip()


# Older vocabulary, same class.
GitRegistry = GitLibrary


__all__ = [
    "DEFAULT_GIT_CACHE_DIR",
    "GitRepoCache",
    "GitRef",
    "GitLibrary",
    "GitRegistry",
    "GitLibraryError",
    "is_git_ref",
    "parse_git_ref",
]
