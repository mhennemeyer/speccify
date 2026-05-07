# Projektstatus: Speccify

## Meta
- **Typ:** Code
- **Phase:** Phase 1b Step 1 (`speccify init`) abgeschlossen — bereit für Step 2 (Lockfile-Schema-Erweiterung `kind: llm`). Phase 1a abgeschlossen.
- **Priorität:** Mittel
- **Zuletzt aktualisiert:** 2026-05-06

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
- [ ] Phase 1b Step 2 — Lockfile-Schema-Erweiterung `generator.oneOf`
      (`template`/`llm`), `GeneratorPin` als Union.
- [ ] Phase 1b Step 3 — Replay-Cache + `LlmClient`-Protokoll
      (`speccify_core.codegen.replay`).
- [ ] Phase 1b Step 4 — React-LLM-Adapter + Codegen-Dispatcher
      (`render_for_target`).
- [ ] Phase 1b Step 5 — `speccify pull --target react --offline` + CI-E2E mit
      eingechecktem Replay-Cache.
- [ ] Phase 1b Step 6 — Master-Plan-Sync + Tag-Vorschlag `v0.2.0-phase-1b`.
- [ ] Optional: annotated Tag `v0.1.0-phase-1a` setzen (Phase 1a abgeschlossen).
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