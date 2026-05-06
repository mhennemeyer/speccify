---
sessionId: session-260505-181449-1wqk
isActive: false
---

# Requirements

### Overview & Goals

Phase 0 (Spec-Schema v0 + flowcation lint + 5 Referenz-Specs) ist inhaltlich abgeschlossen. Diese Aufgabe schließt die Phase formal ab:

1. `.agent/plans/phase-0-spec-schema-spike.md` wird aktualisiert — alle abgeschlossenen Stages werden als erledigt markiert.
2. Verbleibende offene Punkte (Open Questions + Phase-1-Übergang) werden in einen neuen Plan `.agent/plans/phase-0-wrap-up.md` ausgelagert.
3. Der ursprüngliche Phase-0-Plan wird nach `.agent/plans/archive/` verschoben.

### Scope

**In Scope**
- Status-Audit von Phase-0-Stages 1–8 anhand des Repos (`schema/`, `core/`, `cli/`, `specs/`, `.github/workflows/ci.yml`).
- Überarbeitung des Phase-0-Plans mit klaren Erledigt-Markierungen pro Stage.
- Erstellung eines neuen Plans `phase-0-wrap-up.md`, der ausschließlich die noch offenen Punkte enthält:
  - Entscheidung der 5 Open Questions aus dem Phase-0-Plan (`kind`-Enum, Asset-Ref-URI-Schema, `uses:`-Auflösung, `$schema`-Pin, Conformance-Tests).
  - Optionaler Release-Tag `v0.0.0-phase0`.
  - Übergabe an einen separaten Phase-1-Plan (dieser Plan erstellt Phase 1 nicht selbst — er definiert nur die Übergabepunkte).
- Verschieben von `phase-0-spec-schema-spike.md` nach `.agent/plans/archive/`.
- Aktualisierung von `.agent/status.md` und `.agent/log.md` (per `rules.md`).

**Out of Scope**
- Implementierung der Phase-1-Features (CLI `init`/`add`/`pull`/`lock`, MCP-Server, SwiftUI-Codegen, Browser-Playground).
- Schema-Änderungen außerhalb der Open-Question-Entscheidungen.
- Sigstore, Registry, Conformance-Runner.

### Funktionale Anforderungen

- Der archivierte Phase-0-Plan zeigt für jeden Stage 1–8 sichtbar den Erledigt-Status (Checkbox `[x]` oder Häkchen), inklusive kurzer Referenz auf den finalen Artefakt-Pfad.
- Der neue `phase-0-wrap-up.md` enthält ausschließlich Restpunkte und ist als eigenständiger Plan in `.agent/plans/` lesbar.
- `rules.md`-Workflow eingehalten: `log.md` und `status.md` aktualisiert.

# Technical Design

### Aktueller Stand (Audit)

Verifiziert per Repo-Inspektion gegen `phase-0-spec-schema-spike.md`:

 Stage | Soll | Ist | Status |
---|---|---|---|
 1 — JSON-Schema v0 | `schema/spec.schema.json` | vorhanden (Draft 2020-12) | erledigt |
 2 — `flowcation lint` CLI | `flowcation_core.SpecLoader` + `SchemaValidator`, Typer-CLI `lint` | `core/src/flowcation_core/{loader,validator}.py`, `cli/src/flowcation_cli/` | erledigt |
 3 — `specs/button.flowcation.yaml` | UI-Component | vorhanden | erledigt |
 4 — `specs/contact-form.flowcation.yaml` | UI mit Validierung | vorhanden | erledigt |
 5 — `specs/http-api-client.flowcation.yaml` | Logic | vorhanden | erledigt |
 6 — `specs/onboarding-wizard.flowcation.yaml` | Workflow mit `uses:` | vorhanden | erledigt |
 7 — `specs/login-screen.flowcation.yaml` | Screen | vorhanden | erledigt |
 8 — CI-Smoke | Pytest + `flowcation lint specs/*.yaml` + GH-Actions | `.github/workflows/ci.yml` deckt ruff/format/mypy/pytest/lint | erledigt |

Laut `status.md`: 12 Pytest-Tests grün, `uv run flowcation lint specs/*.yaml` grün.

### Wirklich offen geblieben

Aus Plan-Abschnitt *Open Questions* + `status.md` *Nächste Schritte*:

