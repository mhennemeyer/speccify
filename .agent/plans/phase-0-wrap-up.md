# Phase 0 — Wrap-up

> **Status**: Draft
> **Erstellt**: 2026-05-05
> **Vorgänger**: [Phase 0 — Spec-Schema v0 + `flowcation lint` + 5 Referenz-Specs (archiviert)](./archive/phase-0-spec-schema-spike.md)
> **Ziel**: Phase 0 formal abnehmen, die fünf Open Questions aus dem Phase-0-Plan entscheiden und die Übergabepunkte für einen separaten Phase-1-Plan definieren.

---

## Ziel

- Phase 0 inhaltlich ist abgeschlossen (Schema v0, `flowcation lint`, 5 Referenz-Specs, CI grün).
- Dieser Plan trifft die noch offenen **Entscheidungen** (ADR-artig dokumentiert) und bereitet den Übergang zu Phase 1 vor.
- Schema-Migrationen, die aus den Entscheidungen folgen, gehören in **Phase 1**, nicht in dieses Wrap-up.

---

## Scope

**In Scope**
- Entscheidung der 5 Open Questions aus dem Phase-0-Plan
  (`kind`-Enum, Asset-Ref-URI-Schema, `uses:`-Auflösung, `$schema`-Pin, Conformance-Tests).
- Optionaler Release-Tag `v0.0.0-phase0`.
- Definition der Übergabepunkte an einen **separaten** Phase-1-Plan (dieser Plan erstellt Phase 1 nicht selbst).
- Aktualisierung von `.agent/status.md` und `.agent/log.md`.

**Out of Scope**
- Implementierung der Phase-1-Features (CLI `init`/`add`/`pull`/`lock`, MCP-Server, SwiftUI-Codegen, Browser-Playground).
- Schema-Änderungen / Migrationen — gehören in Phase 1.
- Sigstore, Registry, Conformance-Runner.

---

## Stages

### Stage 1 — Open Question 1: `kind`-Enum
- Entscheiden, ob Phase 1 das Schema von offenem String auf `enum` (`ui-component`, `ui-workflow`, `logic`, `workflow`, `screen`) verengt.
- **Empfehlung**: Ja — strikte enum ab Phase 1.

### Stage 2 — Open Question 2: Asset-Ref-URI-Schema
- Entscheiden zwischen relativen Pfaden (`./screenshots/...`) und URI-Schema (`asset://`, `figma://`).
- **Empfehlung**: Beide erlauben, mit klarer Priorität auf `asset://` für portable Specs (Details in Phase 1).

### Stage 3 — Open Question 3: `uses:`-Auflösung in Phase 1 verankern
- Phase 0 prüft nur syntaktisch; Phase-1-Plan definiert Resolver formal.
- Hier: nur Doku-Verweis, keine Umsetzung.

### Stage 4 — Open Question 4: `$schema`-Pin
- Entscheiden, ob `$schema` auf `https://json-schema.org/draft/2020-12/schema` gepinnt wird.
- **Empfehlung**: Ja — pinnen.

### Stage 5 — Open Question 5: Conformance-Runner
- Field bleibt deklarativ in Phase 0–2; Runner kommt in **Phase 3**.
- Hier: nur Doku-Verweis.

### Stage 6 — Optionaler Release-Tag `v0.0.0-phase0`
- Entscheiden, ob ein Tag gesetzt wird, um den Phase-0-Stand einzufrieren.

### Stage 7 — Phase-1-Plan-Stub (separater Plan-Auftrag)
- Übergabepunkte sammeln: Entscheidungen aus Stages 1–4, `status.md`-Stand, Master-Plan-Phase-1-Abschnitt.
- **Erstellung des Phase-1-Plans erfolgt in einer separaten Aufgabe.**

---

## Entscheidungstabelle (ADR-Light)

| # | Frage | Entscheidung | Rationale | Schema-Impact | Phase |
|---|---|---|---|---|---|
| 1 | `kind`-Enum vs. offener String | _offen_ | strikte Validierung, klare Codegen-Dispatch | Schema-Breaking (minor in Pre-1.0) | Phase 1 |
| 2 | Asset-Ref-URI-Schema | _offen_ | Portabilität vs. Einfachheit | additiv | Phase 1 |
| 3 | `uses:`-Auflösung | Phase 1 (Resolver) | Phase 0 nur Syntax-Check | additiv (Resolver, kein Schema-Change) | Phase 1 |
| 4 | `$schema`-Pin auf Draft 2020-12 | _offen_ | Reproduzierbarkeit | nicht-breaking | Phase 1 |
| 5 | Conformance-Runner | Phase 3 | Field bleibt deklarativ | kein Schema-Change | Phase 3 |

> Tabelle wird gefüllt, sobald die Entscheidungen getroffen sind.

---

## Validation

- Entscheidungstabelle für alle 5 Open Questions ausgefüllt.
- `.agent/status.md` zeigt *Phase 0 abgeschlossen — Wrap-up läuft* (bzw. *abgeschlossen* nach Wrap-up-Ende).
- `.agent/log.md` enthält Eintrag zum Wrap-up.
- Phase-1-Plan-Auftrag ist als nächste Aufgabe definiert.

---

## Nächste Phase

[Phase 1 — CLI-MVP + MCP + ein Codegen-Target + Playground](./flowcation-plan.md#phase-1-cli-mvp--mcp--ein-codegen-target--playground) — eigener Phasen-Plan folgt.
