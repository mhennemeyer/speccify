# Projektstatus: Speccify

## Meta
- **Typ:** Code
- **Phase:** Phase 1a-0 (Rebrand `flowcation` → `speccify`) abgeschlossen (Tag `v0.0.1-speccify-rebrand`) — Phase 1a aktiv
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
- [ ] Phase 1a umsetzen: [`.agent/plans/phase-1a-resolver-lockfile.md`](./plans/phase-1a-resolver-lockfile.md)
      — Manifest, lokale Pseudo-Registry, MVS-Resolver, `speccify.lock`,
      CLI-Befehle `add`/`lock`/`pull`/`verify`, Stub-Codegen (Markdown).
- [x] **Phase 1a-0 — Rebrand auf `speccify`** abgeschlossen
      (siehe [`.agent/plans/archive/phase-1a0-rename-to-speccify.md`](./plans/archive/phase-1a0-rename-to-speccify.md)).
- [x] Naming-Entscheidung getroffen: `speccify`
      (siehe [`.agent/plans/archive/naming-plan.md`](./plans/archive/naming-plan.md)).

## Blocker
Keine.