1. **`kind`-Enum vs. offener String** — soll Phase 1 das Schema auf enum (`ui-component`, `ui-workflow`, `logic`, `workflow`, `screen`) verengen?
2. **Asset-Refs** — relative Pfade (`./screenshots/...`) vs. URI-Schema (`asset://`, `figma://`)?
3. **`uses:`-Auflösung** — Phase 0 nur syntaktisch; Phase 1 baut Resolver.
4. **`$schema`-Pin** auf `https://json-schema.org/draft/2020-12/schema`?
5. **Conformance-Tests** — Field bleibt deklarativ; Runner nach Phase 3.
6. **Optionaler Release-Tag** `v0.0.0-phase0`.
7. **Übergabe** an Phase-1-Plan (separater Plan, nicht Teil dieses Wrap-ups).

### Key Decisions (in diesem Plan)

- **Ein neuer Plan, kein In-Place-Update**: Der Phase-0-Plan ist abgeschlossen; verbleibende Punkte gehören in einen separaten Wrap-up-Plan, damit das Archiv den finalen Phase-0-Stand einfriert.
- **Wrap-up trennt Entscheidung von Umsetzung**: Open Questions werden im Wrap-up entschieden und dokumentiert; Schema-Änderungen, die daraus folgen, gehören in den Phase-1-Plan.
- **Phase-1-Plan ist eine eigene Aufgabe**: Dieser Plan erstellt ihn nicht; er listet nur die Eingabepunkte (`status.md` + entschiedene Open Questions).

### Proposed Changes

#### 1. Phase-0-Plan abhaken (in-place)

`.agent/plans/phase-0-spec-schema-spike.md`:
- Header `Status: Draft` -> `Status: Done` (+ Datum 2026-05-05).
- Jeder Stage-Eintrag bekommt einen Erledigt-Marker und einen kurzen Verweis auf das Artefakt (z. B. `-> schema/spec.schema.json`).
- Validation-Block mit Erledigt-Marker pro Punkt.
- Open-Questions-Block bleibt unverändert (wandert per Archivierung mit) — die Entscheidungen werden im neuen Wrap-up-Plan getroffen, nicht im archivierten.

#### 2. Neuer Plan: `.agent/plans/phase-0-wrap-up.md`

Struktur (analog zum existierenden Phase-0-Plan):

- Status / Erstellt / Vorgänger (verweist auf den archivierten Phase-0-Plan).
- Ziel: Phase-0-Abnahme + Open Questions entscheiden + Übergang zu Phase 1 vorbereiten.
- Scope (In/Out of Scope wie oben).
- Stages:
  1. Open Question 1 — `kind`-Enum entscheiden (Empfehlung: ja, ab Phase 1 enum).
  2. Open Question 2 — Asset-Ref-URI-Schema entscheiden.
  3. Open Question 3 — `uses:`-Auflösung formal in Phase 1 verankern (nur Doku).
  4. Open Question 4 — `$schema`-Pin entscheiden (Empfehlung: Draft 2020-12 pinnen).
  5. Open Question 5 — Conformance-Runner formal in Phase 3 verankern (nur Doku).
  6. Optionaler Tag `v0.0.0-phase0`.
  7. Phase-1-Plan-Stub (separater Plan-Auftrag).
- Validation: Entscheidungen sind in einer ADR-artigen Tabelle dokumentiert; `status.md` + `log.md` aktualisiert.

#### 3. Archivierung

- `.agent/plans/phase-0-spec-schema-spike.md` -> `.agent/plans/archive/phase-0-spec-schema-spike.md` (mittels `git mv`, damit History erhalten bleibt).
- Querverweis im Master-Plan (`flowcation-plan.md` Zeilen 276–281) prüfen — falls dort auf den alten Pfad verlinkt wird, Link auf `archive/phase-0-spec-schema-spike.md` aktualisieren.

#### 4. Status / Log

- `.agent/status.md`: Phase auf *Phase 0 abgeschlossen — Wrap-up läuft* setzen, *Nächste Schritte* auf den neuen Wrap-up-Plan zeigen lassen.
- `.agent/log.md`: Eintrag *Phase 0 abgenommen, Plan archiviert, Wrap-up-Plan angelegt*.

