---
lifecycle: done
sessionId: session-260506-065711-16qq
---
# Requirements

### Overview & Goals

Phase 0 inhaltlich abschließen, indem die fünf Open Questions aus dem archivierten Phase-0-Plan formal entschieden, dokumentiert und der Übergang zu Phase 1 vorbereitet wird. **Keine Code- oder Schema-Änderung in diesem Wrap-up** — alle Schema-Migrationen, die aus den Entscheidungen folgen, gehören per Wrap-up-Scope in Phase 1.

### Scope

**In Scope**
- Entscheidungstabelle (ADR-Light) in `.agent/plans/phase-0-wrap-up.md` für Q1–Q5 vollständig füllen.
- Neue `Handover`-Sektion im Wrap-up: Übergabepunkte für einen separaten Phase-1-Plan.
- `.agent/status.md` auf *Phase 0 abgeschlossen* setzen.
- `.agent/log.md` um einen Wrap-up-Eintrag ergänzen.
- Annotated Git-Tag `v0.0.0-phase0` auf den Wrap-up-Commit setzen.

**Out of Scope**
- Implementierung der Entscheidungen im Schema (`schema/spec.schema.json`) oder Validator (`flowcation_core.validator`) — gehört in Phase 1.
- Erstellung des Phase-1-Plans selbst — separate Folgeaufgabe.
- Tests, Codegen, Resolver, Conformance-Runner, Registry, Sigstore.

### Entschiedene Open Questions

 # | Frage | Entscheidung |
---|---|---|
 1 | `kind`-Enum vs. offener String | Strikte Enum ab Phase 1 mit `ui-component`, `ui-workflow`, `logic`, `workflow`, `screen` |
 2 | Asset-Ref-URI-Schema | Whitelist: relative Pfade + `asset://` + `figma://` + `https://` |
 3 | `uses:`-Auflösung | Phase 1 (Resolver in `flowcation-core`) — Phase 0 nur Syntax-Check |
 4 | `$schema`-Pin | Pin auf `https://json-schema.org/draft/2020-12/schema`; Validator prüft den Pin in Phase 1 explizit |
 5 | Conformance-Runner | Phase 3 — Field bleibt deklarativ |

### Funktionale Anforderungen

- Wrap-up-Plan trägt für Q1, Q2, Q4 die finalen Entscheidungen, Rationale und Phase-Zuordnung in der Tabelle.
- Eine neue `## Handover`-Sektion listet die Entscheidungen verdichtet, verlinkt den Master-Plan-Phase-1-Abschnitt und benennt die nächste Aufgabe (separater Phase-1-Plan).
- `status.md`-Phase wechselt auf `Phase 0 abgeschlossen — Phase-1-Plan steht aus`.
- `log.md` enthält einen datierten Eintrag mit den fünf Entscheidungen und dem Tag.
- Release-Tag `v0.0.0-phase0` ist annotated, mit Hinweis auf den Wrap-up-Commit als Inhalt.

### Non-Functional Requirements

- Reine Doku-/Meta-Änderung; kein Pytest-/Ruff-/Mypy-Run nötig, da kein Code berührt wird.
- Konsistenz mit `AGENTS.md` (Verweisstruktur Wrap-up ↔ archivierter Phase-0-Plan) bleibt erhalten.

# Technical Design

### Current Implementation

- `.agent/plans/phase-0-wrap-up.md` enthält bereits die Stage-Struktur und einen leeren ADR-Light-Tabellen-Skeleton (Zeilen 65–75): Q1, Q2, Q4 sind als `_offen_` markiert; Q3 (Phase 1) und Q5 (Phase 3) sind bereits zugewiesen.
- `.agent/plans/archive/phase-0-spec-schema-spike.md` ist die Quelle der Open Questions (Zeilen 95–101).
- `schema/spec.schema.json` deklariert bereits `$schema: https://json-schema.org/draft/2020-12/schema` (Zeile 2), ein offenes `kind`-Feld (Zeilen 20–24) und ein liberales `ux.references`-Pattern (Zeilen 89–96). Die Entscheidungen Q1, Q2, Q4 spiegeln den dort dokumentierten *Phase-1-Migrations-Pfad* wider — Umsetzung erfolgt in Phase 1.
- `.agent/status.md` Zeile 5 zeigt aktuell *Wrap-up läuft*; Zeilen 26–31 listen Wrap-up-Aufgaben.
- `.agent/log.md` endet am 2026-05-05 mit dem Wrap-up-Anlage-Eintrag.
- Es existiert kein Phase-1-Plan unter `.agent/plans/next/` (Verzeichnis ist leer).

### Key Decisions

