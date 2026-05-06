from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import SpecLoader, SpecLoaderError


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_load_happy_path(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "spec.yaml",
        "id: spec://x\nversion: 1.0.0\nkind: ui-component\ntitle: X\nsummary: y\n",
    )
    data = SpecLoader.load(p)
    assert data["id"] == "spec://x"
    assert data["version"] == "1.0.0"


def test_load_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SpecLoaderError):
        SpecLoader.load(tmp_path / "nope.yaml")


def test_load_invalid_yaml(tmp_path: Path) -> None:
    p = _write(tmp_path, "bad.yaml", "id: spec://x\n  version: : :\n")
    with pytest.raises(SpecLoaderError):
        SpecLoader.load(p)


def test_load_empty_file(tmp_path: Path) -> None:
    p = _write(tmp_path, "empty.yaml", "")
    with pytest.raises(SpecLoaderError):
        SpecLoader.load(p)


def test_load_non_mapping(tmp_path: Path) -> None:
    p = _write(tmp_path, "list.yaml", "- a\n- b\n")
    with pytest.raises(SpecLoaderError):
        SpecLoader.load(p)
