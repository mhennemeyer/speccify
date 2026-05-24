"""Helpers for minting, hashing and verifying Speccify API tokens.

The cleartext token is shown to the user **exactly once** at creation
time. The database only stores:

* ``token_prefix`` — the first 12 chars (non-secret, used as an indexed
  lookup key so verification is O(matches) instead of O(rows)).
* ``token_hash`` — an argon2 hash of the full cleartext token.

Token format: ``speccify_<32-base32-chars>``. The leading prefix makes
tokens grep-able in logs/issues so leak-detection bots (truffleHog,
GitHub secret scanning) can recognise them.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from django.utils import timezone

from .models import ApiToken

_TOKEN_PREFIX_LITERAL = "speccify_"
_TOKEN_BODY_BYTES = 24  # → 32 base32 chars

_hasher = PasswordHasher()


@dataclass(frozen=True)
class MintedToken:
    """Result of minting a fresh token; the cleartext is only here."""

    token: ApiToken
    cleartext: str


def _generate_cleartext() -> str:
    body = secrets.token_urlsafe(_TOKEN_BODY_BYTES)
    return f"{_TOKEN_PREFIX_LITERAL}{body}"


def _prefix(cleartext: str) -> str:
    return cleartext[:12]


def mint_token(
    *,
    user,
    label: str,
    requires_2fa: bool = True,
    last_2fa_verified_at=None,
) -> MintedToken:
    """Create a new ``ApiToken`` row and return it together with the cleartext."""

    cleartext = _generate_cleartext()
    token = ApiToken.objects.create(
        user=user,
        label=label,
        token_prefix=_prefix(cleartext),
        token_hash=_hasher.hash(cleartext),
        requires_2fa=requires_2fa,
        last_2fa_verified_at=last_2fa_verified_at,
    )
    return MintedToken(token=token, cleartext=cleartext)


def verify_cleartext(cleartext: str) -> ApiToken | None:
    """Return the matching active :class:`ApiToken` row, or ``None``.

    Performs a prefix-indexed lookup and then an argon2 ``verify`` against
    each candidate hash. In normal operation there is at most one match.
    """

    if not cleartext.startswith(_TOKEN_PREFIX_LITERAL):
        return None
    candidates = ApiToken.objects.filter(
        token_prefix=_prefix(cleartext), revoked_at__isnull=True
    )
    for candidate in candidates:
        try:
            _hasher.verify(candidate.token_hash, cleartext)
        except VerifyMismatchError:
            continue
        candidate.last_used_at = timezone.now()
        candidate.save(update_fields=["last_used_at"])
        return candidate
    return None
