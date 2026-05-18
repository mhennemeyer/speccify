# Projektstatus: Speccify

## Meta
- **Typ:** Code
- **Phase:** Phase 1b **abgeschlossen** und getaggt (`v0.1.0-phase-1a` → `d28cb33`, `v0.2.0-phase-1b` → `8c90511`, lokal annotated; kein Git-Remote konfiguriert, also kein Push). **Phase 1c läuft**: Phasen-Plan `.agent/plans/phase-1c-mcp-server.md` aktiv. **Steps 0–5 abgeschlossen** (2026-05-16): SDK `mcp[cli]>=1.27.1,<2.0` gepinnt; Server-Skeleton + Read-only Tools `resolve`/`lint`/`render` + Write-Tools `lock`/`pull`/`verify` + Resources `speccify://manifest|lockfile` und `spec://{scope}/{name}@{version}` + Prompt `add-spec` (dünne Adapter über `speccify_core`). Cross-Consistency CLI ↔ MCP byte-identisch. Step 5: `scripts/mcp_smoke.py` (stdio-Roundtrip mit `mcp`-Client, offline, prüft `tools/list` + `tools/call render` + `resources/read manifest`), Pytest-Wrapper `mcp/tests/test_stdio_smoke.py`, CI-Step `speccify-mcp smoke (stdio, offline)`, `mcp/README.md` neu + Top-Level-README ergänzt. **174 Tests grün**, ruff/format clean. Nächster Schritt: Step 6 (Master-Plan-Sync + `AGENTS.md` auf 1d + Tag-Vorschlag `v0.3.0-phase-1c`).
- **Priorität:** Mittel
- **Zuletzt aktualisiert:** 2026-05-16

## Beschreibung
Spec-First-Plattform für sprach-/framework-unabhängige Komponenten-Spezifikationen.
Phase 0 etabliert das Spec-Schema v0, den Validator und die CLI `speccify lint` als
Fundament für alle weiteren Phasen.

## Aktueller Stand
- `schema/spec.schema.json` v0 vorhanden (Draft 2020-12).
- `speccify_core` enthält `SpecLoader` + `SchemaValidator` mit Tests.
- `speccify_cli` mit Sub-Command `lint` (Typer); `speccify lint specs/*.yaml` läuft grün.
- 5 Referenz-Specs unter `specs/` (button, contact-form, http-api-client,
  onboarding-wizard, login-screen) — alle valide.
- Pytest grün (12 Tests). Ruff/Format-Check/Mypy grün.
- Dev-Tooling vollständig: `ruff`, `mypy`, `types-PyYAML` als Dev-Deps gepinnt.
- GitHub-Actions-Workflow `.github/workflows/ci.yml` deckt Lint + Format-Check +
  Mypy + Pytest + `speccify lint` ab.

## Nächste Schritte
- [x] Phase 1b Step 1 — `speccify init <name> [--target react]` (minimal:
      nur `speccify.yaml`, kein Skeleton). 7 neue CLI-Tests grün, alle 81
      Tests grün, ruff/format/mypy clean.
- [x] Phase 1b Step 2 — Lockfile-Schema-Erweiterung `generator.oneOf`
      (`template`/`llm`), neuer `LlmGeneratorPin` + `AnyGeneratorPin`-Union,
      `TemplateGeneratorPin`-Alias für Rückwärtskompatibilität. 4 neue Tests
      grün (LLM mit/ohne `seed`, gemischtes Lockfile, Schema-Reject bei
      kombinierten Feldern), 85 Tests gesamt grün, ruff/format/mypy clean.
- [x] Phase 1b Step 3 — Replay-Cache + `LlmClient`-Protokoll
      (`speccify_core.codegen.replay`: `CacheKey`/`ReplayCache`/`CacheMissError` +
      `LlmClient`-Protokoll + `ReplayCacheClient`-Wrapper mit `bind_key`-Vertrag).
      15 neue Tests grün, 100 Tests gesamt, ruff/format/mypy clean.
