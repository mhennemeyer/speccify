"""DRF authentication classes for the Speccify registry API."""

from __future__ import annotations

from rest_framework import authentication, exceptions

from .tokens import verify_cleartext


class BearerTokenAuthentication(authentication.BaseAuthentication):
    """Authenticate via ``Authorization: Bearer <token>``.

    The token's :class:`~speccify_registry.api.models.ApiToken` row is
    attached to ``request.auth`` so downstream views can enforce
    freshness rules (``requires_2fa`` / ``last_2fa_verified_at``) without
    a second DB roundtrip.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None

        cleartext = header[len(self.keyword) + 1 :].strip()
        if not cleartext:
            raise exceptions.AuthenticationFailed("Empty bearer token.")

        api_token = verify_cleartext(cleartext)
        if api_token is None:
            raise exceptions.AuthenticationFailed("Invalid or revoked token.")

        return (api_token.user, api_token)

    def authenticate_header(self, request):
        return self.keyword
