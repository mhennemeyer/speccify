"""Top-level URL routing for the Speccify registry backend."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("api/v1/registry/", include("speccify_registry.api.urls")),
    path("", include("speccify_registry.web.urls")),
]