- [x] Phase 1b Step 4 — React-LLM-Adapter (`speccify_core.codegen.react_llm`)
      mit LLM-Pin, Prompt-Template, minimaler Normalisierung, Klammer-Heuristik
      für TSX-Validität, PascalCase-Output (`<scope>/<Name>.tsx`); Dispatcher
      `render_for_target` + `TargetRender` + `SUPPORTED_TARGETS=("react",)`;
      Re-Exports in `speccify_core.__init__`. 20 neue Tests grün, 120 Tests
      gesamt, ruff/format/mypy clean. `pull`/`verify` bleiben in Step 4 noch
      beim Stub — Umstellung ist Step-5-Aufgabe.
- [x] Phase 1b Step 5a — **Provider-Switch von Anthropic auf AWS Bedrock**
      (firmenweite Default-Infrastruktur). Live-`BedrockClient`
      (`speccify_core.codegen.bedrock_client`) via `boto3` `converse`,
      Modell-Pin `bedrock/eu.anthropic.claude-opus-4-7` (`eu-central-1`),
      `temperature` weggelassen (deprecated für Opus-4-7),
      Standard-AWS-Credential-Chain. `boto3>=1.35` als optional-Dep
      `speccify-core[bedrock]` (+ Workspace-Mirror). Maintainer-Skript
      `scripts/record_llm_cache.py` umgestellt, eingebauter `.env`-Loader.
      10 neue Tests in `core/tests/test_bedrock_client.py` (Modell-Strip,
      fehlendes `boto3`, Text-Block-Extraktion via Fake-boto3, Region,
      Default-Chain, Schema-Fehler, Exception-Wrapping). **Live-Aufnahme
      erfolgreich**: 6/6 Cache-Einträge unter `tests/fixtures/llm-cache/`
      (~36 KB) eingecheckt. 131 Tests grün, ruff/format/mypy clean.
- [x] Phase 1b Step 5b — `pull`/`verify` umgestellt auf
      `render_for_target(spec, target, llm_client=...)`. Neue Flags
      `--offline/--no-offline` (Default offline) und `--cache-dir`
      (Default-Repo-Pfad `tests/fixtures/llm-cache`, Env-Override
      `SPECCIFY_CACHE_DIR`) auf `pull` und `verify`. Gemeinsamer Helper
      `speccify_cli.commands._llm_client.build_replay_client`. `pull`
      schreibt `LlmGeneratorPin` (`provider=bedrock`, `model`,
      `prompt_version`, `seed`, `cache_key=sha256:<digest>`) pro Spec
      ins Lockfile. `verify` prüft Modell-/Prompt-/Seed-/Cache-Key-Drift
      gegen Re-Render und meldet harte Cache-Misses. Neue Helper-Methode
      `Lockfile.with_generator(spec_id, generator)`. example-project
      regeneriert: 3 TSX-Dateien (`org/Button.tsx`, `org/ContactForm.tsx`,
      `org/OnboardingWizard.tsx`), Lockfile enthält LLM-Pins. 9 neue
      CLI-Tests (5 `test_pull.py` inkl. Determinismus + offline-Miss,
      6 `test_verify.py` inkl. Modell-Drift + Disk-Drift). **134 Tests
      grün**, ruff/format clean.
- [x] Phase 1b Step 5c — CI-Workflow um E2E-Smoke erweitert: bestehender
      `example-project`-Step nutzt explizit `--offline` für `pull`/`verify`;
      neuer Step `init + add + lock + pull + verify` läuft in `mktemp -d`
      gegen `registry-fixtures/` und `tests/fixtures/llm-cache/` (Binary
      direkt aus `.venv/bin/speccify`, weil `uv run` aus fremder CWD den
      Workspace-Kontext verliert). `README.md` erweitert um End-to-End-
      Smoke und Maintainer-Doku zu `scripts/record_llm_cache.py`. Lokal
      1:1 nachgestellt — beide Smoke-Pfade grün. 134 Tests grün,
      ruff/format clean.
