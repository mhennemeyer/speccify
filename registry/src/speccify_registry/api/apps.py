"""App configuration for the Speccify registry API."""

from __future__ import annotations

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "speccify_registry.api"
    label = "registry_api"
    verbose_name = "Speccify Registry API"
