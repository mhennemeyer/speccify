"""Pytest bootstrap for the Speccify registry backend.

Configures Django + ``pytest-django`` locally for the ``registry/`` tree
without forcing the global pytest config to depend on Django. The
in-memory SQLite database (`SPECCIFY_REGISTRY_TEST=1`) keeps tests fast
and avoids requiring a running Postgres service.
"""

from __future__ import annotations

import os

import django


def pytest_configure(config) -> None:  # noqa: D401 - pytest hook
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "speccify_registry.settings")
    os.environ.setdefault("SPECCIFY_REGISTRY_TEST", "1")
    django.setup()