- [x] Phase 1b Step 6 — Master-Plan-Sync: `speccify-plan.md` markiert Phase 1b als abgeschlossen (React-LLM/Bedrock/Replay-Cache + `pull`/`verify --offline` + CI-E2E), `AGENTS.md` „Aktuelle Phase" auf 1c umgestellt, Phasen-Plan-Step 5c + 6 abgehakt. Tag `v0.2.0-phase-1b` als Vorschlag an User offen (nicht selbst gesetzt).
- [x] Annotated Tags lokal gesetzt: `v0.1.0-phase-1a` (→ `d28cb33`) und `v0.2.0-phase-1b` (→ `8c90511`). Kein Git-Remote vorhanden → Push entfällt; User kann später `git push --tags` ausführen.
- [x] Phasen-Plan `.agent/plans/phase-1c-mcp-server.md` geschrieben (MCP-Server `speccify-mcp`, stdio-only, 6 Tools = CLI-1:1, Replay-Cache-offline-CI, Tag-Vorschlag `v0.3.0-phase-1c`).
- [x] **Phase 1c Step 0** — `mcp[cli]>=1.27.1,<2.0` in `mcp/pyproject.toml` gepinnt (PyPI-Latest 1.27.1, Extra `cli`, `requires_python>=3.10`); `uv sync --all-packages` + `uv.lock` aktualisiert; `uv run pytest` → 134 grün; ruff clean.
- [x] **Phase 1c Step 1** — Server-Skeleton: `speccify_mcp.server.build_server(ServerConfig)` liefert `FastMCP(name="speccify-mcp")` ohne Tools/Resources/Prompts; `speccify_mcp.cli:main` mit Argparse (`--project`/`--log-level`), Env-Fallback (`SPECCIFY_PROJECT_ROOT`/`SPECCIFY_LOG_LEVEL`), stderr-Logging, `server.run(transport="stdio")`. Console-Script `speccify-mcp` in `mcp/pyproject.toml`. 9 neue Unit-Tests in `mcp/tests/test_server_skeleton.py` (leeres tools/resources/prompts-list, Parser, Project-Root-Auflösung). **143 Tests grün**, ruff/format clean.
- [x] **Phase 1c Step 2** — Read-only Tools: `mcp/src/speccify_mcp/tools/{resolve,lint,render}.py` als reine Adapter-Funktionen, registriert über `FastMCP.tool()` in `server._register_readonly_tools`; `render` mit `ReplayCacheClient` (Default `tests/fixtures/llm-cache`, Env-Override `SPECCIFY_CACHE_DIR`, offline-Default). 12 neue Tests in `mcp/tests/test_tools_readonly.py` (happy + Fehlerpfad pro Tool, Test-Helper kopiert `example-project/`+`registry-fixtures/`). **155 Tests grün**, ruff/format clean.
- [x] **Phase 1c Step 3** — Write-Tools `lock`/`pull`/`verify` als Adapter unter `mcp/src/speccify_mcp/tools/{lock,pull,verify}.py` (eigener `_workspace.py` ohne `speccify-cli`-Dep, gleiche Konventionen wie CLI: atomares Schreiben, LLM-Pin im Lockfile, `--offline`-Default, Env-Override `SPECCIFY_CACHE_DIR`). Registriert über `FastMCP.tool()` in neuem `server._register_write_tools`. 10 neue Tests in `mcp/tests/test_tools_write.py` (lock happy + fehlendes Manifest; pull happy + fehlendes Lockfile + Target-Mismatch + offline Cache-Miss; verify grün + Disk-Drift + fehlendes Lockfile; **Cross-Consistency CLI ↔ MCP**: `cli.commands.pull.run_pull` und `speccify_mcp.tools.run_pull` produzieren byte-identische TSX-Outputs + Lockfile). **165 Tests grün**, ruff/format clean.
- [x] **Phase 1c Step 4** — Resources + Prompt: `mcp/src/speccify_mcp/{resources,prompts}.py` registrieren `speccify://manifest`, `speccify://lockfile` (mit Hint-Fallback bei fehlendem Lockfile), `spec://{scope}/{name}@{version}` (über `LocalRegistry.fetch` → `Spec.raw_bytes` als YAML), und Prompt `add-spec(spec_ref, out_dir=./src/components)` mit Schritt-Anleitung resolve→lock→pull→verify. Verdrahtet in `server.build_server` (Lazy-Import gegen Zyklus). 8 neue Tests in `mcp/tests/test_resources_prompts.py`; `test_server_skeleton` aktualisiert (2 fixe Resources + 1 Template + 1 Prompt). **173 Tests grün** (165 + 8), ruff/format clean.
- [x] **Phase 1c Step 5** — CI-Smoke `speccify-mcp` (stdio, offline) + Doku: `scripts/mcp_smoke.py` startet Server via `python -m speccify_mcp.cli`, prüft `tools/list` (6 Tools) + `tools/call render @org/button` (offline, TSX + `generator_pin.kind=llm`) + `resources/read speccify://manifest` mit offiziellem `mcp`-Python-Client. Pytest-Wrapper `mcp/tests/test_stdio_smoke.py` (1 Test) ruft das Skript als Subprocess (Symmetrie zu CI). CI-Step `speccify-mcp smoke (stdio, offline)` in `.github/workflows/ci.yml`. `mcp/README.md` neu (Installation, Tools-/Resources-/Prompts-Tabellen, Client-Config-Snippets); Top-Level-README ergänzt um Abschnitt „MCP-Server" + aktualisierte Phase-Liste/Status. **174 Tests grün**, ruff/format clean.
- [ ] Phase 1c Step 6 — Master-Plan-Sync + Tag-Vorschlag `v0.3.0-phase-1c`.
- [x] Phasen-Plan `.agent/plans/phase-1b-react-codegen.md` geschrieben
      (LLM-Codegen mit Replay-Cache, minimaler `init`, TSX mit Props/Types).
