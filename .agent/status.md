# Projektstatus: Flowcation

## Meta
- **Typ:** Code
- **Phase:** Phase 0 abgeschlossen (Tag `v0.0.0-phase0`) — Phase 1a aktiv
- **Priorität:** Mittel
- **Zuletzt aktualisiert:** 2026-05-06

## Beschreibung
Spec-First-Plattform für sprach-/framework-unabhängige Komponenten-Spezifikationen.
Phase 0 etabliert das Spec-Schema v0, den Validator und die CLI `flowcation lint` als
Fundament für alle weiteren Phasen.

## Aktueller Stand
- `schema/spec.schema.json` v0 vorhanden (Draft 2020-12).
- `flowcation_core` enthält `SpecLoader` + `SchemaValidator` mit Tests.
- `flowcation_cli` mit Sub-Command `lint` (Typer); `flowcation lint specs/*.yaml` läuft grün.
- 5 Referenz-Specs unter `specs/` (button, contact-form, http-api-client,
  onboarding-wizard, login-screen) — alle valide.
- Pytest grün (12 Tests). Ruff/Format-Check/Mypy grün.
- Dev-Tooling vollständig: `ruff`, `mypy`, `types-PyYAML` als Dev-Deps gepinnt.
- GitHub-Actions-Workflow `.github/workflows/ci.yml` deckt Lint + Format-Check +
  Mypy + Pytest + `flowcation lint` ab.

## Nächste Schritte
- [ ] Phase 1a umsetzen: [`.agent/plans/phase-1a-resolver-lockfile.md`](./plans/phase-1a-resolver-lockfile.md)
      — Manifest, lokale Pseudo-Registry, MVS-Resolver, `flowcation.lock`,
      CLI-Befehle `add`/`lock`/`pull`/`verify`, Stub-Codegen (Markdown).
- [ ] Naming-Entscheidung treffen: [`.agent/plans/naming-plan.md`](./plans/naming-plan.md)
      (Rebrand wegen Marken-Konflikt mit „Flowcation" Frankfurt).

## Blocker
Keine.