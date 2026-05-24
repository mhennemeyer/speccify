"""Persistence models for the Speccify registry API (Phase 2, Stage 1).

The data model intentionally stays minimal — only what publish/search/yank
in later stages actually consume. The `User` model is the Django default
(`auth.User`); registry-specific user attributes (PATs, 2FA state) live on
side tables (`ApiToken`, `django_otp` `TOTPDevice`).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class YankStatus(models.TextChoices):
    NONE = "none", "none"
    YANKED = "yanked", "yanked"


class Scope(models.Model):
    """A registry-bound namespace like ``@org`` or ``@marc``.

    Per the Phase-2 decision (Open Question 7), scopes are self-service:
    the first user to publish under a free scope becomes its owner. Names
    listed in :class:`ScopeReservation` are blocked from auto-claiming.
    """

    name = models.CharField(max_length=64, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_scopes",
    )
    is_reserved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"@{self.name}"


class Spec(models.Model):
    """A spec identity inside a scope (e.g. ``@org/button``)."""

    scope = models.ForeignKey(Scope, on_delete=models.CASCADE, related_name="specs")
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scope__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "name"], name="uniq_spec_per_scope"
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"@{self.scope.name}/{self.name}"


class SpecVersion(models.Model):
    """A single published version of a :class:`Spec`.

    ``yaml_bytes`` holds the original on-disk bytes — the same input that
    feeds ``sha256(yaml_bytes)``. Keeping the canonical bytes (not a
    re-serialised round-trip) is what makes reproducibility work between
    CLI, MCP and the web playground.
    """

    spec = models.ForeignKey(Spec, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=64)
    yaml_bytes = models.BinaryField()
    sha256 = models.CharField(max_length=64, db_index=True)
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_versions",
    )
    yank_status = models.CharField(
        max_length=16,
        choices=YankStatus.choices,
        default=YankStatus.NONE,
    )
    yank_reason = models.TextField(blank=True, default="")
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["spec__scope__name", "spec__name", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["spec", "version"], name="uniq_version_per_spec"
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.spec}@{self.version}"


class ApiToken(models.Model):
    """Personal-access token for CLI/MCP authentication.

    The plaintext token is shown to the user **once** at creation time
    and never stored — only its argon2 hash lives in the DB.
    ``last_2fa_verified_at`` records the freshest TOTP confirmation that
    was used to mint or rotate this token; publish/yank endpoints will
    reject tokens whose 2FA timestamp is older than the configured TTL
    (default 5 minutes, enforced in Stage 2).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_tokens",
    )
    label = models.CharField(max_length=128)
    # Short non-secret prefix of the cleartext token (first 12 chars) — used as
    # an indexed lookup key so verification doesn't have to brute-force-hash
    # against every row. Not enough entropy on its own to authenticate.
    token_prefix = models.CharField(max_length=16, db_index=True, default="")
    token_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    requires_2fa = models.BooleanField(default=True)
    last_2fa_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"ApiToken(user={self.user_id}, label={self.label!r})"


class DeviceCodeStatus(models.TextChoices):
    PENDING = "pending", "pending"
    APPROVED = "approved", "approved"
    DENIED = "denied", "denied"
    EXPIRED = "expired", "expired"
    CONSUMED = "consumed", "consumed"


class DeviceCode(models.Model):
    """OAuth-style device-authorization grant for `speccify login`.

    The CLI starts the flow with ``POST /auth/device-code``, opens the
    browser at ``verification_url`` (where the user logs in and enters
    ``user_code``), then polls ``POST /auth/device-code/poll`` until the
    record is ``approved`` and a freshly-minted :class:`ApiToken` is
    handed back exactly once (status flips to ``consumed``).
    """

    device_code = models.CharField(max_length=64, unique=True)
    user_code = models.CharField(max_length=16, unique=True)
    status = models.CharField(
        max_length=16,
        choices=DeviceCodeStatus.choices,
        default=DeviceCodeStatus.PENDING,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_codes",
        null=True,
        blank=True,
    )
    api_token = models.ForeignKey(
        "ApiToken",
        on_delete=models.SET_NULL,
        related_name="device_codes",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"DeviceCode(user_code={self.user_code}, status={self.status})"


class ScopeReservation(models.Model):
    """Reservation list of blocked scope names (admin-managed).

    Entries here cannot be auto-claimed via self-service. Curated upfront
    with platform terms, common words and known brand names; admins can
    extend the list via the Django admin in later stages.
    """

    name = models.CharField(max_length=64, unique=True)
    reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.name
