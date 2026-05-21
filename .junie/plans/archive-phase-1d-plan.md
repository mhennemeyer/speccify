---
sessionId: session-260521-155933-q9i0
---

# Requirements

### Overview & Goals

Phase 1d (Browser-Playground unter `apps/web/`) ist vollständig abgeschlossen (alle Steps 0–6, 183 Pytest grün, Frontend `pnpm build` grün, CI erweitert, Master-Plan synchronisiert). Offen ist nur der User-Tag `v0.4.0-phase-1d`, den der Agent laut `.agent/rules.md` nicht selbst setzen darf.

Diese Aufgabe schließt Phase 1d organisatorisch ab — analog zu Phasen 1a / 1b / 1c.

### Scope

**In Scope**
- `git mv .agent/plans/phase-1d-browser-playground.md .agent/plans/archive/phase-1d-browser-playground.md`.
- Frontmatter im verschobenen Plan: `isActive: true` → `isActive: false`.
- `AGENTS.md`: Verweise auf den aktiven 1d-Plan auf den `archive/`-Pfad umstellen; 1d in Liste archivierter Pläne.
- `.agent/status.md`: Meta + „Nächste Schritte"-Block aktualisieren.
- `.agent/log.md` (falls existent): kurzer Eintrag „Phase 1d archiviert".

**Out of Scope**
- Inhaltliche Änderungen am Phasen-Plan (nur Frontmatter-Flip).
- Setzen des Git-Tags `v0.4.0-phase-1d` (User-Aufgabe).
- Entwurf des Phase-2-Plans (Registry-MVP).
- Code- oder Test-Änderungen.

### Acceptance Criteria
- `.agent/plans/phase-1d-browser-playground.md` existiert nicht mehr; `.agent/plans/archive/phase-1d-browser-playground.md` existiert mit `isActive: false`.
- `AGENTS.md` referenziert den archivierten Pfad.
- `.agent/status.md` reflektiert den archivierten Zustand.
- `uv run pytest` weiterhin grün (183 Tests).

# Technical Design

### Current Implementation

- **Phasen-Plan**: `.agent/plans/phase-1d-browser-playground.md` mit `isActive: true`, alle Steps 0–6 abgehakt.
- **AGENTS.md**: Abschnitt „Aktuelle Phase" verweist auf den aktiven 1d-Plan; Archivliste enthält 1a/1b/1c.
- **`.agent/status.md`**: Step 6 als abgeschlossen dokumentiert; „nächster Schritt = Phasen-Plan archivieren analog 1a/1b/1c" steht bereits drin.
- **Archiv-Konvention**: `phase-1a-...`, `phase-1b-...`, `phase-1c-...` — 1:1 übernehmen.

### Key Decisions

1. **`git mv` statt `cp + rm`** — Datei-History bleibt erhalten.
2. **Frontmatter-Flip `isActive: false`** als einzige Inhalts-Änderung.
3. **Tag `v0.4.0-phase-1d` bleibt ungesetzt** — User-Aufgabe.
4. **Kein Phase-2-Plan** in diesem Schritt.

### File Structure

```
.agent/
├── plans/
│   └── archive/
│       └── phase-1d-browser-playground.md   (NEU: verschoben)
├── status.md                                 (MODIFIZIERT)
└── log.md                                    (ggf. MODIFIZIERT)
AGENTS.md                                     (MODIFIZIERT)
```

### Risks

- **History-Verlust** → explizites `git mv`.
- **Dangling Links** → vor Commit per Repo-Suche prüfen.
- **Frontmatter-Bruch** → nur eine Boolean-Zeile ändern.

# Delivery Steps

###   Step 1: Phasen-Plan archivieren und isActive flippen
Der 1d-Phasen-Plan liegt als historisches Dokument unter `.agent/plans/archive/` und ist als inaktiv markiert.

- `git mv .agent/plans/phase-1d-browser-playground.md .agent/plans/archive/phase-1d-browser-playground.md` ausführen (History-Erhalt).
- In der verschobenen Datei nur die Frontmatter-Zeile `isActive: true` auf `isActive: false` ändern.
- Per Repo-Suche prüfen, ob andere Markdown-Dateien auf den alten Pfad verweisen, und ggf. anpassen.

###   Step 2: AGENTS.md, status.md und log.md auf Archiv-Zustand umstellen
Die Onboarding-/Status-Dokumente reflektieren, dass Phase 1d archiviert ist und der Tag-Vorschlag `v0.4.0-phase-1d` beim User liegt.

- `AGENTS.md` Abschnitt „Aktuelle Phase": Verweis auf den 1d-Plan auf den `archive/`-Pfad umstellen (analog 1c); ergänzen, dass der Plan archiviert ist; Tag-Vorschlag als offen markieren.
- `AGENTS.md`: 1d in die Liste archivierter Phasen-Pläne aufnehmen (Stil wie 1a/1b/1c).
- `.agent/status.md`: Meta-Block um Archiv-Hinweis ergänzen; „Nächste Schritte"-Liste: 1d-Archivierung als `[x]`; „Phase-2-Plan-Entwurf (Registry-MVP) nach User-Tag" als nächster offener Punkt.
- `.agent/log.md` (nur falls existent): kurzen, datierten Eintrag „Phase 1d Phasen-Plan archiviert" anhängen.
- Abschließend `uv run pytest` als Sanity-Check (Erwartung: 183 grün).