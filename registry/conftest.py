"""Pytest bootstrap for the Speccify registry backend.

``DJANGO_SETTINGS_MODULE`` is set via ``registry/pytest.ini`` so that
``pytest-django`` can boot Django before test collection. This conftest
only flips the in-memory SQLite switch via ``SPECCIFY_REGISTRY_TEST=1``
and ensures the editable workspace member is importable even when the
``.pth`` entry hasn't been picked up by the current interpreter.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SPECCIFY_REGISTRY_TEST", "1")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# macOS `UF_HIDDEN`-Workaround (siehe `scripts/_venv_hygiene.py`); No-Op auf
# Nicht-macOS bzw. wenn das venv nicht existiert.
from _venv_hygiene import unhide_venv_pth_files  # noqa: E402

unhide_venv_pth_files(_REPO_ROOT / ".venv")

_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
