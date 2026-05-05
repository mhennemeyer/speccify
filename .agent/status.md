# Projektstatus: Flowcation

## Meta
- **Typ:** Code
- **Phase:** Phase 0 — Spec-Schema v0 + `flowcation lint` + 5 Referenz-Specs (Abschluss)
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
- [ ] Phase 0 final abnehmen (optionaler Tag `v0.0.0-phase0`).
- [ ] Phasen-Plan für Phase 1 erstellen (CLI-MVP `init`/`add`/`pull`/`lock`,
      MCP-Server, erstes Codegen-Target SwiftUI, Web-Playground).
- [ ] Open Questions aus Phase-0-Plan entscheiden (`kind`-Enum, Asset-Ref-URI-Schema,
      `$schema`-Pin, Conformance-Runner-Verschiebung in Phase 3).

## Blocker
Keine.