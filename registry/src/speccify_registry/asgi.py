"""ASGI entrypoint for the Speccify registry backend."""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "speccify_registry.settings")

application = get_asgi_application()