1. **ADR-Light statt separater ADR-Dateien.** Entscheidungen werden in der bestehenden Tabelle des Wrap-up-Plans gefüllt, nicht in einem neuen `.agent/adrs/`-Ordner. Begründung: kompatibel mit der bisherigen Plan-Konvention (`.agent/plans/*.md`), keine neue Struktur nötig.
2. **Implementierung strikt in Phase 1.** Auch Q4 (`$schema`-Pin) wird *nicht* jetzt im Validator durchgesetzt, obwohl der Pin im Schema bereits gesetzt ist. Begründung: Wrap-up-Scope laut Plan-Datei explizit doku-only.
3. **Phase-1-Plan-Stub als separate Folgeaufgabe.** Statt einer leeren Datei unter `.agent/plans/next/` wird im Wrap-up nur eine `Handover`-Sektion mit Übergabepunkten geschrieben. Begründung: konsistent mit der bestehenden Plan-Struktur (`flowcation-plan.md` → `phase-0-wrap-up.md`).
4. **Annotated Tag, kein lightweight Tag.** `v0.0.0-phase0` als `git tag -a` mit Message-Body, der die fünf Entscheidungen kurz auflistet. Begründung: erfüllt die `Conventional`-/Audit-Disziplin und macht den Tag selbsterklärend.

### Proposed Changes

#### `.agent/plans/phase-0-wrap-up.md`
- Status-Zeile (Zeile 3) von `Draft` → `Done` ändern (am Ende).
- Stages 1, 2, 4 (Zeilen 36–50) um eine Zeile *Entscheidung:* ergänzen, die das Ergebnis aus den Round-1-Antworten festhält.
- Tabellen-Zeilen 69, 70, 72 (Q1, Q2, Q4) füllen: Spalte *Entscheidung* + ggf. Rationale-Verfeinerung. Q3 und Q5 unverändert.
- Nach der Tabelle (vor `## Validation`) eine neue Sektion einfügen:
  ```markdown
  ## Handover an Phase 1
  - Schema-Migrationen aus Q1/Q2/Q4 (siehe Tabelle).
  - Validator-Erweiterung: `$schema`-Pin explizit prüfen.
  - Resolver für `uses:` (Q3).
  - Master-Plan-Phase-1-Abschnitt: …flowcation-plan.md#phase-1-…
  - Nächster Plan-Auftrag: `.agent/plans/next/phase-1-cli-mvp.md` (Erstellung in separater Aufgabe).
  ```
- Validation-Block: Häkchen für *Entscheidungstabelle gefüllt* und *Phase-1-Auftrag definiert* setzen.

#### `.agent/status.md`
- Zeile 5 (`Phase`): `Phase 0 abgeschlossen — Phase-1-Plan steht aus`.
- Zeile 7 (`Zuletzt aktualisiert`): heutiges Datum.
- *Aktueller Stand* (Zeilen 14–23) um eine Zeile mit dem Tag und dem ADR-Stand erweitern.
- *Nächste Schritte* (Zeilen 25–31) reduziert auf einen Punkt: separater Phase-1-Plan in `.agent/plans/next/`.

#### `.agent/log.md`
- Neuer Datum-Block mit den fünf ADR-Entscheidungen, Hinweis auf gefüllte Tabelle und gesetzten Tag.

#### Git
- Commit `chore(plans): wrap up phase 0 — adr decisions Q1–Q5` (Conventional Commit, deckt Plan-, Status-, Log-Änderungen ab).
- `git tag -a v0.0.0-phase0 -m "Phase 0 closed — schema v0, flowcation lint, 5 reference specs. ADRs Q1–Q5 recorded."`.

### Data Models / Contracts

Keine. Reine Markdown-/Repo-Änderung.

### File Structure

```
.agent/
├── plans/
│   └── phase-0-wrap-up.md      # MOD: Stages 1/2/4, ADR-Tabelle, neue Handover-Sektion, Status Done
├── status.md                    # MOD: Phase, Datum, Stand, Nächste Schritte
└── log.md                       # MOD: neuer Eintrag
```

Keine neuen Dateien. `schema/`, `core/`, `cli/`, `specs/` werden nicht angefasst.

### Risks

- **Risiko**: Der Pin auf Draft 2020-12 (Q4) ist im Schema bereits gesetzt, wird aber im Validator noch nicht erzwungen — wenn jemand das Schema versehentlich auf einen anderen Draft umstellt, fällt es im Wrap-up-Stand nicht auf. **Mitigation**: explizit in `Handover` als Phase-1-Aufgabe markieren.
- **Risiko**: Strikte `kind`-Enum (Q1) bricht unbekannte Spec-Klassen, die in Drittprojekten existieren könnten. **Mitigation**: Phase 1 ist Pre-1.0 (`v0.0.x`), Breaking-Minor-Bumps sind explizit erlaubt; in der ADR-Rationale dokumentieren.
- **Risiko**: `figma://` in der Whitelist (Q2) ist nicht-portabel und kann in Codegen-Builds fehlschlagen. **Mitigation**: in der ADR-Rationale auf Phase 3 (Conformance) verweisen, wo Asset-Resolution konkretisiert wird.

