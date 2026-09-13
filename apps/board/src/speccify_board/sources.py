"""Where a board's specs come from: a shallow clone of a register branch, a
local project folder, or a folder full of projects. Writes go back the same
way the desktop app does it — commit on the register branch, push, never
force (Spec 028/032)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from speccify_core.board import BoardSpec, load_specs

from speccify_board.config import RepoConfig

GIT_TIMEOUT = 60


class SourceError(Exception):
    """A repository could not be read or written."""


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT,
        env={"GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C", "PATH": _path(), "HOME": _home()},
    )
    if check and result.returncode != 0:
        raise SourceError(result.stderr.strip() or f"git {' '.join(args)} → {result.returncode}")
    return result


def _path() -> str:
    import os

    return os.environ.get("PATH", "/usr/bin:/bin")


def _home() -> str:
    import os

    return os.environ.get("HOME", "/tmp")


@dataclass
class SourceState:
    specs: list[BoardSpec] = field(default_factory=list)
    commit: str | None = None
    refreshed_at: str | None = None
    error: str | None = None


@dataclass
class Source:
    """One board entry: a remote register clone or a local folder."""

    config: RepoConfig
    data_dir: Path
    author_name: str
    author_email: str
    state: SourceState = field(default_factory=SourceState)
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def clone_dir(self) -> Path:
        return self.data_dir / "repos" / self.config.name

    # --- reading ---------------------------------------------------------------

    def specs_dirs(self) -> list[tuple[str, Path]]:
        """(label, folder) pairs; a workspace folder yields one per project."""
        if self.config.is_remote:
            return [(self.name, self.clone_dir)]
        base = self.config.path
        assert base is not None
        if (base / ".agent" / "specs").is_dir():
            return [(self.name, base / ".agent" / "specs")]
        if any(base.glob("*/SPEC.md")):
            return [(self.name, base)]
        found = sorted(
            (f"{self.name}/{child.name}", child / ".agent" / "specs")
            for child in base.iterdir()
            if child.is_dir() and (child / ".agent" / "specs").is_dir()
        )
        if not found:
            raise SourceError(f"Kein Spec-Ordner unter {base}")
        return found

    def refresh(self) -> SourceState:
        with self.lock:
            try:
                if self.config.is_remote:
                    self._sync_clone()
                specs: list[BoardSpec] = []
                for label, folder in self.specs_dirs():
                    specs.extend(load_specs(folder, repo=label))
                self.state = SourceState(
                    specs=specs,
                    commit=self._head() if self.config.is_remote else None,
                    refreshed_at=datetime.now(UTC).isoformat(timespec="seconds"),
                    error=None,
                )
            except (SourceError, OSError, subprocess.TimeoutExpired) as exc:
                self.state = SourceState(
                    specs=self.state.specs,
                    commit=self.state.commit,
                    refreshed_at=datetime.now(UTC).isoformat(timespec="seconds"),
                    error=str(exc),
                )
            return self.state

    def _head(self) -> str | None:
        result = git(self.clone_dir, "rev-parse", "--short", "HEAD", check=False)
        return result.stdout.strip() or None

    def _sync_clone(self) -> None:
        assert self.config.url is not None
        branch = self.config.branch
        if not (self.clone_dir / ".git").exists():
            self.clone_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.rmtree(self.clone_dir, ignore_errors=True)
            git(
                self.clone_dir.parent,
                "clone",
                "--quiet",
                "--depth=1",
                "--branch",
                branch,
                "--single-branch",
                self.config.url,
                self.clone_dir.name,
            )
            git(self.clone_dir, "config", "user.name", self.author_name)
            git(self.clone_dir, "config", "user.email", self.author_email)
            return
        git(self.clone_dir, "fetch", "--quiet", "--depth=1", "origin", branch)
        # Unsent local commits (a failed push) are pushed first, never discarded.
        ahead = git(self.clone_dir, "rev-list", "--count", f"origin/{branch}..HEAD").stdout.strip()
        if ahead not in ("", "0"):
            self._push(branch)
        git(self.clone_dir, "reset", "--quiet", "--hard", f"origin/{branch}")

    # --- writing -------------------------------------------------------------------

    def _push(self, branch: str) -> None:
        """Push, and on rejection catch up once (fetch + rebase) and retry."""
        first = git(self.clone_dir, "push", "--quiet", "origin", f"HEAD:{branch}", check=False)
        if first.returncode == 0:
            return
        git(self.clone_dir, "fetch", "--quiet", "origin", branch)
        rebase = git(self.clone_dir, "rebase", "--quiet", f"origin/{branch}", check=False)
        if rebase.returncode != 0:
            git(self.clone_dir, "rebase", "--abort", check=False)
            raise SourceError(
                "Push abgelehnt und Nachholen mit Konflikt — bitte in der App entscheiden: "
                + rebase.stderr.strip()
            )
        git(self.clone_dir, "push", "--quiet", "origin", f"HEAD:{branch}")

    def _folder_for(self, spec_id: str) -> tuple[str, Path]:
        for label, folder in self.specs_dirs():
            candidate = folder / spec_id / "SPEC.md"
            if candidate.is_file():
                return label, candidate
        raise SourceError(f"Keine Spec {spec_id} in {self.name}")

    def _commit_and_push(self, subject: str) -> str | None:
        if not self.config.is_remote:
            return None
        git(self.clone_dir, "add", "-A")
        git(self.clone_dir, "commit", "--quiet", "-m", subject)
        self._push(self.config.branch)
        return self._head()

    def _log(self, spec_file: Path, spec_id: str, event_type: str, summary: str) -> None:
        line = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "spec_id": spec_id,
            "event_type": event_type,
            "actor": "board",
            "summary": summary,
        }
        with (spec_file.parent / "history.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    def move_station(self, spec_id: str, station: str) -> str | None:
        """Rewrite only the `station:` line, log, commit and push."""
        if station not in ("Backlog", "Doing", "Done"):
            raise SourceError(f"Unbekannte Station: {station}")
        with self.lock:
            _label, spec_file = self._folder_for(spec_id)
            text = spec_file.read_text(encoding="utf-8")
            new_text, old_station = _replace_station(text, station)
            if old_station == station:
                return self.state.commit
            spec_file.write_text(new_text, encoding="utf-8")
            self._log(
                spec_file, spec_id, "station_changed", f"{old_station} -> {station} · Web-Board"
            )
            return self._commit_and_push(f"spec({spec_id}): {old_station} -> {station} (Web-Board)")

    def toggle_task(self, spec_id: str, index: int, done: bool) -> str | None:
        """Flip the n-th checkbox outside code fences, log, commit and push."""
        with self.lock:
            _label, spec_file = self._folder_for(spec_id)
            text = spec_file.read_text(encoding="utf-8")
            new_text, task_text = _toggle_task(text, index, done)
            if new_text == text:
                return self.state.commit
            spec_file.write_text(new_text, encoding="utf-8")
            mark = "erledigt" if done else "offen"
            self._log(
                spec_file,
                spec_id,
                "spec_edited",
                f"Task {index + 1} {mark}: {task_text} · Web-Board",
            )
            return self._commit_and_push(f"spec({spec_id}): Task {index + 1} {mark} (Web-Board)")


_TASK_RE = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+\[)( |x|X)(\]\s+)(.*?)(\s*)$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _replace_station(text: str, station: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise SourceError("Kein Frontmatter.")
    old = ""
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() == "station":
            old = value.strip()
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            lines[index] = f"station: {station}{ending}"
            return "".join(lines), old
    raise SourceError("Keine station:-Zeile im Frontmatter.")


def _toggle_task(text: str, index: int, done: bool) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    fence: str | None = None
    seen = -1
    for position, line in enumerate(lines):
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            fence = marker if fence is None else (None if marker == fence else fence)
            continue
        if fence is not None:
            continue
        match = _TASK_RE.match(line.rstrip("\r\n"))
        if not match:
            continue
        seen += 1
        if seen != index:
            continue
        ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        lines[position] = (
            f"{match.group(1)}{'x' if done else ' '}{match.group(3)}{match.group(4)}{ending}"
        )
        return "".join(lines), match.group(4)
    raise SourceError(f"Keine Task Nr. {index + 1}.")