- [x] Phase 1a Step 5 — `speccify verify`, `lint`-Anpassung, CI-Step (E2E im
      example-project: lock + pull + verify), Master-Plan-Sync (React-first,
      Template-Pin, Sub-Spikes 1a–1d), `.gitignore` für example-project-Artefakte.
- [x] Phase 1a Step 4 — Stub-Codegen + `speccify pull --target react`
      (`speccify_core.codegen.stub` + Jinja-Template, atomares Schreiben,
      Lockfile-Update via `with_generated_files`, 8 neue Tests grün).
- [x] Phase 1a Step 3 — Lockfile-Format, `speccify lock` und `speccify add`
      (`schema/lockfile.schema.json`, `speccify_core.lockfile`,
      `speccify_cli.commands.lock`/`.add` mit gemeinsamem `WorkspaceContext`,
      16 neue Tests grün, deterministischer YAML-Dump).
- [x] Phase 1a Step 2 — MVS-Resolver mit transitiver Auflösung + Diamond-Test
      (`speccify_core.resolver`, `Range`/`Resolver`/`ResolverError`-Hierarchie,
      Diamond `button@0.1.1` über `login-screen.uses: ^0.1.1`).
- [x] Phase 1a Step 1 — Manifest und Pseudo-Registry-Layer
      (`schema/manifest.schema.json`, `speccify_core.manifest`,
      `speccify_core.registry`, `registry-fixtures/` mit 5 Specs +
      `button@0.1.1`, `example-project/`).
- [x] **Phase 1a-0 — Rebrand auf `speccify`** abgeschlossen
      (siehe [`.agent/plans/archive/phase-1a0-rename-to-speccify.md`](./plans/archive/phase-1a0-rename-to-speccify.md)).
- [x] Naming-Entscheidung getroffen: `speccify`
      (siehe [`.agent/plans/archive/naming-plan.md`](./plans/archive/naming-plan.md)).

## Blocker
Keine.