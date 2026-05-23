"""Minimal API views for Stage 1 smoke tests.

Real endpoints (publish/search/yank/fetch/versions/whoami) arrive in
Stages 2–5. Stage 1 only exposes:

* ``GET  /api/v1/registry/whoami``  → 401 for anonymous requests.
* ``GET  /api/v1/registry/specs``   → empty paginated list (placeholder
  for the search endpoint).
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


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
                "scopes": list(
                    request.user.owned_scopes.values_list("name", flat=True)
                ),
            }
        )


class SpecsSearchView(APIView):
    def get(self, request: Request) -> Response:
        # Stage 1 placeholder — real full-text search lands in Stage 4.
        return Response(
            {"results": [], "total": 0, "page": 1, "per_page": 20}
        )