### File Structure

```
.agent/plans/
├── archive/
│   ├── package-manager-comparison.md            (bestehend)
│   └── phase-0-spec-schema-spike.md             (NEU: verschoben)
├── next/
├── flowcation-plan.md                            (ggf. Link aktualisieren)
├── naming-plan.md
└── phase-0-wrap-up.md                            (NEU)
.agent/
├── status.md                                     (aktualisiert)
└── log.md                                        (aktualisiert)
```

### Risks

- **Offene Querverweise auf den alten Pfad** — Master-Plan bzw. AGENTS.md könnten auf `phase-0-spec-schema-spike.md` verlinken. Vor dem Verschieben per Suche prüfen.
- **Open-Question-Entscheidungen ohne Schema-Migration** — falls eine Entscheidung Schema-Breaking wäre (z. B. `kind`-Enum strikt), gehört die Umsetzung in Phase 1, nicht in dieses Wrap-up. Wrap-up dokumentiert nur.

# Delivery Steps

### ✓ Step 1: Phase-0-Plan abhaken
`.agent/plans/phase-0-spec-schema-spike.md` zeigt für jeden Stage 1–8 sichtbar den Erledigt-Status mit Artefakt-Verweis.

- Header-Status von `Draft` auf `Done` (Stand 2026-05-05) ändern.
- Jeden Stage-Block mit Erledigt-Marker versehen und auf das jeweilige Artefakt verweisen:
  - Stage 1 -> `schema/spec.schema.json` (Draft 2020-12)
  - Stage 2 -> `core/src/flowcation_core/{loader,validator}.py` + `cli/src/flowcation_cli/`
  - Stages 3–7 -> jeweilige Datei in `specs/`
  - Stage 8 -> `.github/workflows/ci.yml` + 12 grüne Pytest-Tests
- Validation-Block ebenfalls abhaken (lint grün, pytest grün, Schema valide).

### ✓ Step 2: Wrap-up-Plan anlegen
`.agent/plans/phase-0-wrap-up.md` enthält ausschließlich die nach Phase-0-Abschluss verbleibenden Punkte.

- Header (Status `Draft`, Erstellt 2026-05-05, Vorgänger-Link auf archivierten Phase-0-Plan).
- Ziel-Block: Phase-0-Abnahme + Open Questions entscheiden + Phase-1-Übergang vorbereiten.
- Scope-Block (In/Out of Scope analog Plan).
- Stages-Block mit je einem Eintrag pro Open Question (1–5), plus Tag-Stage und Phase-1-Plan-Stub-Stage.
- ADR-artige Entscheidungstabelle vorbereiten (Spalten: Frage, Entscheidung, Rationale, Schema-Impact, Phase).
- Validation-Block (Tabelle gefüllt, `status.md`/`log.md` aktualisiert).

### ✓ Step 3: Phase-0-Plan archivieren
`.agent/plans/phase-0-spec-schema-spike.md` ist nach `.agent/plans/archive/` verschoben — ohne History-Verlust und ohne broken Links.

- `git mv .agent/plans/phase-0-spec-schema-spike.md .agent/plans/archive/phase-0-spec-schema-spike.md`.
- Per Suche prüfen, ob `flowcation-plan.md`, `AGENTS.md` oder andere Dokumente auf den alten Pfad verlinken; gefundene Links auf `archive/phase-0-spec-schema-spike.md` umbiegen.
- Sicherstellen, dass der neue Wrap-up-Plan im Vorgänger-Block ebenfalls auf den archivierten Pfad zeigt.

### ✓ Step 4: status.md und log.md aktualisieren
`.agent/status.md` und `.agent/log.md` reflektieren den Phase-0-Abschluss und den Wrap-up-Übergang gemäß `rules.md`.

- `status.md` -> Phase auf *Phase 0 abgeschlossen — Wrap-up läuft* setzen, *Nächste Schritte* auf `phase-0-wrap-up.md` (Open Questions + Phase-1-Plan) verweisen, Datum aktualisieren.
- `log.md` -> neuer Eintrag unter heutigem Datum: *Phase-0-Plan abgehakt, Wrap-up-Plan angelegt, Phase-0-Plan nach `archive/` verschoben* mit kurzer Liste der durchgeführten Schritte.