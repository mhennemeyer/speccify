"""URL routing for the registry API app."""

from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("whoami", views.WhoamiView.as_view(), name="whoami"),
    path("specs", views.SpecsSearchView.as_view(), name="specs-search"),
    path("specs/publish", views.SpecPublishView.as_view(), name="specs-publish"),
    path(
        "specs/<str:scope>/<str:name>",
        views.SpecVersionListView.as_view(),
        name="spec-versions",
    ),
    path(
        "specs/<str:scope>/<str:name>/<str:version>",
        views.SpecVersionDetailView.as_view(),
        name="spec-version-detail",
    ),
    path(
        "specs/<str:scope>/<str:name>/<str:version>/yank",
        views.SpecVersionYankView.as_view(),
        name="spec-version-yank",
    ),
    path(
        "auth/device-code",
        views.DeviceCodeStartView.as_view(),
        name="api-device-code-start",
    ),
    path(
        "auth/device-code/poll",
        views.DeviceCodePollView.as_view(),
        name="api-device-code-poll",
    ),
]