# Delivery Steps

###   Step 1: ADR-Tabelle und Stage-Entscheidungen im Wrap-up-Plan füllen
`.agent/plans/phase-0-wrap-up.md` enthält die finalen Entscheidungen für Q1–Q5 in Tabelle und Stages.

- Stage 1 um Entscheidung ergänzen: strikte Enum `ui-component | ui-workflow | logic | workflow | screen` ab Phase 1.
- Stage 2 um Entscheidung ergänzen: Whitelist relative Pfade + `asset://` + `figma://` + `https://`.
- Stage 4 um Entscheidung ergänzen: `$schema` auf Draft 2020-12 pinnen, Validator prüft Pin in Phase 1.
- ADR-Light-Tabelle (Zeilen 67–73) füllen: Spalte *Entscheidung* für Q1, Q2, Q4; Rationale und Schema-Impact-Spalten verfeinern, sodass kein `_offen_` mehr übrigbleibt.
- Q3 und Q5 unverändert lassen (bereits zugewiesen).
- Den erläuternden Hinweissatz unter der Tabelle (Zeile 75) entfernen, da die Tabelle vollständig ist.

###   Step 2: Handover-Sektion ergänzen und Validation/Status-Markierung des Plans abschließen
Der Wrap-up-Plan dokumentiert die Übergabepunkte an einen separaten Phase-1-Plan und ist als `Done` markiert.

- Neue Sektion `## Handover an Phase 1` zwischen ADR-Tabelle und Validation einfügen, mit Bullets:
  - Schema-Migrationen aus Q1/Q2/Q4 (Verweis auf Tabelle).
  - Validator-Pflicht: `$schema`-Pin explizit prüfen (Q4-Implementierung).
  - Resolver für `uses:` in `flowcation-core` (Q3).
  - Verweis auf Master-Plan-Abschnitt `Phase 1 — CLI-MVP + MCP + ein Codegen-Target + Playground`.
  - Nächster Plan-Auftrag: separater Plan unter `.agent/plans/next/phase-1-cli-mvp.md` (Erstellung als Folgeaufgabe, nicht Teil dieses Wrap-ups).
- Validation-Block: Häkchen `Entscheidungstabelle für alle 5 Open Questions ausgefüllt`, `status.md` aktualisiert, `log.md` aktualisiert, `Phase-1-Plan-Auftrag ist als nächste Aufgabe definiert` markieren.
- Status-Zeile am Plan-Anfang (Zeile 3) von `Draft` auf `Done` setzen und Abschluss-Datum ergänzen.

###   Step 3: Status- und Log-Datei aktualisieren
`.agent/status.md` und `.agent/log.md` reflektieren den Wrap-up-Abschluss und verweisen auf den nächsten Plan.

- `status.md` Zeile 5: `Phase` auf `Phase 0 abgeschlossen — Phase-1-Plan steht aus` setzen.
- `status.md` Zeile 7: `Zuletzt aktualisiert` auf heutiges Datum.
- `status.md` *Aktueller Stand*: eine Zeile ergänzen, die den Tag `v0.0.0-phase0` und den ADR-Abschluss benennt.
- `status.md` *Nächste Schritte*: auf einen Punkt reduzieren — Erstellung von `.agent/plans/next/phase-1-cli-mvp.md`.
- `log.md`: neuen Datums-Block hinzufügen mit den fünf ADR-Entscheidungen (Q1 strict enum, Q2 scheme whitelist, Q3 Phase-1-Resolver, Q4 Draft-2020-12-Pin + Validator-Check, Q5 Phase-3-Runner) und Hinweis auf den gesetzten Release-Tag.

###   Step 4: Release-Tag v0.0.0-phase0 setzen
Ein annotated Git-Tag `v0.0.0-phase0` markiert den Phase-0-Stand auf dem Wrap-up-Commit.

- Plan-/Status-/Log-Änderungen als ein Conventional-Commit bündeln: `chore(plans): wrap up phase 0 — adr decisions Q1–Q5`.
- Annotated Tag setzen: `git tag -a v0.0.0-phase0 -m "Phase 0 closed — schema v0, flowcation lint, 5 reference specs. ADRs Q1–Q5 recorded."`.
- Verifizieren mit `git tag -l v0.0.0-phase0` und `git show v0.0.0-phase0 --no-patch`.
- Tag wird **nicht** automatisch gepusht — Push erfolgt durch den Nutzer (kein Schreibzugriff auf Remote im Plan-Scope).