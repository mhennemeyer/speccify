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

_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
