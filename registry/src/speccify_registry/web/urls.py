"""URL routing for the server-rendered web UI."""

from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("auth/signup", views.signup_view, name="web-signup"),
    path("auth/login", views.login_view, name="web-login"),
    path("auth/logout", views.logout_view, name="web-logout"),
    path("auth/2fa-setup", views.totp_setup_view, name="web-totp-setup"),
    path("auth/tokens", views.tokens_view, name="web-tokens"),
    path(
        "auth/tokens/<int:token_id>/revoke",
        views.token_revoke_view,
        name="web-token-revoke",
    ),
    path("auth/device", views.device_approve_view, name="web-device-approve"),
]
