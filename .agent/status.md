# Projektstatus: Flowcation

## Meta
- **Typ:** Code
- **Phase:** Phase 0 abgeschlossen — Wrap-up läuft (Open Questions + Übergang zu Phase 1)
- **Priorität:** Mittel
- **Zuletzt aktualisiert:** 2026-05-05

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
- [ ] Wrap-up-Plan abarbeiten: [`.agent/plans/phase-0-wrap-up.md`](./plans/phase-0-wrap-up.md)
      — Open Questions entscheiden (`kind`-Enum, Asset-Ref-URI-Schema, `$schema`-Pin,
      Conformance-Runner nach Phase 3) und Entscheidungstabelle füllen.
- [ ] Optionaler Release-Tag `v0.0.0-phase0`.
- [ ] Separater Phasen-Plan für Phase 1 (CLI-MVP `init`/`add`/`pull`/`lock`,
      MCP-Server, erstes Codegen-Target SwiftUI, Web-Playground).

## Blocker
Keine.