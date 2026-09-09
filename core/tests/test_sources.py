"""Tests for skill sources — the location model shared with the desktop app."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core.sources import (
    SourceUnavailable,
    checkout_dir,
    display_name,
    is_git_location,
    resolve_source,
    slug,
)


def test_git_locations_names_and_slugs_match_the_app() -> None:
    assert is_git_location("https://github.com/acme/skills")
    assert is_git_location("git@gitlab.itsd.example:team/skills.git")
    assert is_git_location("git+https://github.com/acme/skills")
    assert not is_git_location("~/Desktop/Work/speccify/skills")
    assert display_name("https://github.com/acme/skills.git") == "skills"
    assert display_name("git@gitlab.example:team/itsd-skills.git") == "itsd-skills"
    assert display_name("~/Work/speccify/skills/") == "skills"
    # Pinned to the Rust test in sources_cmd.rs — both sides must agree.
    assert slug("https://github.com/acme/Skills.git") == "github.com-acme-skills"
    assert slug("git@gitlab.example:team/x.git") == "gitlab.example-team-x"


def test_resolve_source_uses_the_managed_checkout(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    location = "https://github.com/acme/skills.git"
    assert checkout_dir(location) == tmp_path / ".speccify/sources/github.com-acme-skills"
    with pytest.raises(SourceUnavailable, match="not cloned"):
        resolve_source(location)
    (checkout_dir(location) / ".git").mkdir(parents=True)
    assert resolve_source(location) == checkout_dir(location)


def test_resolve_source_resolves_directories_relative_to_the_manifest(tmp_path: Path) -> None:
    (tmp_path / "project/vendor-skills").mkdir(parents=True)
    base = tmp_path / "project"
    assert resolve_source("./vendor-skills", base) == (base / "vendor-skills").resolve()
    assert resolve_source(str(base / "vendor-skills")) == (base / "vendor-skills").resolve()
    with pytest.raises(SourceUnavailable, match="does not exist"):
        resolve_source("./missing", base)
