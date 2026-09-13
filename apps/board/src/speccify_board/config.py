"""Board configuration: one YAML file names the repositories that belong together."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


class ConfigError(Exception):
    """The configuration file is missing or invalid."""


@dataclass(frozen=True)
class RepoConfig:
    name: str
    url: str | None = None
    path: Path | None = None
    branch: str = "specs"

    @property
    def is_remote(self) -> bool:
        return self.url is not None


@dataclass(frozen=True)
class BoardConfig:
    title: str = "Speccify"
    refresh_seconds: int = 60
    author_name: str = "Speccify Board"
    author_email: str = "board@speccify.local"
    repos: tuple[RepoConfig, ...] = field(default_factory=tuple)

    @property
    def names(self) -> list[str]:
        return [repo.name for repo in self.repos]


def _expand_env(value: str) -> str:
    """`${GIT_TOKEN}` from the environment; unset variables stay literal."""

    def replace(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), match.group(0))

    return _ENV_RE.sub(replace, value)


def parse_config(text: str, *, base_dir: Path | None = None) -> BoardConfig:
    raw = yaml.safe_load(text) or {}
    if not isinstance(raw, dict):
        raise ConfigError("Konfiguration muss ein Mapping sein.")
    repos: list[RepoConfig] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw.get("repos") or []):
        if not isinstance(entry, dict):
            raise ConfigError(f"repos[{index}] muss ein Mapping sein.")
        name = str(entry.get("name") or "").strip()
        url = entry.get("url")
        path = entry.get("path")
        if not name:
            raise ConfigError(f"repos[{index}]: `name` fehlt.")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
            raise ConfigError(
                f"repos[{index}]: `name` darf nur Buchstaben, Ziffern, . _ - enthalten."
            )
        if name in seen:
            raise ConfigError(f"repos: `{name}` doppelt.")
        if bool(url) == bool(path):
            raise ConfigError(f"repos[{index}] ({name}): genau eines von `url` oder `path`.")
        seen.add(name)
        resolved_path: Path | None = None
        if path:
            resolved_path = Path(_expand_env(str(path))).expanduser()
            if not resolved_path.is_absolute() and base_dir is not None:
                resolved_path = (base_dir / resolved_path).resolve()
        repos.append(
            RepoConfig(
                name=name,
                url=_expand_env(str(url)) if url else None,
                path=resolved_path,
                branch=str(entry.get("branch") or "specs"),
            )
        )
    author = raw.get("author") or {}
    if isinstance(author, str):
        match = re.fullmatch(r"\s*(.*?)\s*<([^>]+)>\s*", author)
        author = {"name": match.group(1), "email": match.group(2)} if match else {"name": author}
    try:
        refresh = int(raw.get("refresh_seconds", 60))
    except (TypeError, ValueError) as exc:
        raise ConfigError("`refresh_seconds` muss eine Zahl sein.") from exc
    return BoardConfig(
        title=str(raw.get("title") or "Speccify"),
        refresh_seconds=max(5, refresh),
        author_name=str(author.get("name") or "Speccify Board"),
        author_email=str(author.get("email") or "board@speccify.local"),
        repos=tuple(repos),
    )


def load_config(path: Path) -> BoardConfig:
    if not path.is_file():
        raise ConfigError(f"Keine Konfiguration: {path}")
    return parse_config(path.read_text(encoding="utf-8"), base_dir=path.parent)
