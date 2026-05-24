"""Load/save the per-host Speccify CLI credentials file.

File: ``~/.config/speccify/credentials.toml`` (XDG-compliant, override
with ``SPECCIFY_CONFIG_HOME``). Layout::

    [registries."http://localhost:8001"]
    token = "speccify_..."
    username = "marc"

Tokens are stored in plaintext (npm/cargo/pip-style) — file permission
``0600`` is enforced on save and checked on load. The directory itself
is created with ``0700``.
"""

from __future__ import annotations

import os
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def _config_home() -> Path:
    override = os.environ.get("SPECCIFY_CONFIG_HOME")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "speccify"


def credentials_path() -> Path:
    return _config_home() / "credentials.toml"


def normalize_registry_url(url: str) -> str:
    """Drop path/query/fragment so ``scheme://host[:port]`` is the canonical key."""

    parts = urlsplit(url.rstrip("/"))
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


@dataclass(frozen=True)
class Credential:
    registry: str
    token: str
    username: str | None = None


def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def load_all() -> dict[str, Credential]:
    path = credentials_path()
    if not path.exists():
        return {}
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    out: dict[str, Credential] = {}
    for host, entry in raw.get("registries", {}).items():
        if not isinstance(entry, dict) or "token" not in entry:
            continue
        out[host] = Credential(
            registry=host,
            token=str(entry["token"]),
            username=entry.get("username"),
        )
    return out


def get(registry: str) -> Credential | None:
    return load_all().get(normalize_registry_url(registry))


def save(credential: Credential) -> Path:
    """Persist (or update) a single credential; returns the file path."""

    path = credentials_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass

    existing = load_all()
    existing[normalize_registry_url(credential.registry)] = credential

    lines: list[str] = []
    for host in sorted(existing):
        cred = existing[host]
        lines.append(f"[registries.{_toml_quote(host)}]")
        lines.append(f"token = {_toml_quote(cred.token)}")
        if cred.username:
            lines.append(f"username = {_toml_quote(cred.username)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def check_permissions(path: Path | None = None) -> None:
    """Warn (raise ``PermissionError``) when the credentials file is world-readable."""

    target = path or credentials_path()
    if not target.exists():
        return
    mode = stat.S_IMODE(target.stat().st_mode)
    if mode & 0o077:
        raise PermissionError(f"{target} is too permissive ({oct(mode)}); expected 0600.")
