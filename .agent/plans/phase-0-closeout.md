---
sessionId: session-260505-164252-ui7l
isActive: true
---

# Requirements

### Was ist im Phase-0-Plan noch offen?

**Inhaltlich nichts.** Stages 1–8 sind im Code abgehakt: 5 valide Specs, Loader/Validator/CLI mit 12 Tests, CI-Workflow, alle Verifikations-Kommandos lokal grün.

**Formal vier Doku-Punkte:**
1. Status-Header `Draft` → `Done` (+ Abschlussdatum).
2. Open Questions 1–5 inline als _Resolved_/_Deferred_ markieren.
3. Block `## Abschluss-Verifikation` (Beleg `lint`/`pytest`/`ruff`/`mypy` grün).
4. `.agent/status.md` + `.agent/log.md` aktualisieren.

**Brauchst Du zu entscheiden?** Nein — alles aus letzter Runde geklärt: Open Questions inline, kein Tag, kein Phase-1-Plan im selben Task. Neu in diesem Durchlauf laut Deinem Wunsch:
- Phase-0-Plan nach `.agent/plans/archive/` verschieben (mit Querverweis-Update).
- Leichtgewichtiges Phase-1-Skeleton (`phase-1-cli-mvp.md`) anlegen, damit der Master-Plan einen Anker für die Folgephase hat.

### Scope

**In Scope:** Re-Verifikation, Phase-0-Plan finalisieren, `status.md`/`log.md` aktualisieren, Phase-0-Plan archivieren, Phase-1-Skeleton anlegen.

**Out of Scope:** Schema v0 ändern, Phase-1 inhaltlich ausarbeiten, Git-Tag, Änderungen an `core/`, `cli/`, `specs/`, Tests, CI.

# Technical Design

### Aktueller Stand (verifiziert)

- Schema, Loader, Validator, CLI, 5 Specs, CI-Workflow vorhanden.
- Lokal grün: `uv sync` ✓, `flowcation lint specs/*.yaml` 5×✓, `pytest` 12 passed, `ruff check`/`format --check` clean, `mypy core/src cli/src` 0 issues.

### Key Decisions

1. **Schema v0 unverändert** — alle Open Questions, die Schema-Änderungen implizieren würden, werden auf Phase 1/3 verschoben.
2. **Resolution inline** im Phase-0-Plan, kein separates ADR.
3. **Archivierung** unter `.agent/plans/archive/` (Konvention bereits vorhanden für `package-manager-comparison.md`); Querverweise im Master-Plan und `AGENTS.md` werden auf den neuen Pfad gezogen.
4. **Phase-1-Skeleton** = nur Header (Status: Draft, Vorgänger, Ziel, Scope-Bullets, Stages-Platzhalter, Open Questions); keine inhaltliche Ausarbeitung in dieser Session.
5. **Kein Git-Tag.**

### Resolution-Tabelle für Phase-0-Plan

 # | Frage | Entscheidung | Ziel-Phase |
---|---|---|---|
 1 | `kind`-Enum vs. offener String | **Deferred** | Phase 1 |
 2 | Asset-Refs: Pfade vs. URI | **Resolved (v0): beides erlauben**; finale Wahl in Phase 1 | Phase 1 |
 3 | `uses:`-Auflösung | **Resolved: nur syntaktisch**; Resolver in Phase 1 | Phase 1 |
 4 | `$schema`-Pin Draft 2020-12 | **Resolved: bereits gepinnt** | — |
 5 | Conformance-Tests | **Resolved: nur Schema-Feld**; Runner in Phase 3 | Phase 3 |

### File Structure

```
.agent/
  plans/
    archive/
      phase-0-spec-schema-spike.md   # MOVED — Status Done, Resolutions, Verifikations-Block
    phase-1-cli-mvp.md                # NEW — Skeleton
    flowcation-plan.md                # MODIFIED — Querverweis auf neuen Pfad
  status.md                            # MODIFIED — Phase abgeschlossen
  log.md                               # MODIFIED — neuer Eintrag
AGENTS.md                              # MODIFIED — Link auf phase-0-...md → archive/
```

Unverändert: `schema/`, `core/**`, `cli/**`, `specs/*.yaml`, `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock`.

# Validation

- Re-Verifikation grün (lint/pytest/ruff/mypy) — sonst kein Status-Wechsel.
- Phase-0-Plan: Status `Done`, Resolution-Tabelle (5 Zeilen), Abschluss-Verifikations-Block.
- `git mv` für Archivierung (History bleibt erhalten); kein toter Link nach `phase-0-spec-schema-spike.md` (`grep -r phase-0-spec-schema-spike .agent/ AGENTS.md` zeigt nur Archiv-Pfade).
- `status.md` zeigt Phase 0 abgeschlossen, nächster Schritt = Phase 1.
- `log.md` enthält neuen Eintrag mit Datum + Kommandos + Ergebnis.
- Phase-1-Skeleton existiert mit Status `Draft`.

Keine Tests werden geändert.

