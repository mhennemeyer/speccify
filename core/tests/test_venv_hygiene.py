"""Tests für `scripts/_venv_hygiene.py` — macOS `UF_HIDDEN`-Workaround.

Das Modul ist plattform-gated (`sys.platform == "darwin"`), die Tests
ebenfalls. Auf Nicht-macOS-Systemen werden die Verhaltens-Tests
übersprungen; ein einziger Test prüft das No-Op-Verhalten plattformneutral.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

# `scripts/` ist nicht als Paket exportiert — direkt über `sys.path` ziehen,
# analog zum Root-`conftest.py`.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _venv_hygiene import (  # noqa: E402
    find_default_venv,
    unhide_venv_deep,
    unhide_venv_pth_files,
)


def test_unhide_returns_zero_for_missing_venv(tmp_path: Path) -> None:
    """Nicht existierendes Venv → No-Op, kein Fehler."""
    assert unhide_venv_pth_files(tmp_path / "does-not-exist") == 0


def test_unhide_returns_zero_for_empty_venv(tmp_path: Path) -> None:
    """Leeres Venv (keine `.pth`-Dateien) → 0 angefasste Dateien."""
    (tmp_path / "lib" / "python3.12" / "site-packages").mkdir(parents=True)
    assert unhide_venv_pth_files(tmp_path) == 0


def test_find_default_venv_walks_parents(tmp_path: Path) -> None:
    """`find_default_venv` findet ein `.venv` im Parent-Verzeichnis."""
    venv = tmp_path / ".venv"
    venv.mkdir()
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert find_default_venv(sub) == venv


def test_find_default_venv_returns_none_when_absent(tmp_path: Path) -> None:
    assert find_default_venv(tmp_path) is None


@pytest.mark.skipif(sys.platform != "darwin", reason="UF_HIDDEN ist macOS-only.")
def test_unhide_clears_uf_hidden_flag(tmp_path: Path) -> None:
    """Auf macOS: `UF_HIDDEN` wird von `.pth`-Dateien entfernt, andere
    Flags bleiben unangetastet, die Zählung stimmt."""
    sp = tmp_path / "lib" / "python3.12" / "site-packages"
    sp.mkdir(parents=True)
    pth_hidden = sp / "hidden.pth"
    pth_visible = sp / "visible.pth"
    other = sp / "ignored.txt"
    pth_hidden.write_text("/some/path\n")
    pth_visible.write_text("/other/path\n")
    other.write_text("noise\n")

    uf_hidden = stat.UF_HIDDEN
    os.chflags(pth_hidden, uf_hidden)
    # `other` bekommt auch das Flag — wird aber nicht angefasst, weil keine
    # `.pth`-Endung.
    os.chflags(other, uf_hidden)

    touched = unhide_venv_pth_files(tmp_path)
    assert touched == 1

    assert not (pth_hidden.lstat().st_flags & uf_hidden)
    assert not (pth_visible.lstat().st_flags & uf_hidden)
    # Nicht-`.pth`-Datei bleibt unangetastet:
    assert other.lstat().st_flags & uf_hidden

    # Idempotenz: zweiter Lauf fasst nichts mehr an.
    assert unhide_venv_pth_files(tmp_path) == 0


@pytest.mark.skipif(sys.platform != "darwin", reason="UF_HIDDEN ist macOS-only.")
def test_unhide_clears_hidden_subdirs_and_py_files(tmp_path: Path) -> None:
    """Auch versteckte Verzeichnisse + versteckte `.py`-Dateien tiefer im
    Baum (z. B. `django/contrib/admin/templatetags/`) werden entversteckt.
    `__pycache__` bleibt ausgespart."""
    sp = tmp_path / "lib" / "python3.12" / "site-packages"
    pkg = sp / "django" / "contrib" / "admin" / "templatetags"
    pkg.mkdir(parents=True)
    py_file = pkg / "admin_urls.py"
    py_file.write_text("# stub\n")
    pycache = pkg / "__pycache__"
    pycache.mkdir()
    pyc_file = pycache / "admin_urls.cpython-312.pyc"
    pyc_file.write_bytes(b"\x00")

    uf_hidden = stat.UF_HIDDEN
    os.chflags(pkg, uf_hidden)
    os.chflags(py_file, uf_hidden)
    os.chflags(pycache, uf_hidden)
    os.chflags(pyc_file, uf_hidden)

    # `unhide_venv_pth_files` (flach) lässt versteckte Subdirs/Python-Files in
    # Ruhe — die fängt nur der `--deep`-Sweep ab.
    assert unhide_venv_pth_files(tmp_path) == 0
    assert pkg.lstat().st_flags & uf_hidden

    touched = unhide_venv_deep(tmp_path)
    # Erwartet: `pkg` (Dir) + `py_file` (.py) — `__pycache__` + `.pyc` bleiben.
    assert touched == 2
    assert not (pkg.lstat().st_flags & uf_hidden)
    assert not (py_file.lstat().st_flags & uf_hidden)
    assert pycache.lstat().st_flags & uf_hidden
    assert pyc_file.lstat().st_flags & uf_hidden

    # Idempotenz auch für den deep-Sweep.
    assert unhide_venv_deep(tmp_path) == 0
