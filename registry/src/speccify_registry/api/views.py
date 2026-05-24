"""REST views for the Speccify registry API."""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db.models import Max, Q
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import device_codes, two_factor
from . import publish as publish_module
from .models import DeviceCodeStatus, Spec, SpecVersion, YankStatus
from .publish import PublishError

# Search pagination bounds — small enough to keep responses snappy in
# the upcoming Web-UI (Stage 4 frontend) without forcing the CLI to
# paginate aggressively.
_SEARCH_LIMIT_DEFAULT = 20
_SEARCH_LIMIT_MAX = 100


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
    """``GET /api/v1/registry/specs`` — list/search published specs.

    Query parameters:

    - ``q`` (optional): case-insensitive substring match against
      ``scope/name``, ``description`` and ``tags`` entries.
    - ``scope`` (optional): exact-match filter on the scope name
      (e.g. ``scope=org``).
    - ``limit`` (optional, default 20, max 100): page size.
    - ``offset`` (optional, default 0): page offset.

    Results are ordered by the most-recent ``SpecVersion.published_at``
    descending (specs without any published version are excluded), then
    by ``@scope/name`` for deterministic tie-breaks. The response
    always reports the total match count so the Web-UI (Stage 4
    frontend) can render pagination.

    Auth: anonymous — the registry is read-public; private mirrors
    will gate this at the reverse-proxy layer in later phases.
    """

    authentication_classes: list = []

    def get(self, request: Request) -> Response:
        params = request.query_params
        q = (params.get("q") or "").strip()
        scope_filter = (params.get("scope") or "").strip()

        try:
            limit = int(params.get("limit", _SEARCH_LIMIT_DEFAULT))
            offset = int(params.get("offset", 0))
        except (TypeError, ValueError):
            return Response(
                {"code": "invalid_pagination", "detail": "limit/offset must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if limit < 1 or offset < 0:
            return Response(
                {
                    "code": "invalid_pagination",
                    "detail": "limit must be >= 1 and offset must be >= 0.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit = min(limit, _SEARCH_LIMIT_MAX)

        # ``latest_published_at`` is computed once via an aggregate so we
        # can order by it and ship it in the response without N+1 queries.
        # ``Max(... published_at)`` is NULL for specs without versions —
        # those are filtered out below since the catalogue should only
        # surface things that are actually publishable today.
        qs = (
            Spec.objects.select_related("scope")
            .annotate(latest_published_at=Max("versions__published_at"))
            .filter(latest_published_at__isnull=False)
        )

        if scope_filter:
            qs = qs.filter(scope__name=scope_filter)

        if q:
            # ``tags`` is a JSONField list; ``__icontains`` matches the
            # serialised JSON which is good enough for substring search
            # in MVP (we explicitly avoid Postgres-specific JSON
            # operators here so SQLite-backed tests stay portable).
            qs = qs.filter(
                Q(scope__name__icontains=q)
                | Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(tags__icontains=q)
            )

        qs = qs.order_by("-latest_published_at", "scope__name", "name")
        total = qs.count()
        page = list(qs[offset : offset + limit])

        # Resolve the version string of the latest version for each spec
        # in a single query, keyed by spec_id, to avoid an N+1 loop.
        latest_versions: dict[int, SpecVersion] = {}
        if page:
            spec_ids = [s.id for s in page]
            for sv in SpecVersion.objects.filter(spec_id__in=spec_ids).order_by(
                "spec_id", "-published_at"
            ):
                latest_versions.setdefault(sv.spec_id, sv)

        results = []
        for spec in page:
            latest = latest_versions.get(spec.id)
            results.append(
                {
                    "id": f"@{spec.scope.name}/{spec.name}",
                    "scope": spec.scope.name,
                    "name": spec.name,
                    "description": spec.description,
                    "tags": list(spec.tags or []),
                    "latest_version": latest.version if latest else None,
                    "latest_published_at": (
                        spec.latest_published_at.isoformat() if spec.latest_published_at else None
                    ),
                }
            )

        return Response(
            {
                "results": results,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )


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


def _serialise_version(version: SpecVersion) -> dict:
    return {
        "version": version.version,
        "sha256": version.sha256,
        "yank_status": version.yank_status,
        "yank_reason": version.yank_reason,
        "published_at": version.published_at.isoformat(),
        "uploader": version.uploader.get_username(),
    }


class SpecVersionListView(APIView):
    """``GET /api/v1/registry/specs/<scope>/<name>`` — list all versions."""

    authentication_classes: list = []

    def get(self, request: Request, scope: str, name: str) -> Response:
        spec = Spec.objects.filter(scope__name=scope, name=name).select_related("scope").first()
        if spec is None:
            return Response(
                {"detail": f"Unknown spec @{scope}/{name}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        versions = list(spec.versions.all().select_related("uploader"))
        return Response(
            {
                "id": f"@{scope}/{name}",
                "description": spec.description,
                "tags": list(spec.tags or []),
                "versions": [_serialise_version(v) for v in versions],
            }
        )


class SpecVersionDetailView(APIView):
    """``GET /api/v1/registry/specs/<scope>/<name>/<version>`` — fetch YAML + meta."""

    authentication_classes: list = []

    def get(self, request: Request, scope: str, name: str, version: str) -> Response:
        row = (
            SpecVersion.objects.filter(spec__scope__name=scope, spec__name=name, version=version)
            .select_related("spec", "spec__scope", "uploader")
            .first()
        )
        if row is None:
            return Response(
                {"detail": f"Unknown version @{scope}/{name}@{version}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                **_serialise_version(row),
                "id": f"@{scope}/{name}",
                "yaml": bytes(row.yaml_bytes).decode("utf-8"),
            }
        )


class SpecPublishView(APIView):
    """``POST /api/v1/registry/specs`` — publish (or re-publish) a spec version.

    Accepts either ``multipart/form-data`` with a ``yaml`` file part, or
    ``application/json`` with a ``yaml`` string field. Auth via Bearer
    token; the token must have a fresh 2FA verification (TTL configured
    in ``settings.SPECCIFY_2FA_TTL_SECONDS``).
    """

    def post(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        api_token = request.auth
        if api_token is not None and not two_factor.has_fresh_2fa(api_token):
            return Response(
                {
                    "code": "stale_2fa",
                    "detail": (
                        "This token's 2FA verification is too old; re-mint the token to publish."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        yaml_bytes = _extract_yaml_bytes(request)
        if yaml_bytes is None:
            return Response(
                {
                    "code": "missing_yaml",
                    "detail": (
                        "Provide the spec YAML as a multipart 'yaml' file "
                        "or a JSON 'yaml' string field."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            version, created = publish_module.publish(user=request.user, yaml_bytes=yaml_bytes)
        except PublishError as exc:
            return Response(
                {"code": exc.code, "detail": exc.detail},
                status=exc.http_status,
            )

        body = {
            "id": f"@{version.spec.scope.name}/{version.spec.name}",
            "version": version.version,
            "sha256": version.sha256,
            "created": created,
            "yank_status": version.yank_status,
        }
        return Response(
            body,
            status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
        )


class SpecVersionYankView(APIView):
    """``POST /api/v1/registry/specs/<scope>/<name>/<version>/yank`` — yank a published version.

    Auth: Bearer token with fresh 2FA. Caller must own the scope.
    Idempotent: re-yanking an already-yanked version returns 200 and
    keeps the original reason unless a non-empty new reason is given.
    """

    def post(self, request: Request, scope: str, name: str, version: str) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        api_token = request.auth
        if api_token is not None and not two_factor.has_fresh_2fa(api_token):
            return Response(
                {
                    "code": "stale_2fa",
                    "detail": (
                        "This token's 2FA verification is too old; re-mint the token to yank."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        row = (
            SpecVersion.objects.filter(spec__scope__name=scope, spec__name=name, version=version)
            .select_related("spec", "spec__scope")
            .first()
        )
        if row is None:
            return Response(
                {
                    "code": "version_not_found",
                    "detail": f"Unknown version @{scope}/{name}@{version}.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if row.spec.scope.owner_id != request.user.id:
            return Response(
                {
                    "code": "scope_forbidden",
                    "detail": (f"You do not own scope @{scope}; only the owner can yank versions."),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        reason_raw = request.data.get("reason") if hasattr(request, "data") else None
        reason = (reason_raw or "").strip() if isinstance(reason_raw, str) else ""

        already_yanked = row.yank_status == YankStatus.YANKED
        row.yank_status = YankStatus.YANKED
        # Keep the original reason on a no-op re-yank unless the caller supplies a new one;
        # this matches npm's `npm unpublish` semantics and avoids overwriting forensic notes.
        if reason:
            row.yank_reason = reason
        elif not already_yanked:
            row.yank_reason = ""
        row.save(update_fields=["yank_status", "yank_reason"])

        return Response(
            {
                "id": f"@{scope}/{name}",
                "version": version,
                "yank_status": row.yank_status,
                "yank_reason": row.yank_reason or None,
                "already_yanked": already_yanked,
            },
            status=status.HTTP_200_OK,
        )


def _extract_yaml_bytes(request: Request) -> bytes | None:
    """Read YAML bytes from either multipart upload or JSON body."""

    upload = request.FILES.get("yaml") if hasattr(request, "FILES") else None
    if upload is not None:
        return upload.read()
    if hasattr(request, "data"):
        payload = request.data.get("yaml")
        if isinstance(payload, str):
            return payload.encode("utf-8")
        if isinstance(payload, (bytes, bytearray)):
            return bytes(payload)
    return None
