# Phase 0 — Spec-Schema v0 + `flowcation lint` + 5 Referenz-Specs

> **Status**: Done (abgeschlossen am 2026-05-05)
> **Erstellt**: 2026-05-05
> **Vorgänger**: [Master-Plan](./flowcation-plan.md), Phase 0 (Zeilen 276–281).
> **Ziel**: Phase 0 abschließen — `spec.schema.json` v0 ist veröffentlicht, `flowcation lint` validiert YAML-Specs, fünf handgeschriebene Referenz-Specs decken die drei Komponenten-Klassen ab.

---

## Ziel

Aus dem Master-Plan, Phase 0:

- Spec-Schema v0 (YAML + JSON-Schema) veröffentlichen.
- Asset-Refs (Screenshots / Wireframes / Negativ-Beispiele) als first-class im Schema.
- 5 Referenz-Specs handgeschrieben: 1 Button, 1 Form, 1 API-Client, 1 Workflow, 1 Screen.
- Validator-CLI `flowcation lint` (das erste CLI-Kommando überhaupt).

Erfolgskriterium: `flowcation lint specs/*.yaml` läuft grün gegen alle 5 Referenz-Specs.

---

## Scope

**In Scope**

- `schema/spec.schema.json` (Draft-2020-12 oder kompatibel).
- `flowcation_core.SpecLoader` (YAML → dict) und `flowcation_core.SchemaValidator` (jsonschema-basiert).
- `flowcation_cli` mit Typer-CLI; Sub-Command `lint <files...>`.
- Fünf YAML-Specs unter `specs/`.
- Pytest-Smoke-Tests für Loader + Validator + CLI.

**Out of Scope**

- Codegen, MCP-Server, Resolver, Lockfile, Registry, Web-Playground (alles Phase 1+).
- `add`/`pull`/`publish`/`init`-Befehle.
- sigstore-Signaturen, CI-Pipeline.
- Visuelle Diff-/Galerie-Ansichten.

---

## Stages

### Stage 1 — JSON-Schema v0 ✅
→ `schema/spec.schema.json` (Draft 2020-12).

- `schema/spec.schema.json` ableiten aus dem YAML-Beispiel im Master-Plan (Zeilen 123–174).
- Pflichtfelder: `id`, `version`, `kind`, `title`, `summary`.
- Optional: `inputs`, `outputs`, `events`, `uses`, `acceptance`, `ux.references`, `non_functional`, `conformance`.
- `id`-Pattern: `^flow://[a-z0-9-]+(@[\w.-]+)?$` oder `@scope/<name>`.
- `version`: SemVer-Pattern.
- `kind`: zunächst offener String, bewusst nicht enum (Open Question, siehe unten).

### Stage 2 — `flowcation lint` CLI ✅
→ `core/src/flowcation_core/{loader,validator}.py` + `cli/src/flowcation_cli/`.

- `flowcation_core.SpecLoader.load(path: Path) -> dict` (PyYAML).
- `flowcation_core.SchemaValidator(schema_path)` mit `jsonschema`.
- `flowcation_cli/__main__.py` mit Typer: `flowcation lint <files...>` → exit 0/1, klare Fehlermeldungen mit Pfad + JSONPath.
- Entry-Point in `cli/pyproject.toml` reaktivieren.

### Stage 3 — Referenz-Spec 1: `specs/button.flowcation.yaml` ✅
UI-Component, einfach. Variants (primary/secondary), disabled, loading.

### Stage 4 — Referenz-Spec 2: `specs/contact-form.flowcation.yaml` ✅
UI-Component mit Validierung (Name, E-Mail, Nachricht, Submit-Verhalten).

### Stage 5 — Referenz-Spec 3: `specs/http-api-client.flowcation.yaml` ✅
Logic-Component: typisierter HTTP-Client (`get`/`post`, retry, timeout).

### Stage 6 — Referenz-Spec 4: `specs/onboarding-wizard.flowcation.yaml` ✅
Workflow, referenziert `button` und `contact-form` über `uses:`.

### Stage 7 — Referenz-Spec 5: `specs/login-screen.flowcation.yaml` ✅
Screen mit OTP-Login (analog Master-Plan-Beispiel `flow://login-with-otp`).

### Stage 8 — CI-Smoke ✅
→ `.github/workflows/ci.yml` (ruff/format/mypy/pytest/lint) + 12 grüne Pytest-Tests.

- `uv run flowcation lint specs/*.yaml` → exit 0.
- `pytest` für Loader + Validator + CLI grün.
- Optional: GitHub-Actions-Workflow `ci.yml` (kann auch in Phase 1 nachgezogen werden).

---

## Validation

- ✅ `flowcation lint specs/*.yaml` läuft grün.
- ✅ Jede Spec hat mindestens ein `acceptance`-Beispiel (Given/When/Then).
- ✅ `pytest` grün (12 Tests); Loader + Validator haben Happy-Path- und Fehlerfall-Tests (fehlendes Pflichtfeld, ungültige `id`).
- ✅ Schema als Draft-2020-12 deklariert und mit `jsonschema` validierbar.

---

## Open Questions

1. **`kind`-Enum vs. offener String**: Schema v0 lässt offen, ab Phase 1 enum (`ui-component`, `ui-workflow`, `logic`, `workflow`, `screen`)?
2. **Asset-Refs**: Relative Pfade (`./screenshots/...`) vs. URI-Schema (`asset://...`, `figma://...`)? Aktuell beides erlauben; in Phase 1 entscheiden.
3. **`uses:`-Auflösung in Phase 0**: Lint nur syntaktisch prüfen, keine Resolver-Logik (das gehört in Phase 1).
4. **Schema-Version**: `$schema` auf `"https://json-schema.org/draft/2020-12/schema"` festlegen?
5. **Conformance-Tests**: Phase 0 deklariert nur das Schema-Feld; Runner kommt in Phase 3.

---

## Nächste Phase

[Phase 1 — CLI-MVP + MCP + ein Codegen-Target + Playground](./flowcation-plan.md#phase-1-cli-mvp--mcp--ein-codegen-target--playground).
