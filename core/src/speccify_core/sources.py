"""Skill sources: where a project's skills come from, by location.

A source is a **git URL or a directory**. The manifest lists them under
`sources:`; the app keeps the same list per project and a global one. Git
sources are not cloned here — the desktop app (or the user) clones them once
into `~/.speccify/sources/<slug>/` and keeps them fresh with `git pull`; the
core only needs to find that checkout, which is why the slug is computed
identically on both sides (`apps/desktop/src-tauri/src/sources_cmd.rs`).
A checkout is treated like any local library: ids and versions come from
`SKILL.md` metadata, no tags needed.
"""

from __future__ import annotations

import os
from pathlib import Path

from speccify_core.registry import LibraryError

SOURCES_DIRNAME = "sources"
_URL_PREFIXES = ("http://", "https://", "ssh://", "git://", "git@", "file://", "git+")


class SourceUnavailable(LibraryError):
    """The source is known but not on disk — not cloned yet, or the directory is gone."""


def is_git_location(location: str) -> bool:
    """Git URL or directory? Decided by scheme or `.git` suffix, like the app does."""
    s = location.strip()
    return s.startswith(_URL_PREFIXES) or s.endswith(".git")


def plain_url(location: str) -> str:
    s = location.strip()
    return s[4:] if s.startswith("git+") else s


def display_name(location: str) -> str:
    """Last path segment without `.git` — `skills` for `…/acme/skills.git`."""
    s = plain_url(location).rstrip("/")
    last = s.replace(":", "/").rsplit("/", 1)[-1]
    name = last[:-4] if last.endswith(".git") else last
    return name or s


def slug(location: str) -> str:
    """Stable checkout directory name: host + path, everything else `-`.

    Must match the Rust side: `https://github.com/acme/Skills.git` →
    `github.com-acme-skills`, `git@gitlab.example:team/x.git` →
    `gitlab.example-team-x`.
    """
    s = plain_url(location)
    for prefix in ("https://", "http://", "ssh://", "git://", "file://", "git@"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    if s.endswith(".git"):
        s = s[:-4]
    out: list[str] = []
    dash = False
    for ch in s:
        if ch.isascii() and (ch.isalnum() or ch == "."):
            out.append(ch.lower())
            dash = False
        elif not dash:
            out.append("-")
            dash = True
    return "".join(out).strip("-")


def home_dir() -> Path:
    raw = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    return Path(raw) if raw else Path.home()


def checkout_dir(location: str) -> Path:
    return home_dir() / ".speccify" / SOURCES_DIRNAME / slug(location)


def resolve_source(location: str, base: Path | None = None) -> Path:
    """The directory holding a source's skills, without touching the network.

    Git: the managed checkout — `SourceUnavailable` if it was never cloned.
    Directory: relative to `base` (the manifest's directory), `~` expanded.
    """
    if is_git_location(location):
        directory = checkout_dir(location)
        if not (directory / ".git").exists():
            raise SourceUnavailable(
                f"Source {location.strip()} is not cloned yet — add it in the app "
                f"(Library, or the project's skills tab), or clone it to {directory}."
            )
        return directory
    raw = location.strip()
    path = Path(os.path.expanduser(raw))
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    path = path.resolve()
    if not path.is_dir():
        raise SourceUnavailable(f"Source directory does not exist: {path}")
    return path


__all__ = [
    "SOURCES_DIRNAME",
    "SourceUnavailable",
    "checkout_dir",
    "display_name",
    "is_git_location",
    "plain_url",
    "resolve_source",
    "slug",
]