# Delivery Steps

###   Step 1: Phase-0-Plan finalisieren (Status, Resolutions, Verifikation)
Der Phase-0-Plan ist als _Done_ erkennbar und enthält Resolution + Verifikations-Beleg.

- Vorab: `uv sync` + `uv run flowcation lint specs/*.yaml`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy core/src cli/src` lokal ausführen; Ergebnisse puffern.
- Header in `.agent/plans/phase-0-spec-schema-spike.md`: `Status: Draft` → `Status: Done`; Zeile `> **Abgeschlossen**: <ISO-Datum>` ergänzen.
- Direkt unter `## Open Questions` Block `## Resolution der Open Questions (Phase-0-Abschluss)` einfügen — Tabelle mit den 5 Einträgen aus dem Technical-Design-Tab.
- Vor `## Nächste Phase` Block `## Abschluss-Verifikation` einfügen: Bullet-Liste der ausgeführten Kommandos mit Ergebnis (`12 passed`, `5× ✓`, _All checks passed_) + Verweis auf `.agent/log.md`-Eintrag.
- Stages 1–8 nicht umnummerieren, Open Questions nicht löschen.

###   Step 2: status.md und log.md aktualisieren
Die projektweiten Statusdokumente reflektieren den abgeschlossenen Phase-0-Stand.

- `.agent/status.md`:
  - `Phase:` → `Phase 0 abgeschlossen — Vorbereitung Phase 1`.
  - `Zuletzt aktualisiert:` auf aktuelles ISO-Datum.
  - `Aktueller Stand`: Bullet ergänzen mit Verweis auf Verifikations-Run.
  - `Nächste Schritte`: Punkt _Phase 0 final abnehmen_ entfernen; verbleiben: (1) Phase-1-Plan ausarbeiten, (2) optional Tag `v0.0.0-phase0`.
- `.agent/log.md`:
  - Neuer Datums-Eintrag oben mit Kommandos + Ergebnis als Bullet-Liste; Hinweise: _Resolutions dokumentiert_, _Status Draft → Done_, _Plan archiviert_, _Phase-1-Skeleton angelegt_.
  - Sprache Deutsch, Du-Ansprache.

###   Step 3: Phase-0-Plan nach archive/ verschieben
Phase-0-Plan liegt unter `.agent/plans/archive/`, alle Querverweise zeigen auf den neuen Pfad.

- `git mv .agent/plans/phase-0-spec-schema-spike.md .agent/plans/archive/phase-0-spec-schema-spike.md` (Verzeichnis ist vorhanden — `package-manager-comparison.md` liegt dort).
- In `AGENTS.md`: Pfad in Sektion _Aktuelle Phase_ auf `.agent/plans/archive/phase-0-spec-schema-spike.md` aktualisieren und Vermerk „(abgeschlossen)" anhängen; aktuelle Phase auf Phase 1 umstellen mit Verweis auf neues Skeleton.
- In `.agent/plans/flowcation-plan.md`: ggf. Querverweis auf den Phase-0-Plan auf neuen Archiv-Pfad ziehen (per Suche nach `phase-0-spec-schema-spike`).
- Verifizieren: keine toten Links (`grep -r "phase-0-spec-schema-spike" .agent/ AGENTS.md` zeigt nur Archiv-Pfade).

###   Step 4: Phase-1-Skeleton anlegen
`.agent/plans/phase-1-cli-mvp.md` existiert als Draft-Skeleton, das die Folgephase verankert.

- Header: `Status: Draft`, `Erstellt: <ISO-Datum>`, `Vorgänger: archive/phase-0-spec-schema-spike.md`, Master-Plan-Link auf Phase 1 (Zeilen 282–288).
- Sektion `## Ziel`: Kurzform aus Master-Plan Phase 1 (CLI-MVP `init`/`add`/`pull`/`lock`/`verify`/`publish`/`yank`/`search` + MCP-Server + Codegen-Target SwiftUI + Browser-Playground + Lockfile mit Generator-Pin).
- Sektion `## Scope` (In/Out) — Out: Registry-Backend, Conformance-Runner, weitere Codegen-Targets, Federation, Desktop-App.
- Sektion `## Stages`: nur Überschriften-Platzhalter (z. B. `Stage 1 — CLI-Skelett init/add/lint`, `Stage 2 — Resolver + lock/verify`, `Stage 3 — Codegen-Pipeline SwiftUI`, `Stage 4 — MCP-Server`, `Stage 5 — Browser-Playground`); keine Detail-Ausarbeitung.
- Sektion `## Open Questions`: Übernahme der aus Phase 0 verschobenen Punkte (`kind`-Enum, Asset-Ref-URI-Schema final, Resolver-Mechanik, Modell-Pin-Drift) + Hinweis auf [`flowcation-plan.md`](./flowcation-plan.md) Sektion _Offene Punkte_.
- Sprache Deutsch, Du-Ansprache; keine Implementierungs-Annahmen, die später Verbindlichkeit suggerieren.