"""Django settings for the Speccify registry backend.

Single-file settings module for the Phase-2 MVP. Production hardening
(separate `prod.py`, secrets, allowed hosts, static-files pipeline) is
deferred to Phase 7 (Polish & Launch).
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get(
    "SPECCIFY_REGISTRY_SECRET_KEY",
    # Dev-default — überschrieben in prod/CI via env.
    "dev-insecure-secret-key-do-not-use-in-prod",
)
DEBUG = os.environ.get("SPECCIFY_REGISTRY_DEBUG", "1") == "1"
ALLOWED_HOSTS: list[str] = ["*"] if DEBUG else []

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "rest_framework",
    "speccify_registry.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "speccify_registry.urls"
WSGI_APPLICATION = "speccify_registry.wsgi.application"
ASGI_APPLICATION = "speccify_registry.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


def _database_from_env() -> dict[str, object]:
    """Resolve database configuration.

    Tests and lightweight local checks fall back to SQLite (no Postgres
    service required); Docker-Compose and CI set `DATABASE_URL` or the
    individual `POSTGRES_*` env vars.
    """

    url = os.environ.get("DATABASE_URL")
    if url and url.startswith("postgres"):
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.environ.get("POSTGRES_DB", "speccify_registry"),
                "USER": os.environ.get("POSTGRES_USER", "speccify"),
                "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "speccify"),
                "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
                "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            }
        }
    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:" if os.environ.get("SPECCIFY_REGISTRY_TEST") else BASE_DIR / "db.sqlite3",
        }
    }


DATABASES = _database_from_env()

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "speccify_registry.api.authentication.BearerTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}

# How fresh a 2FA confirmation has to be for token-minting / publish / yank.
# Decision (Phase-2 Round-1, Q4): TOTP only via django-otp; default TTL 5 min.
SPECCIFY_2FA_TTL_SECONDS = int(os.environ.get("SPECCIFY_2FA_TTL_SECONDS", "300"))

# Device-code flow timing.
SPECCIFY_DEVICE_CODE_TTL_SECONDS = int(
    os.environ.get("SPECCIFY_DEVICE_CODE_TTL_SECONDS", "600")
)
SPECCIFY_DEVICE_CODE_POLL_INTERVAL_SECONDS = int(
    os.environ.get("SPECCIFY_DEVICE_CODE_POLL_INTERVAL_SECONDS", "5")
)

LOGIN_URL = "/auth/login"
LOGIN_REDIRECT_URL = "/auth/tokens"
