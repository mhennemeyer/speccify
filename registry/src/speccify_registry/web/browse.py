"""Server-rendered browse views: home (search), spec detail, user profile.

These are thin server-rendered counterparts to the JSON ``/api/v1/registry``
endpoints — they exist so anonymous visitors can discover specs without
running the CLI. The data shape mirrors :class:`SpecsSearchView` (latest
version + published_at) to keep semantic drift to a minimum.
"""

from __future__ import annotations

import yaml
from django.contrib.auth import get_user_model
from django.db.models import Max, Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from ..api.models import Scope, Spec, SpecVersion

User = get_user_model()

_PAGE_SIZE = 20


def _license_from_yaml(yaml_bytes: bytes) -> str:
    """Lese das Top-Level-`license`-Feld aus den Spec-Bytes (best effort).

    Die Registry speichert nur `yaml_bytes` (keine denormalisierte Lizenz-
    Spalte). Fürs Browsen reicht ein robustes Parsen: bei kaputtem YAML oder
    fehlendem Feld gibt es einen leeren String zurück — die Templates zeigen
    dann einfach kein Badge.
    """
    try:
        data = yaml.safe_load(bytes(yaml_bytes).decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError):
        return ""
    if not isinstance(data, dict):
        return ""
    value = data.get("license")
    return str(value) if value else ""


def _published_specs_qs():
    return (
        Spec.objects.select_related("scope")
        .annotate(latest_published_at=Max("versions__published_at"))
        .filter(latest_published_at__isnull=False)
    )


def _attach_latest(specs: list[Spec]) -> list[dict]:
    """Resolve latest version per spec without N+1 queries."""

    if not specs:
        return []
    spec_ids = [s.id for s in specs]
    latest: dict[int, SpecVersion] = {}
    for sv in SpecVersion.objects.filter(spec_id__in=spec_ids).order_by("spec_id", "-published_at"):
        latest.setdefault(sv.spec_id, sv)
    rows = []
    for spec in specs:
        sv = latest.get(spec.id)
        rows.append(
            {
                "id": f"@{spec.scope.name}/{spec.name}",
                "scope": spec.scope.name,
                "name": spec.name,
                "description": spec.description,
                "tags": list(spec.tags or []),
                "latest_version": sv.version if sv else None,
                "license": _license_from_yaml(sv.yaml_bytes) if sv else "",
                "latest_published_at": (
                    spec.latest_published_at if spec.latest_published_at else None
                ),
            }
        )
    return rows


@require_http_methods(["GET"])
def home_view(request: HttpRequest) -> HttpResponse:
    """``GET /`` — search + recently published specs."""

    q = (request.GET.get("q") or "").strip()
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    offset = (page - 1) * _PAGE_SIZE

    qs = _published_specs_qs()
    if q:
        qs = qs.filter(
            Q(scope__name__icontains=q)
            | Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(tags__icontains=q)
        )
    qs = qs.order_by("-latest_published_at", "scope__name", "name")
    total = qs.count()
    specs = list(qs[offset : offset + _PAGE_SIZE])
    rows = _attach_latest(specs)
    has_next = offset + _PAGE_SIZE < total
    has_prev = page > 1
    return render(
        request,
        "web/browse_home.html",
        {
            "q": q,
            "rows": rows,
            "total": total,
            "page": page,
            "has_next": has_next,
            "has_prev": has_prev,
        },
    )


@require_http_methods(["GET"])
def spec_detail_view(request: HttpRequest, scope: str, name: str) -> HttpResponse:
    """``GET /specs/<scope>/<name>`` — versions list + latest YAML preview."""

    spec = get_object_or_404(Spec.objects.select_related("scope"), scope__name=scope, name=name)
    versions = list(spec.versions.select_related("uploader").order_by("-published_at"))
    if not versions:
        raise Http404("Spec has no published versions yet.")
    latest = versions[0]
    try:
        yaml_text = bytes(latest.yaml_bytes).decode("utf-8")
    except UnicodeDecodeError:  # pragma: no cover - YAML is UTF-8 by contract
        yaml_text = ""
    return render(
        request,
        "web/browse_spec_detail.html",
        {
            "spec": spec,
            "spec_id": f"@{spec.scope.name}/{spec.name}",
            "versions": versions,
            "latest": latest,
            "license": _license_from_yaml(latest.yaml_bytes),
            "yaml_text": yaml_text,
        },
    )


@require_http_methods(["GET"])
def user_profile_view(request: HttpRequest, username: str) -> HttpResponse:
    """``GET /u/<username>`` — owned scopes and the specs published under them."""

    user = get_object_or_404(User, username=username)
    scopes = list(Scope.objects.filter(owner=user).order_by("name"))
    scope_ids = [s.id for s in scopes]
    specs = list(_published_specs_qs().filter(scope_id__in=scope_ids))
    rows = _attach_latest(specs)
    rows.sort(
        key=lambda r: (r["latest_published_at"] is None, r["latest_published_at"]),
        reverse=True,
    )
    return render(
        request,
        "web/browse_profile.html",
        {
            "profile_user": user,
            "scopes": scopes,
            "rows": rows,
        },
    )
