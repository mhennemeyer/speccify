"""A directory of skills, behind the same `Library` protocol as everything else.

Layout is what a skills repository actually looks like — one directory per
skill, no version segment, optionally grouped in folders (the folder
structure is the repository's organisation, the app shows it as categories;
`speccify export --category` writes into it):

    <root>/<name>/SKILL.md
    <root>/<name>/assets/…
    <root>/<category>/<sub>/<name>/SKILL.md

Two consequences follow from the format rather than from taste:

* **The version lives in the file, not in the path.** `metadata.speccify.version`
  is the working copy's version; other versions come from git tags, the way Go
  modules do it. A local library therefore offers exactly one version of a
  skill — the one on disk.
* **There is no scope directory.** `name` is what Claude Code looks up, and it
  looks in `<skills-root>/<name>/SKILL.md`. Speccify's `@scope/name` id lives
  in `metadata.speccify.scope`, so the same directory serves both.

Because this satisfies `Library`, the manifest, lockfile, resolver, bundle
hashing and git sources keep working untouched — none of them ever cared what
was inside a bundle.
"""

from __future__ import annotations

from pathlib import Path

from speccify_core.registry import Bundle, LibraryError, Version, split_id
from speccify_core.skill import SKILL_FILENAME, SkillError, parse_skill


class LocalSkillLibrary:
    """Directory-backed skill library (read-only)."""

    def __init__(self, root: str | Path, *, via: str | None = None) -> None:
        self._root = Path(root)
        if not self._root.exists():
            raise LibraryError(f"Skill library does not exist: {self._root}")
        if not self._root.is_dir():
            raise LibraryError(f"Skill library is not a directory: {self._root}")
        self._via = via if via is not None else "local"

    @property
    def root(self) -> Path:
        return self._root

    @property
    def via(self) -> str:
        return self._via

    def serves(self, playbook_id: str) -> bool:
        """Anything that is not a git source — a bare name or `@scope/name`."""
        return not playbook_id.startswith("git+")

    # --- Lookup ---------------------------------------------------------------

    def _directory(self, playbook_id: str) -> Path | None:
        """`@scope/name` and a bare `name` both resolve to a `<name>/SKILL.md` here.

        `<root>/<name>` wins; otherwise the first (sorted) `<name>` in any
        category folder.
        """
        name = split_id(playbook_id)[1] if "/" in playbook_id else playbook_id.lstrip("@")
        directory = self._root / name
        if (directory / SKILL_FILENAME).is_file():
            return directory
        for candidate in self._skill_directories():
            if candidate.name == name:
                return candidate
        return None

    def _skill_directories(self, directory: Path | None = None, depth: int = 0) -> list[Path]:
        """Every skill directory below the root, sorted; bundles are not descended into."""
        directory = directory or self._root
        found: list[Path] = []
        if depth > 6:
            return found
        for child in sorted(p for p in directory.iterdir() if p.is_dir()):
            if child.name.startswith(".") or child.name in ("node_modules", "target"):
                continue
            if (child / SKILL_FILENAME).is_file():
                found.append(child)
                continue
            found.extend(self._skill_directories(child, depth + 1))
        return found

    def _version_of(self, directory: Path) -> Version | None:
        try:
            skill = parse_skill((directory / SKILL_FILENAME).read_text(encoding="utf-8"))
        except (SkillError, OSError):
            return None
        raw = skill.version
        if not raw:
            # A skill without a version is still a usable skill; it simply
            # cannot be pinned. `0.0.0` keeps the resolver working and makes
            # the omission visible in the lockfile.
            return Version.parse("0.0.0")
        try:
            return Version.parse(raw)
        except ValueError:
            return None

    def list_versions(self, playbook_id: str) -> list[Version]:
        directory = self._directory(playbook_id)
        if directory is None:
            return []
        version = self._version_of(directory)
        return [version] if version is not None else []

    def list_playbooks(self) -> list[tuple[str, Version]]:
        """Every skill here, sorted — used by `search` and the viewer."""
        found: list[tuple[str, Version]] = []
        for directory in self._skill_directories():
            version = self._version_of(directory)
            if version is None:
                continue
            skill = parse_skill((directory / SKILL_FILENAME).read_text(encoding="utf-8"))
            found.append((skill.qualified_id, version))
        return found

    # Kept for symmetry with the older library; the name is the odd one out now.
    list_skills = list_playbooks

    def fetch(self, playbook_id: str, version: Version) -> Bundle:
        directory = self._directory(playbook_id)
        if directory is None:
            raise LibraryError(f"Skill '{playbook_id}' not found in {self._root}.")
        available = self._version_of(directory)
        if available != version:
            raise LibraryError(
                f"Skill '{playbook_id}@{version}' not found in {self._root}. "
                f"Available: {available or 'none'}."
            )
        files: dict[str, bytes] = {}
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                files[path.relative_to(directory).as_posix()] = path.read_bytes()
        return Bundle(
            source_id=playbook_id,
            version=version,
            files=files,
            origin=str(directory),
        )


__all__ = ["LocalSkillLibrary"]
