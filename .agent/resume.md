# Resume — Speccify Phase 3

> Einstiegspunkt für die nächste Session. Letzte Aktualisierung: 2026-05-26.

## Status

- **Phase 3 aktiv.** Plan: [`plans/phase-3-codegen-targets.md`](./plans/phase-3-codegen-targets.md) (`isActive: true`).
- **Stage 0 Done** (2026-05-24) — 10 Open Questions geklärt, Decisions im Plan dokumentiert.
- **Stage 1a Done** (2026-05-25) — `Renderer`-Protocol + `TARGETS`-Registry in `core/src/speccify_core/codegen/__init__.py`; React-Renderer transparent darüber portiert; 5 neue Tests in `core/tests/test_renderer_protocol.py`; 225 Root-Pytest grün; `ruff` clean. Commits: `be848a4` (Tests) + `43462ee` (Refactor).
- **Phase 2** abgeschlossen, Tag-Vorschlag `v0.5.0-phase-2` weiterhin offen an User (selbst nicht setzen).

## Zentrale Decisions (aus Stage 0)

- Zweites + drittes Target: **SwiftUI + Angular**, beide in Phase 3.
- Codegen-Modus für **alle** Targets: **`kind: llm` + Replay-Cache** (wie real ausgelieferter React-Renderer `react_llm.py` + `ReplayCacheClient`). Korrigiert die ursprüngliche fehlerhafte Stage-0-Notiz „`kind: template`".
- Conformance-Runner MVP: **Build-Smoke + Snapshot + Visual-Regression** gegen Spec-`screenshots[]`. Voll-interaktive Tests → Phase 4.
- Workspaces: **Cargo-Stil** Root-Lockfile + **globale MVS**.
- Multi-Target: `targets: [...]`-Liste im Manifest; **Lockfile-Schema-Bump v2 → v3**, **Manifest-Schema-Bump v1 → v2**.
- Migration: Loader liest v1/v2-Bytes transparent (existierende `example-project/`-Bytes + Test-Strings bleiben unangetastet); CLI schreibt beim nächsten `lock`/`pull` v3.
- MCP-Tools target-agnostisch via Argument (Tool-Count bleibt 8).

## Nächster Schritt — Stage 1b: Lockfile v3 + Manifest v2

Outcome: Lockfile v3 mit `targets: [...]`-Cross-Product + v1/v2→v3-Loader-Migration; Manifest v2 mit `targets: list[str]` (v1 transparent lesbar); alle ~8 Adapter umgestellt; Tests grün.

Konkrete Schritte:

1. **Schema-Snapshots**: `schema/lockfile.v2.schema.json` + `schema/manifest.v1.schema.json` als Archivierungs-Snapshots anlegen (vgl. v1-Lockfile-Snapshot existiert bereits).
2. **`schema/lockfile.schema.json`** auf v3 heben: `Lockfile.targets: list[str]` top-level; `LockEntry.target` Pflicht; `generated_files_sha256` bleibt pro Entry.
3. **`schema/manifest.schema.json`** auf v2 heben: `targets: list[str]` statt `target: str`.
4. **`core/src/speccify_core/lockfile.py`**: In-Memory-Migration v1 → v2 → v3 im Loader; `build_lockfile()`-Signatur `target: str` → `targets: list[str]`.
5. **`core/src/speccify_core/manifest.py`**: `ProjectManifest.target: str` → `targets: list[str]`; v1-Manifeste mit `target: react` werden zu `targets: ["react"]`.
6. **Adapter umstellen** (~8 Aufrufer):
   - `cli/src/speccify_cli/commands/{init,add,lock,pull,verify}.py`
   - `mcp/src/speccify_mcp/...` (Resources + Tools)
   - `apps/web/backend/src/speccify_web_backend/services/render.py`
   - `registry/...` (Tests + ggf. Resolver-Pfad)
7. **Tests**: `core/tests/test_lockfile_v3.py` (Migration, Round-Trip, Multi-Target-Entries); `core/tests/test_manifest_v2.py` (v1-Compat-Read, v2-Round-Trip).
8. **Verifikation**: `uv run pytest` Root (Ziel: 225+ neue grün) + Registry-Pytest grün; `ruff check` + `ruff format --check` clean.
9. **Commit**: `feat(core): lockfile schema v3 + manifest schema v2 with migration`.

## Tooling-Reibung — gelöst (2026-05-27)

macOS `UF_HIDDEN`-Workaround läuft jetzt automatisch:

- `scripts/_venv_hygiene.py` mit `unhide_venv_pth_files` (flach, schnell) + `unhide_venv_deep` (rekursiv, opt-in).
- `conftest.py` (Root + `registry/`) hooked den flachen Sweep auf Pytest-Session-Start.
- CLI-Skript `scripts/fix-venv-hidden.sh` (mit optionalem `--deep`-Flag).
- 6 Unit-Tests in `core/tests/test_venv_hygiene.py` (4 plattformneutral + 2 macOS-gated).
- Doku in README + AGENTS.md.

Fehlende `.py`-Dateien (z. B. `django.contrib.admin.templatetags.admin_urls`) sind ein anderes Quarantäne-Symptom (gelöschte statt nur versteckte Dateien) und brauchen `uv sync --reinstall-package <name>` — dokumentiert im README-Troubleshooting-Abschnitt.

## Befehle (Spickzettel)

```bash
# Hidden-Flag entfernen (jedes Mal nach uv sync nötig)
chflags nohidden .venv/lib/python3.12/site-packages/*.pth

# Root-Tests
.venv/bin/python -m pytest -q

# Registry-Tests
cd registry && ../.venv/bin/python -m pytest -q

# Lint + Format
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

## Pflichtlektüre vor Code

1. `AGENTS.md` (Aktuelle Phase + Konventionen).
2. `.agent/agent.md` + `.agent/rules.md` (Sprache: Deutsch, Du; FP-Stil; Tests pflicht; Tags nur User).
3. `.agent/plans/phase-3-codegen-targets.md` (Decisions Stage 0 + Stages 1a Done / 1b–8 Open).
