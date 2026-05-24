"""REST views for the Speccify registry API."""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import device_codes
from .models import DeviceCodeStatus


class WhoamiView(APIView):
    def get(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(
            {
                "username": request.user.get_username(),
                "scopes": list(request.user.owned_scopes.values_list("name", flat=True)),
            }
        )


class SpecsSearchView(APIView):
    def get(self, request: Request) -> Response:
        # Stage 1 placeholder — real full-text search lands in Stage 4.
        return Response({"results": [], "total": 0, "page": 1, "per_page": 20})


def _verification_url(request: Request) -> str:
    return request.build_absolute_uri("/auth/device")


class DeviceCodeStartView(APIView):
    """``POST /api/v1/registry/auth/device-code`` — start a device-code flow."""

    authentication_classes: list = []

    def post(self, request: Request) -> Response:
        dc = device_codes.issue()
        return Response(
            {
                "device_code": dc.device_code,
                "user_code": dc.user_code,
                "verification_url": _verification_url(request),
                "expires_in": settings.SPECCIFY_DEVICE_CODE_TTL_SECONDS,
                "interval": settings.SPECCIFY_DEVICE_CODE_POLL_INTERVAL_SECONDS,
            },
            status=status.HTTP_201_CREATED,
        )


class DeviceCodePollView(APIView):
    """``POST /api/v1/registry/auth/device-code/poll`` — poll until approved.

    On approval, returns ``{token: <cleartext>}`` exactly once and flips
    the row to ``consumed``; subsequent polls yield ``{status: "denied"}``.
    """

    authentication_classes: list = []

    def post(self, request: Request) -> Response:
        device_code = request.data.get("device_code") if hasattr(request, "data") else None
        if not device_code:
            return Response(
                {"detail": "device_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dc = device_codes.fetch_by_device_code(device_code)
        if dc is None:
            return Response(
                {"detail": "Unknown device_code."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if dc.status == DeviceCodeStatus.PENDING:
            return Response({"status": "pending"})
        if dc.status == DeviceCodeStatus.EXPIRED:
            return Response({"status": "expired"})
        if dc.status == DeviceCodeStatus.DENIED:
            return Response({"status": "denied"})
        if dc.status == DeviceCodeStatus.CONSUMED:
            return Response({"status": "denied"})
        if dc.status == DeviceCodeStatus.APPROVED:
            # The cleartext is stashed in the cache by the web-side
            # ``approve`` view, keyed by device_code; we hand it out at
            # most once and immediately flip status to ``consumed``.
            cache_key = device_code_cache_key(dc.device_code)
            cleartext = cache.get(cache_key)
            if cleartext is None:
                device_codes.consume(dc)
                return Response({"status": "denied"})
            cache.delete(cache_key)
            device_codes.consume(dc)
            return Response({"token": cleartext})
        return Response({"status": "denied"})  # pragma: no cover - defensive


def device_code_cache_key(device_code: str) -> str:
    return f"speccify:devicecode:{device_code}"
