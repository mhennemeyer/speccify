---
sessionId: session-260522-105600-2a
isActive: true
---

# Requirements

### Overview & Goals

Phase 1 (1a–1d) ist abgeschlossen: `speccify-core` liefert den vollständigen Render-Vertrag (MVS-Resolver, Lockfile, React-LLM-Codegen via Bedrock + Replay-Cache); `speccify-cli`, `speccify-mcp` und der Browser-Playground unter `apps/web/` sind byte-identische Adapter über demselben Pipeline-Kern. Damit ist die **Lese-Seite** der Plattform (Spec → Code) gefestigt.

**Ziel von Phase 2:** Ein **Registry-MVP**, das die **Schreib-Seite** schließt — Specs werden nicht mehr nur lokal aus `registry-fixtures/` resolved, sondern können über ein hostetes Backend **publiziert, versioniert, gesucht und geyanked** werden. Damit wird Speccify von einem reproduzierbaren Codegen-Spike zu einem echten Paket-Manager-Ökosystem („npm für Specs"), wie im Master-Plan unter Phase 2 skizziert (siehe [`speccify-plan.md`](./speccify-plan.md) Z. 316–321).

Konkret soll am Ende von Phase 2 folgender End-to-End-Workflow grün laufen:
1. Ein Maintainer ruft `speccify login` und authentifiziert sich gegen das Registry (mit 2FA für Publish).
2. `speccify publish` lädt eine signierte Spec mit Hashes in das Registry hoch.
3. Ein zweiter User (oder Agent über MCP) ruft `speccify search <begriff>` und findet die Spec.
4. `speccify add @org/<name>` löst gegen das Live-Registry auf (statt gegen `registry-fixtures/`), `lock` + `pull` arbeiten wie bisher.
5. Eine Web-UI zeigt Spec-Detailseiten, Versionen, Profile und Suche.
6. Ein Maintainer kann eine fehlerhafte Version `yanken`; Lockfiles mit dieser Version warnen, neue `add`-Aufrufe lehnen sie ab.

Single Source of Truth für Phase-2-Änderungen ist dieses Dokument.

### Scope

**In Scope**
- **Django-Backend** unter `registry/` (Django 5.x + Postgres + S3-kompatibles Object-Storage für YAML-Bundles und Assets):
  - Modelle: `User`, `Scope` (`@org`), `Spec`, `SpecVersion` (mit `sha256`, `yank_status`, `published_at`, `uploader`), Membership/Permission.
  - REST-API (`/api/v1/registry/...`) für `publish`, `yank`, `search`, `fetch <id>@<version>`, `versions <id>`, `whoami`.
  - Auth via Personal Access Tokens (CLI/MCP); Web-UI via Session-Login.
  - 2FA (TOTP) **pflicht für Publish/Yank** (UI: Setup-Flow; CLI: Re-Auth-Prompt bei Token-Erstellung).
- **Web-UI** (Django-Templates **oder** Next.js-Page in `apps/web/`, Entscheidung in Step 1):
  - Suche (Volltext über `id`, `title`, `tags`, `description`).
  - Spec-Detailseite: Versionen, Akzeptanzkriterien, Inputs/Outputs, „Used by" (statisch leer in 1, ab Phase 6).
  - Profile pro `@scope` mit Spec-Liste.
- **CLI-Erweiterungen**:
  - `speccify login` / `logout` (speichert Token in `~/.config/speccify/credentials`).
  - `speccify publish` (validiert lokal, lädt YAML + Manifest-Metadaten hoch, holt signierte Quittung).
  - `speccify search <term>`.
  - `speccify yank <id>@<version> [--reason]`.
  - `speccify whoami`.
  - **Resolver-Anpassung**: zweistufige Registry-Resolution — zuerst lokales `registry-fixtures/` (Dev), dann konfigurierte Remote-Registry (`~/.config/speccify/config.toml` mit `default_registry = "https://registry.speccify.io"`). Lockfile-Feld `resolved_via` macht die Quelle nachvollziehbar.
- **MCP-Erweiterungen**: neue Tools `search(query)`, `publish(manifest_path, token_env)`, `yank(spec_ref, reason)` (Auth über Env-Var-Token; kein Browser-Login im MCP-Flow).
- **sigstore-Vorbereitung** (nicht volle Integration): Spec-Bundle-Signatur-Feld im Lockfile reservieren (`signature: { kind: "sigstore" | "none", ... }`); Default in Phase 2 ist `none`, aber API + Lockfile-Schema akzeptieren das Feld vorwärtskompatibel. Volle sigstore-Integration (Transparency Log, Verify im `verify`-Command) bleibt **explizit Phase 3+**.
- **Federation-Hooks** (vorgesehen, nicht ausgeliefert): Registry-API ist über `Host`-Header / Config-URL parametrisierbar; `speccify.yaml` darf pro Dep einen `registry`-Override tragen. „Registry-gebundene Scopes" (gegen Dependency Confusion, siehe Package-Manager-Vergleich): jeder `@scope` ist **genau einer** Registry zugeordnet; der Resolver verweigert eine Auflösung desselben Scopes über zwei verschiedene Registries.
- **Tests & CI**: Pytest gegen Django-API (mit `pytest-django`), Frontend-Tests bei Next.js-Variante (Vitest/Playwright); CI-Job `registry backend` (Postgres-Service-Container), Cross-Consistency-Test erweitert: `add` gegen ein lokal hochgezogenes Registry liefert byte-identische Lockfiles zu `add` gegen `registry-fixtures/`.
- **Doku**: `registry/README.md` (Setup, Migrations, lokales Dev-Setup mit Docker-Compose), Top-Level-`README.md`-Abschnitt „Registry (Phase 2)".
- **Master-Plan-Sync** + Tag-Vorschlag `v0.5.0-phase-2` an User.

**Out of Scope (Phase 2)**
- **Workspaces** (`workspaces: [...]` im Manifest) — auf Phase 3 verschoben (Open-Question-8-Entscheidung), um Phase 2 nicht zu überfrachten. Master-Plan-Anpassung erfolgt in Stage 9.
- **Volle sigstore-Integration** inkl. Transparency-Log-Verifikation in `speccify verify` — Phase 3+. In Phase 2 nur das Lockfile-Feld + API-Slot.
- **Federation aktiv geschaltet** (mehrere Registries indizieren sich gegenseitig) — bleibt vorbereitet, ein Demo-Setup mit zwei verbundenen Registries ist Phase 3+.
- **OAuth-Login** (Google/GitHub) für die Web-UI — Phase 2 nur Username/Passwort + TOTP. OAuth ist Phase 6 (Community & Discovery).
- **Discovery-Features**: Tags-Cloud, Trending, „Used by", semantische Suche — Phase 6.
- **Visuelle Spec-Diffs / Refinement-Diskussionen** — Phase 5.
- **Live-LLM im Backend** (Cloud-Rendering on demand) — bleibt Phase 5+ (Live-Preview).
- **Zahlungs-/Premium-Features**, Private-Registry-Tenants — Phase 7+.
- **Tauri/Desktop-Bezüge** — Phase 4 ist geparkt.
- **Echte Domain/DNS/Deploy auf `registry.speccify.io`** — Phase 2 liefert nur lokales Docker-Compose + Deploy-Doku als Anhang; tatsächlicher Live-Betrieb ist Phase 7 (Polish & Launch).

### User Stories
- *Als Spec-Autor*in* möchte ich `speccify publish` aus meinem CLI ausführen und meine Spec inkl. Hash und signierter Quittung im Registry sehen, damit ich nachweisen kann, dass meine Version unverändert ist.
- *Als Konsument*in* möchte ich `speccify search date-picker` ausführen und in <2 s eine Treffer-Liste mit Spec-IDs, Versionen und Beschreibungen sehen, damit ich nicht durch GitHub grepen muss.
- *Als Maintainer*in eines `@scope`s* möchte ich fehlerhafte Versionen yanken können (mit Begründung), damit Lockfiles davor warnen und neue Pulls sie nicht mehr ziehen.
- *Als Coding-Agent (MCP)* möchte ich `search` und `publish` aufrufen können, ohne einen Browser-Flow zu durchlaufen — Token via Env-Var reicht.
- *Als Plattform-Betreiber*in* möchte ich 2FA für Publish/Yank erzwingen, damit ein kompromittiertes Passwort nicht zur Supply-Chain-Attack führt.

### Functional Requirements
- Resolver akzeptiert sowohl lokale (`registry-fixtures/`) als auch Remote-Registries; Quelle wird im Lockfile als `resolved_via: "<url|path>"` festgehalten.
- `publish` lehnt Specs ab, deren `id`-Scope nicht zum eingeloggten User gehört (registry-gebundene Scopes).
- `publish` ist **idempotent für unveränderte Bytes** (gleicher `sha256` ⇒ 200 statt 409); echte Byte-Änderungen unter gleicher Version ⇒ 409 mit klarer Meldung.
- `yank` ändert nicht die Bytes oder den Hash, nur den `yank_status`; bestehende Lockfiles bleiben gültig, aber `verify` warnt.
- `search` ist case-insensitiv, paginiert (Default 20), liefert deterministisch sortierte Treffer (Relevanz-Score absteigend, Tie-Break: `id` alphabetisch).
- 2FA: Token-Erstellung im Web-UI verlangt frische TOTP-Bestätigung (gültig 5 min); Publish über CLI prüft Server-seitig den `2fa_verified_at`-Timestamp am Token.
- Lockfile-Feld `signature` ist optional; bei `kind: none` (Default) bleibt das Verhalten von Phase 1 unverändert.

### Non-Functional Requirements
- **Reproduzierbarkeit bleibt erhalten**: Lockfiles mit `resolved_via: <remote>` müssen offline reproduzierbar sein, sobald der Replay-Cache bzw. das gefetchte YAML lokal vorliegt. `speccify verify` arbeitet weiterhin ohne Netz, sofern Spec-Bytes lokal liegen.
- **Determinismus zwischen den drei Adaptern bleibt Vertrag**: CLI ↔ MCP ↔ Web rendern byte-identisch; Cross-Consistency-Test wird um Registry-Pfad erweitert.
- **API-Versionierung**: alle Registry-Endpoints unter `/api/v1/registry/...`; Breaking Changes brauchen Phase-Plan + Bump-Begründung.
- **Performance**: `search` (Cache-Hit) < 200 ms p95; `fetch <id>@<version>` < 300 ms p95 inkl. Object-Storage-Round-Trip im lokalen Dev-Setup.
- **Sicherheit**: Passwörter via Django-Default (`argon2`); Tokens als gehashte Strings in der DB; 2FA-Secrets verschlüsselt at rest (`django-fernet-fields` o. ä.).
- **CI bleibt vollständig offline**: das Registry-Backend wird in CI gegen ein temporäres Postgres + lokales MinIO/Filesystem-Backend getestet; keine externen Services nötig.


# Technical Design

### Current Implementation (nach Phase 1d)
- `speccify-core` exponiert `LocalRegistry` (FS-basiert, `registry-fixtures/<scope>/<name>/<version>/spec.speccify.yaml`) als einzige Registry-Quelle.
- Lockfile-Schema (`schema/lockfile.schema.json`) kennt `resolved_via` bereits als String-Feld, hat aber **kein** `signature`-Feld und **keine** Yank-Information.
- CLI/MCP haben weder Auth noch `publish`/`search`/`yank`.
- `registry/` existiert als Verzeichnis im Repo-Layout, ist aber leer (siehe `AGENTS.md`).
- `apps/web/` ist als Browser-Playground belegt; Frage in Step 1: Web-UI als Django-Template oder zusätzlicher Bereich im bestehenden Next.js-Frontend.

### Key Decisions (noch offen — siehe „Open Questions")
1. **Django-Backend vs. FastAPI**: Master-Plan-Empfehlung ist Django (Z. 278, „Bestehende Erfahrung im Team"). Wird in Step 1 final bestätigt.
2. **Web-UI in Django-Templates vs. Next.js**: Django-Templates sind schneller fertig und brauchen kein zweites Deployment; Next.js teilt sich das Tooling mit dem Playground. Empfehlung tendiert zu Django-Templates für MVP; Re-Use von `apps/web/`-Komponenten bleibt Phase 5+.
3. **Object-Storage**: S3-kompatibel (MinIO im Dev, AWS S3 / Cloudflare R2 in Prod). Lokales Dev nutzt MinIO via Docker-Compose.
4. **Token-Speicherung CLI**: `~/.config/speccify/credentials` als TOML mit `chmod 0600`; keine OS-Keychain in MVP (plattform-portabel, Phase 7-Polish).
5. **2FA**: TOTP (RFC 6238) via `django-otp` + `qrcode`. WebAuthn ist Phase 6+.
6. **Resolver-Caching**: Remote-Fetches werden in `~/.cache/speccify/registry/<host>/<scope>/<name>/<version>/spec.speccify.yaml` gespiegelt; `verify` läuft danach offline. Cache-Invalidation ausschließlich über Hash-Mismatch (Spec-Bytes ändern sich nicht unter derselben Version).

### Proposed Changes (high-level — Detail-Stages folgen in Round 2)

#### 1. Workspace-Erweiterung
- Top-Level `pyproject.toml` um `registry/` als uv-Workspace-Member erweitern.
- Neues Python-Paket `registry/` (`speccify-registry`): `pyproject.toml` mit `django>=5.1`, `psycopg[binary]`, `djangorestframework`, `django-otp`, `boto3` (S3), `pytest-django`.
- `registry/docker-compose.yml` für lokales Dev (Postgres + MinIO + Django-Server).

#### 2. Registry-API (REST, `/api/v1/registry/...`)
```
GET    /api/v1/registry/specs?q=<term>&page=<n>     # search, paginiert
GET    /api/v1/registry/specs/<scope>/<name>        # versions list + meta
GET    /api/v1/registry/specs/<scope>/<name>/<ver>  # fetch (YAML + sha256 + yank_status)
POST   /api/v1/registry/specs                       # publish (multipart: yaml + manifest)
POST   /api/v1/registry/specs/<scope>/<name>/<ver>/yank   # yank with reason
GET    /api/v1/registry/whoami                      # token introspection
POST   /api/v1/registry/tokens                      # create token (requires fresh 2FA)
```

#### 3. CLI- & MCP-Adapter
- `cli/src/speccify_cli/commands/{login,publish,search,yank,whoami}.py` als Adapter über `speccify_core.registry.RemoteRegistry` (neu).
- `core/src/speccify_core/registry.py`: `Registry`-Protocol mit `LocalRegistry` und `RemoteRegistry` als Implementierungen. Resolver akzeptiert eine Liste von Registries (Resolution-Strategie: erste gefundene Spec gewinnt; Konflikt-Detection bei doppelten Scopes über zwei Registries → `ConflictError`).
- `mcp/src/speccify_mcp/tools/{search,publish,yank}.py` analog; Auth via Env-Var `SPECCIFY_TOKEN`.

#### 4. Lockfile-Schema-Erweiterung
- `schema/lockfile.schema.json` ergänzt:
  - `signature` (optional): `oneOf` mit `{kind: "none"}` (Default) und `{kind: "sigstore", certificate, rekor_log_index}` (reserviert, in 2 nicht befüllt).
  - `yank_status` (optional, pro `LockEntry`): `none | yanked` plus `yank_reason` — wird beim `lock`-Aufruf gegen das Registry frisch geprüft und vom `verify`-Command gemeldet.

#### 5. Web-UI (Django-Templates, MVP)
- `registry/templates/`: `base.html`, `search.html`, `spec_detail.html`, `scope_profile.html`, `2fa_setup.html`.
- Auth-Flow: Login → Optional-2FA-Setup → Token-Verwaltung. Sessions via Django-Default.

### Tests
- `registry/tests/test_api.py`: publish (happy + idempotent + scope-mismatch + 2FA-missing), search, yank, fetch, versions.
- `registry/tests/test_models.py`: Constraints, scope-membership, yank semantics.
- `core/tests/test_remote_registry.py`: gegen `responses`-/`httpx-mock`-Fixture; Cross-Consistency mit `LocalRegistry`.
- `cli/tests/test_publish.py`, `cli/tests/test_search.py`, `cli/tests/test_yank.py`.
- Cross-Consistency-Erweiterung in `apps/web/backend/tests/test_cross_consistency.py`: gleicher Spec-Pfad gegen RemoteRegistry-Mock liefert byte-identische Outputs.


# Decisions (Round-1-Klärung mit User abgeschlossen, 2026-05-23)

1. **Backend-Framework**: **Django 5.x** (Master-Plan-Default; Admin/Auth/Migrations out of the box).
2. **Web-UI-Stack**: **Django-Templates** in `registry/templates/` (eine Deployment-Einheit, schneller MVP). Re-Use von `apps/web/`-Komponenten bleibt Phase 5+.
3. **Storage-Backend**: **Postgres `BYTEA`** für Spec-YAML-Bundles (eine Infra-Komponente weniger). S3-Switch ab Phase 3+ oder bei großen Assets.
4. **2FA-Methode**: **TOTP only** (RFC 6238 via `django-otp` + `qrcode`). WebAuthn bleibt Phase 6.
5. **Token-Format**: **Opaque Random-Strings** (npm-Stil, gehasht in DB gespeichert).
6. **`speccify login`-UX**: **Device-Code-Flow** (`gh auth login`-Stil). Bahnt Phase-6-OAuth-Switching.
7. **Scope-Vergabe**: **Self-Service** mit Reservierungs-/Sperrliste für gängige Wörter und Trademarks.
8. **Workspaces**: **Auf Phase 3 verschoben** — Stage 7 entfällt im Phase-2-Plan; Master-Plan in Stage 9 entsprechend anpassen.
9. **Web-UI-Ort**: **In `registry/`** (Web-UI gehört zum Registry-Backend, gemeinsamer Deploy).
10. **Default-Registry-Hostname**: **Kein Hardcoding** — `~/.config/speccify/config.toml` muss `default_registry` setzen; keine Annahme über Domain-Status in Phase 2.


# Stages

| Stage | Outcome | Status |
|---|---|---|
| 0 | Open Questions geklärt, Architektur-Entscheidungen dokumentiert, Round-2-Delivery-Steps geschrieben. | **Done** (2026-05-23) |
| 1 | Django-Skeleton + Modelle + Migrations + lokales Docker-Compose; `registry`-Workspace; erste Smoke gegen leeres Registry. | **Done** (2026-05-23) |
| 2 | Auth + 2FA + Tokens + `speccify login`/`whoami`. | **Done** (2026-05-23) |
| 3 | `publish` + `fetch` + `versions` API + CLI/MCP-Adapter; idempotenter Re-Publish. | **Done** (2026-05-24) — Backend + CLI + MCP-Tool `publish` |
| 4 | `search` API + Web-UI (Suche + Detail + Profil). | **Done** (2026-05-24) — Backend + Web-UI |
| 5 | `yank` + Lockfile-Bump auf `schema_version: 2` (`yank_status`, `signature`-Slot); `verify`-Warnung. | **Done** (2026-05-24) — Backend + CLI + MCP + Lockfile v2 + verify-Warnung |
| 6 | RemoteRegistry-Integration im Resolver (zweistufig, Konflikt-Detection); Lockfile-`resolved_via` für Remote-Pfade. | Open |
| 7 | CI: Registry-Job mit Postgres-Service-Container; Cross-Consistency-Erweiterung; Performance-Smoke (`search` p95 < 200 ms). | Open |
| 8 | Master-Plan-Sync + `AGENTS.md`-Phasen-Update + Phasen-Plan-Archivierung + Tag-Vorschlag `v0.5.0-phase-2`. | Open |


# Risks & Mitigations

| Risiko | Wahrscheinlichkeit | Mitigation |
|---|---|---|
| **Phase 2 zu groß** (Backend + Auth + 2FA + Web-UI + 4 neue CLI-Commands + Lockfile-Bump) | hoch | Strikt nach Stages liefern; Workspaces bereits per Round-1-Entscheidung auf Phase 3 verschoben. Stage 4 (Web-UI) ist der nächste Kandidat zum Splitten, falls Backend-Stages länger dauern; sigstore bleibt als reiner Lockfile-Slot in Stage 5, volle Integration explizit Phase 3+. |
| **2FA-UX schiebt MVP** | mittel | TOTP-only halten, kein WebAuthn; Setup-Flow als reine Django-Form (kein JS-Framework). |
| **Registry-Auth schiebt CI** (Tokens in CI-Secrets) | mittel | CI nutzt ausschließlich lokal hochgezogenes Registry mit Test-Fixture-Tokens, keine echten Credentials. |
| **Resolver-Komplexität durch zweistufige Registries** | mittel | Konflikt-Detection (gleicher Scope in zwei Registries → harter Fehler) ist einziger neuer Regel-Pfad; ausführliche Tests in `core/tests/test_resolver.py`. |
| **sigstore-Feld im Lockfile bricht Phase-1-Lockfiles** | niedrig | Feld als optional einführen, Default `kind: none`; `schema_version: 2`-Bump nur, wenn das Yank-Feld dazu kommt, das ebenfalls optional bleibt. |
| **Federation-Hooks zu offen** | niedrig | In Phase 2 nur `registry`-Override pro Dep akzeptieren; echtes Cross-Registry-Indizieren bleibt Phase 3+. |
| **Storage-Wahl unklar** | niedrig | Entschieden in Decision 3: Postgres-`BYTEA` für MVP; S3-Switch ab Phase 3 oder bei großen Asset-Bundles. |


# Delivery Steps

### Step 1: Stage 1 — Django-Skeleton, Modelle, Migrations, Docker-Compose

Neues uv-Workspace-Member `registry/` mit Django-5-Skeleton lädt grün, läuft lokal via `docker-compose up`, hat erstmigrierte Modelle und einen passing Smoke-Test gegen leere Registry-API.

- Top-Level `pyproject.toml`: `registry/` als uv-Workspace-Member ergänzen.
- `registry/pyproject.toml` (Paket `speccify-registry`): `django>=5.1`, `djangorestframework`, `psycopg[binary]>=3.2`, `django-otp>=1.5`, `qrcode>=8`, `argon2-cffi`, Dev-Group: `pytest-django`, `pytest`, `responses`.
- `registry/speccify_registry/` Django-Projekt-Layout: `settings.py` (Postgres via `DATABASE_URL`, `argon2`-Passwort-Hasher, `INSTALLED_APPS` inkl. `django_otp`, `django_otp.plugins.otp_totp`), `urls.py`, `wsgi.py`, `asgi.py`.
- App `registry/speccify_registry/api/` mit Modellen:
  - `User` (Django-Standard via `AbstractUser`).
  - `Scope` (`name` unique, `owner` FK→User, `created_at`, `is_reserved` bool für Sperrliste).
  - `Spec` (`scope` FK, `name`, `description`, `tags` JSON; unique constraint `(scope, name)`).
  - `SpecVersion` (`spec` FK, `version` SemVer-String, `yaml_bytes` `BinaryField`, `sha256` indexed, `uploader` FK→User, `published_at`, `yank_status` enum `none|yanked`, `yank_reason` nullable; unique constraint `(spec, version)`).
  - `ApiToken` (`user` FK, `token_hash` argon2, `label`, `created_at`, `last_used_at`, `revoked_at` nullable, `requires_2fa` bool, `last_2fa_verified_at` nullable).
  - `ScopeReservation` (statische Tabelle mit gesperrten Namen wie `admin`, `speccify`, `org`, gängige Brand-Namen).
- Migrations generieren (`0001_initial.py`), in Git eingecheckt.
- `registry/docker-compose.yml`: Postgres 16 + Django-Dev-Server (`runserver 0.0.0.0:8001`). `Dockerfile.dev` mit `uv sync` + `manage.py migrate` als Entrypoint.
- `registry/README.md`: Setup, Migrations, `docker-compose up`, Test-Befehle.
- Tests `registry/tests/test_models.py`: Scope-Constraint, SpecVersion-Unique, Yank-Status-Default, Token-Hash nicht im Klartext gespeichert.
- Smoke-Test `registry/tests/test_api_smoke.py`: `GET /api/v1/registry/whoami` (anonym → 401), `GET /api/v1/registry/specs?q=foo` (leere Liste).
- Commit: `feat(registry): add django skeleton, models and docker-compose`.

### Step 2: Stage 2 — Auth, 2FA, Tokens, `speccify login`/`whoami`

User-Registrierung + Login (Web), TOTP-Setup-Flow, API-Token-Erstellung mit frischem 2FA-Check, CLI `login` (Device-Code) + `whoami` arbeiten gegen lokales Registry.

- Django-Views in `registry/speccify_registry/web/`: `signup`, `login`, `logout`, `2fa_setup` (QR-Code via `qrcode`), `2fa_verify`, `tokens` (Liste + Erstellen + Revoke).
- 2FA: `django_otp.plugins.otp_totp.models.TOTPDevice`; `confirmed=True` erst nach erfolgreichem Verify; `ApiToken.last_2fa_verified_at` wird beim Erstellen gesetzt (max 5 min alt sein darf).
- REST-Endpoints in `registry/speccify_registry/api/views.py`:
  - `POST /api/v1/registry/auth/device-code` → `{device_code, user_code, verification_url, expires_in, interval}`.
  - `POST /api/v1/registry/auth/device-code/poll` → `{token}` oder `{status: "pending"|"expired"|"denied"}`.
  - `GET /api/v1/registry/whoami` (Bearer-Token) → `{username, scopes}`.
  - `POST /api/v1/registry/tokens` (Session-Auth + 2FA-Required) → erstellt Token, gibt Klartext **einmalig** zurück.
- CLI `cli/src/speccify_cli/commands/login.py`:
  - `speccify login [--registry URL]` startet Device-Code-Flow, druckt `user_code`, öffnet Browser via `webbrowser.open`, pollt im Intervall.
  - Speichert Token in `~/.config/speccify/credentials.toml` (`chmod 0600`) als `[registries.<host>] token = "..."`.
- CLI `cli/src/speccify_cli/commands/whoami.py`: liest Credentials, ruft `whoami`, druckt `username + scopes`.
- Neuer Helper `cli/src/speccify_cli/_credentials.py`: load/save TOML, Permissions-Check.
- Tests:
  - `registry/tests/test_auth.py`: Signup, Login, 2FA-Setup mit korrektem/falschem Code, Token-Erstellung ohne frischen 2FA-Check → 403.
  - `registry/tests/test_device_code.py`: Happy-Path, Polling-Pending, Expired.
  - `cli/tests/test_login.py` (Registry-Server via `pytest-django` + `live_server`): Device-Code-Flow mit `webbrowser.open` gemockt; Credentials-Datei mit `0600`.
  - `cli/tests/test_whoami.py`.
- Commit: `feat(registry,cli): add auth, 2fa, tokens and speccify login/whoami`.

### Step 3: Stage 3 — `publish` + `fetch` + `versions` API + CLI/MCP-Adapter

Maintainer kann `speccify publish` aufrufen; Spec landet im Registry; `fetch`+`versions` liefern sie zurück; idempotenter Re-Publish bei identischen Bytes.

- REST-Endpoints:
  - `POST /api/v1/registry/specs` (multipart: `yaml_file`, `manifest_json`): validiert Spec gegen `spec.schema.json` (Re-Use `speccify-core.SchemaValidator`), prüft Scope-Ownership des Token-Users, speichert `SpecVersion` mit `sha256(yaml_bytes)`. Bei identischen Bytes unter gleicher Version → 200; bei Byte-Drift → 409.
  - `GET /api/v1/registry/specs/<scope>/<name>` → Liste der Versionen + Meta (yank_status, published_at).
  - `GET /api/v1/registry/specs/<scope>/<name>/<version>` → YAML-Bytes + `sha256` + `yank_status` + `published_at`.
- Scope-Reservation: Vor erstem Publish prüfen, ob `Scope` existiert; falls nicht und nicht in `ScopeReservation`, automatisch claimen und User als Owner setzen.
- CLI `cli/src/speccify_cli/commands/publish.py`: liest `speccify.yaml` der gepublishten Spec, validiert lokal, sendet multipart-POST, schreibt Server-Quittung (Hash + URL) nach stdout.
- MCP-Tool `mcp/src/speccify_mcp/tools/publish.py`: gleiche Logik, Auth über Env `SPECCIFY_TOKEN`.
- Tests:
  - `registry/tests/test_publish.py`: happy, idempotent (gleiche Bytes), conflict (geänderte Bytes), scope-mismatch (Token-User != Scope-Owner) → 403, invalid YAML → 400, stale 2FA → 403.
  - `cli/tests/test_publish.py`: gegen `live_server`; nach Publish ist `GET versions` korrekt.
  - `mcp/tests/test_publish_tool.py`.
- Commit: `feat(registry,cli,mcp): add publish, fetch and versions endpoints`.

### Step 4: Stage 4 — `search` API + Web-UI (Suche, Detail, Profil)

User können Specs über Web-UI und CLI suchen; Detailseiten zeigen Versionen + Akzeptanzkriterien; Scope-Profile listen alle Specs.

- REST-Endpoint `GET /api/v1/registry/specs?q=<term>&page=<n>&per_page=<n>`:
  - Volltext-Suche via Postgres `to_tsvector` über `Spec.name`, `Spec.description`, `Spec.tags`, `Scope.name`.
  - Paginiert (Default 20, max 100), Sortierung: ts_rank DESC, dann `scope/name` alphabetisch.
  - Response: `{results: [{id, latest_version, description, tags, yank_status}], total, page, per_page}`.
- Django-Templates:
  - `base.html` (Navigation, Login-Status).
  - `search.html` (Form + Result-List + Pagination).
  - `spec_detail.html` (Versionen-Tabelle, Akzeptanzkriterien aus latest YAML, Yank-Hinweis bei `yanked`).
  - `scope_profile.html` (Scope-Header, Spec-Liste).
- Views in `registry/speccify_registry/web/views.py`: `search_view`, `spec_detail_view`, `scope_profile_view`. URL-Routing in `urls.py`.
- CLI `cli/src/speccify_cli/commands/search.py`: ruft API, druckt Tabelle (Rich).
- MCP-Tool `mcp/src/speccify_mcp/tools/search.py`.
- Performance: GIN-Index auf `to_tsvector(name || description || tags)`; Migration `0002_search_index.py`.
- Tests:
  - `registry/tests/test_search.py`: case-insensitive, paginierung, deterministisch sortiert, leere Query, Tag-Match.
  - `registry/tests/test_web_views.py`: Search-Page rendert, Spec-Detail rendert (auch yanked), Scope-Profile.
  - `cli/tests/test_search.py`, `mcp/tests/test_search_tool.py`.
- Commit: `feat(registry,cli,mcp): add search api and web ui`.

### Step 5: Stage 5 — `yank` + Lockfile-Bump auf `schema_version: 2` (yank_status, signature-Slot)

Maintainer können Versionen yanken; Lockfile-Schema kennt `yank_status` und `signature`-Slot; `verify` warnt bei yanked Versionen; existierende Phase-1-Lockfiles bleiben kompatibel.

- REST-Endpoint `POST /api/v1/registry/specs/<scope>/<name>/<version>/yank` (Body: `{reason}`): setzt `yank_status=yanked`, `yank_reason`, prüft Scope-Ownership + frisches 2FA.
- CLI `cli/src/speccify_cli/commands/yank.py`: `speccify yank @org/foo@0.1.2 --reason "..."`.
- MCP-Tool `mcp/src/speccify_mcp/tools/yank.py`.
- `schema/lockfile.schema.json` Bump auf `schema_version: 2`:
  - Pro `LockEntry`: optional `yank_status: "none"|"yanked"` (Default `none`), optional `yank_reason: string`.
  - Top-Level: optional `signature: oneOf [{kind: "none"}, {kind: "sigstore", certificate, rekor_log_index}]` (Default `none`, in Phase 2 immer `none`).
  - Backward-compat: `schema_version: 1`-Lockfiles werden weiter geladen (warning), beim nächsten `lock` auf 2 hochgezogen.
- `core/src/speccify_core/lockfile.py`: `LockEntry.yank_status`, `Lockfile.signature`-Felder als immutable Dataclasses; Migrations-Helper `migrate_v1_to_v2`.
- `cli/src/speccify_cli/commands/lock.py` + `verify.py`: nach Resolve frisch yank_status vom Registry holen; `verify` exit 0 + Warning bei yanked, exit 1 bei Bytes-Drift wie bisher.
- Tests:
  - `registry/tests/test_yank.py`: happy, idempotent (zweites yank), un-yank ist verboten (out of scope), scope-mismatch → 403.
  - `core/tests/test_lockfile_v2.py`: Round-Trip v2, v1-Migration, signature-none-Default.
  - `cli/tests/test_verify_yank.py`: verify warnt bei yanked, fail-Verhalten dokumentiert.
  - `cli/tests/test_yank.py`, `mcp/tests/test_yank_tool.py`.
- Commit: `feat(registry,cli): add yank and bump lockfile schema to v2 with yank_status and signature slot`.

### Step 6: Stage 6 — RemoteRegistry-Integration im Resolver (zweistufig)

`speccify-core` kann gegen Live-Registry resolven; Lockfile-`resolved_via` zeigt auf Remote-URL; Cross-Registry-Konflikt wird hart abgefangen.

- `core/src/speccify_core/registry.py` refactor:
  - `Registry` als `Protocol` mit `list_versions(spec_id) -> list[Version]` und `fetch(spec_id, version) -> SpecBundle`.
  - `LocalRegistry` bleibt; neue `RemoteRegistry(base_url, token, cache_dir)` mit `httpx`-Client + lokalem File-Cache unter `~/.cache/speccify/registry/<host>/<scope>/<name>/<version>/spec.speccify.yaml`.
  - Cache-Invalidation: ausschließlich bei Hash-Mismatch (Server-Hash != Cached-Hash) → harter Fehler.
  - Resolver akzeptiert `list[Registry]`; Strategie: erste passende Registry pro Spec-ID gewinnt, aber **derselbe Scope** darf nur über **eine** Registry kommen — Konflikt → `ConflictError`.
- `cli/src/speccify_cli/_config.py`: lädt `~/.config/speccify/config.toml` mit `default_registry`-Pflicht-Feld (kein Hardcoding), liest `[registries.<host>]`-Token aus `credentials.toml`.
- `speccify add` / `lock` nutzen Registry-Liste `[LocalRegistry("registry-fixtures/")]` im Dev-Mode-Default, `[RemoteRegistry(default_url)]` in Prod-Setup.
- Lockfile `resolved_via` = absolute URL bei Remote, sonst Pfad.
- Tests:
  - `core/tests/test_remote_registry.py` (via `responses`-Mock): list, fetch, cache-write, hash-mismatch.
  - `core/tests/test_resolver_multi.py`: zwei-Registry-Resolve, Scope-Konflikt → `ConflictError`.
  - `cli/tests/test_add_remote.py` (gegen `live_server`).
- Commit: `feat(core,cli): add remote registry resolver with two-tier strategy and scope conflict detection`.

### Step 7: Stage 7 — CI-Integration + Performance-Smoke + Cross-Consistency-Erweiterung

CI-Job `registry backend` läuft gegen Postgres-Service-Container; Cross-Consistency-Test deckt Registry-Pfad ab; `search`-Performance bleibt unter 200 ms p95 im lokalen Smoke.

- `.github/workflows/ci.yml`: neuer Job `registry backend (django)`:
  - `services: postgres:16-alpine` mit Health-Check.
  - `uv sync --all-packages`, `uv run --package speccify-registry python -m manage migrate`, `uv run --package speccify-registry pytest registry/tests -v`.
- Cross-Consistency-Test `apps/web/backend/tests/test_cross_consistency.py` erweitern um Registry-Pfad: gleiche Spec, einmal via `LocalRegistry`, einmal via `RemoteRegistry` (gegen lokal hochgezogenes Django-Test-Backend) → byte-identische TSX-Outputs.
- Performance-Smoke `registry/tests/test_search_perf.py`: 100 Specs einfügen, `search` 50× ausführen, p95 < 200 ms (eher Sanity-Check als harte Gate; nur lokal, nicht in CI als blocking).
- `cli/tests/` und `mcp/tests/`: jeweils einen Registry-Live-Test gegen `live_server` als Smoke.
- Commit-Folge: `chore(ci): add registry backend job with postgres service`, `test(apps/web): extend cross-consistency to registry path`.

### Step 8: Stage 8 — Master-Plan-Sync, AGENTS.md, Archivierung, Tag-Vorschlag

Master-Plan reflektiert Phase 2 als abgeschlossen; `AGENTS.md`-Sektion „Aktuelle Phase" auf Phase 3 zeigend; Phase-2-Plan archiviert; Tag-Vorschlag `v0.5.0-phase-2` an User.

- `.agent/plans/speccify-plan.md`:
  - Phase 2 als „abgeschlossen" markieren mit Stichpunkten zu Backend, Auth, Publish/Search/Yank, Lockfile-v2, RemoteRegistry.
  - Workspaces aus Phase-2-Scope explizit nach Phase 3 verschoben (mit Begründung).
  - Lockfile-Schema-Beispiel um `signature` + `yank_status` ergänzen.
  - Tool-Vertrag `/api/v1/registry/...` inline dokumentieren (Endpoints, Auth, Fehler-Codes).
- `AGENTS.md`:
  - „Aktuelle Phase" auf „Phase 2 abgeschlossen — Phase 3 (zweites Codegen-Target + Workspaces) als nächstes".
  - Archiv-Verweise auf `archive/phase-2-registry-mvp.md`.
- `.agent/status.md` aktualisieren: Phase 2 als abgeschlossen, Test-Anzahl, Tag-Vorschlag, nächste Schritte = Phase-3-Plan-Skelett.
- Phasen-Plan archivieren: `.agent/plans/phase-2-registry-mvp.md` → `.agent/plans/archive/phase-2-registry-mvp.md`, `isActive: false`.
- Tag-Vorschlag `v0.5.0-phase-2` an User dokumentieren (selbst nicht setzen, vgl. `.agent/rules.md`).
- Commits: `feat(registry): complete phase 2 registry mvp`, `docs(plan): sync master plan with phase 2 outcomes`, `docs(plan): archive phase 2, kickoff phase 3 placeholder`.
