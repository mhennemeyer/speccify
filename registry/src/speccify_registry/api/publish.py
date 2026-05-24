"""Server-side helpers for the publish/fetch/versions REST endpoints.

Splitting the parsing + validation logic out of ``views.py`` keeps the
view thin (HTTP shape only) and makes it reusable from management
commands or future MCP-side helpers.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import yaml
from speccify_core import SchemaValidator

from .models import Scope, ScopeReservation, Spec, SpecVersion

_SCHEMA_VALIDATOR = SchemaValidator()

# ``@scope/name`` — scope and name slugs per spec.schema.json (lowercase
# alphanumerics + dashes, must start with a letter).
_SPEC_ID_RE = re.compile(r"^@([a-z][a-z0-9-]*)/([a-z][a-z0-9-]*)$")

# Strict SemVer subset accepted in Phase 2 (no pre-release/build metadata).
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class PublishError(Exception):
    """Base class for user-facing publish failures, mapped to 4xx by the view."""

    http_status = 400

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class InvalidSpecError(PublishError):
    http_status = 400


class ScopeReservedError(PublishError):
    http_status = 403


class ScopeForbiddenError(PublishError):
    http_status = 403


class VersionConflictError(PublishError):
    http_status = 409


@dataclass(frozen=True)
class ParsedSpec:
    yaml_bytes: bytes
    sha256: str
    spec_id: str
    scope_name: str
    name: str
    version: str
    description: str
    tags: list[str]


def _hash(yaml_bytes: bytes) -> str:
    return hashlib.sha256(yaml_bytes).hexdigest()


def parse_and_validate(yaml_bytes: bytes) -> ParsedSpec:
    """Parse YAML, validate against ``spec.schema.json``, return ``ParsedSpec``.

    The bytes are hashed *as received* (not after a YAML round-trip) so
    that reproducibility against CLI- and MCP-emitted lockfile hashes is
    preserved.
    """

    try:
        data = yaml.safe_load(yaml_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise InvalidSpecError("invalid_encoding", f"Not valid UTF-8: {exc}") from exc
    except yaml.YAMLError as exc:
        raise InvalidSpecError("invalid_yaml", f"YAML parse error: {exc}") from exc

    if not isinstance(data, dict):
        raise InvalidSpecError("invalid_yaml", "Spec root must be a mapping.")

    issues = _SCHEMA_VALIDATOR.iter_issues(data)
    if issues:
        raise InvalidSpecError(
            "schema_violation",
            "; ".join(issue.format() for issue in issues[:5]),
        )

    spec_id = data["id"]
    match = _SPEC_ID_RE.match(spec_id)
    if not match:
        raise InvalidSpecError(
            "unsupported_spec_id",
            f"Phase-2 registry only accepts @scope/name ids, got {spec_id!r}.",
        )
    scope_name, name = match.group(1), match.group(2)

    version = str(data["version"])
    if not _VERSION_RE.match(version):
        raise InvalidSpecError(
            "invalid_version",
            f"version must be MAJOR.MINOR.PATCH, got {version!r}.",
        )

    tags_raw = data.get("tags") or []
    if not isinstance(tags_raw, list):
        raise InvalidSpecError("invalid_tags", "tags must be a list of strings.")
    tags = [str(t) for t in tags_raw]

    return ParsedSpec(
        yaml_bytes=yaml_bytes,
        sha256=_hash(yaml_bytes),
        spec_id=spec_id,
        scope_name=scope_name,
        name=name,
        version=version,
        description=str(data.get("summary") or ""),
        tags=tags,
    )


def _ensure_scope_for_user(user, scope_name: str) -> Scope:
    """Look up or auto-claim a scope on behalf of ``user``.

    Phase-2 decision (Open Question 7): scopes are self-service, but
    names listed in :class:`ScopeReservation` cannot be auto-claimed.
    """

    scope = Scope.objects.filter(name=scope_name).first()
    if scope is not None:
        if scope.owner_id != user.id:
            raise ScopeForbiddenError(
                "scope_forbidden",
                f"@{scope_name} is owned by another user.",
            )
        return scope

    if ScopeReservation.objects.filter(name=scope_name).exists():
        raise ScopeReservedError(
            "scope_reserved",
            f"@{scope_name} is on the reservation list and can't be auto-claimed.",
        )
    return Scope.objects.create(name=scope_name, owner=user)


def publish(*, user, yaml_bytes: bytes) -> tuple[SpecVersion, bool]:
    """Persist a new spec version (or return the existing one for idempotency).

    Returns ``(version_row, created)`` — ``created`` is ``False`` when
    the same bytes were already published under this id+version.
    """

    parsed = parse_and_validate(yaml_bytes)
    scope = _ensure_scope_for_user(user, parsed.scope_name)
    spec, _ = Spec.objects.get_or_create(
        scope=scope,
        name=parsed.name,
        defaults={"description": parsed.description, "tags": parsed.tags},
    )

    existing = SpecVersion.objects.filter(spec=spec, version=parsed.version).first()
    if existing is not None:
        if existing.sha256 == parsed.sha256:
            return existing, False
        raise VersionConflictError(
            "version_conflict",
            f"{parsed.spec_id}@{parsed.version} already exists with different bytes.",
        )

    version = SpecVersion.objects.create(
        spec=spec,
        version=parsed.version,
        yaml_bytes=parsed.yaml_bytes,
        sha256=parsed.sha256,
        uploader=user,
    )
    # Keep the latest description/tags on the Spec row in sync (cheap
    # denormalisation that powers Stage-4 search without re-parsing).
    if spec.description != parsed.description or spec.tags != parsed.tags:
        spec.description = parsed.description
        spec.tags = parsed.tags
        spec.save(update_fields=["description", "tags"])
    return version, True
