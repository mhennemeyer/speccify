"""URL routing for the registry API app."""

from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("whoami", views.WhoamiView.as_view(), name="whoami"),
    path("specs", views.SpecsSearchView.as_view(), name="specs-search"),
]
