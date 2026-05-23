# registry/

`speccify-registry` — Django-Backend für Discovery, Versionierung, Publish, Search und Yank
von Spec-Versionen. Stack: **Django 5 + DRF + Postgres + django-otp**. YAML-Bundles werden
als `BYTEA` in Postgres gespeichert (Phase-2-Entscheidung; S3-Switch ab Phase 3+).

**Aktive Phase:** Phase 2 (Registry-MVP). Plan: [`.agent/plans/phase-2-registry-mvp.md`](../.agent/plans/phase-2-registry-mvp.md).

## Stage-1-Stand

Verfügbar:

- Django-Projekt-Skelett (`speccify_registry/{settings,urls,wsgi,asgi,manage}.py`).
- App `registry_api` mit den fünf Phase-2-Modellen: `Scope`, `Spec`, `SpecVersion`, `ApiToken`, `ScopeReservation`.
- Initiale Migration `0001_initial.py` (in Git eingecheckt).
- Minimaler HTTP-Smoke: `GET /api/v1/registry/whoami` (401 anonym), `GET /api/v1/registry/specs` (leere Liste).
- Docker-Compose-Stack (Postgres 16 + Django-Dev-Server).
- 8 Tests grün via `pytest-django` (SQLite in-memory, kein Postgres nötig).

Noch offen (Stages 2–8): Auth + 2FA + Tokens, `publish`/`fetch`/`versions`, `search` + Web-UI,
`yank` + Lockfile-Schema-v2, RemoteRegistry-Resolver-Integration.

## Setup (lokal, ohne Docker)

```bash
uv sync --all-packages          # installiert registry als Workspace-Member
uv run pytest registry/         # 8 Stage-1-Tests
```

## Setup (lokal, mit Docker-Compose)

```bash
cd registry
docker-compose up --build       # startet Postgres + Django (Port 8001)
curl http://localhost:8001/api/v1/registry/whoami   # → 401
```

## Settings-Übersicht

- `SPECCIFY_REGISTRY_SECRET_KEY` — Prod-Secret (Dev-Default unsicher).
- `SPECCIFY_REGISTRY_DEBUG` — `1` schaltet `DEBUG` ein.
- `DATABASE_URL` — Postgres-DSN; ohne ihn fällt auf SQLite zurück.
- `SPECCIFY_REGISTRY_TEST=1` — schaltet auf in-memory SQLite (Tests/Smoke).

## Migrationen

```bash
uv run python -m django makemigrations registry_api
uv run python -m django migrate
```

## Tests

```bash
uv run pytest registry/ -v
```

Tests laufen ohne externe Services dank in-memory SQLite (siehe `registry/conftest.py`).
