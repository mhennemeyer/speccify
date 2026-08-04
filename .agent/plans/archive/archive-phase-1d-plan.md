---
lifecycle: done
sessionId: session-260521-081738-1i8l
---
# Requirements

### Overview & Goals

Phase 1d (Browser-Playground unter `apps/web/`) ist laut `.agent/plans/phase-1d-browser-playground.md` und `AGENTS.md` vollständig abgeschlossen: alle Steps 0–6 abgehakt, **183 Pytest grün**, Frontend `pnpm build` grün, CI um zwei Jobs erweitert, Master-Plan synchronisiert. Offen ist nur noch der User-Tag `v0.4.0-phase-1d`, den der Agent laut `.agent/rules.md` nicht selbst setzen darf.

Diese Aufgabe schließt Phase 1d organisatorisch ab — analog zum Vorgehen bei Phasen 1a / 1b / 1c:

1. Phasen-Plan `phase-1d-browser-playground.md` in `archive/` verschieben (Frontmatter `isActive: false`).
2. Verweise in `AGENTS.md`, `.agent/status.md`, `.agent/log.md` (falls vorhanden) auf den archivierten Pfad umstellen.
3. Den Hinweis behalten, dass der User den Tag `v0.4.0-phase-1d` noch setzen muss (kein Agent-Set).

### Scope

**In Scope**
- `git mv .agent/plans/phase-1d-browser-playground.md .agent/plans/archive/phase-1d-browser-playground.md`.
- Frontmatter im verschobenen Plan: `isActive: true` → `isActive: false`.
- `AGENTS.md`: Verweise auf den aktiven 1d-Plan auf den `archive/`-Pfad umstellen; Phasen-Liste analog zu 1c ergänzen (Tag-Vorschlag-Hinweis bleibt).
- `.agent/status.md`: Meta + „Nächste Schritte"-Block aktualisieren („Phasen-Plan archiviert; Phase-2-Plan-Entwurf nach User-Tag").
- `.agent/log.md` (falls existent): kurzer Eintrag „Phase 1d archiviert".

**Out of Scope**
- Inhaltliche Änderungen am Phasen-Plan (read-only beim Verschieben außer Frontmatter-Flip).
- Setzen des Git-Tags `v0.4.0-phase-1d` (vgl. `rules.md` — explizit User-Aufgabe).
- Entwurf des Phase-2-Plans (Registry-MVP) — separater Folge-Plan nach User-Tag.
- Code- oder Test-Änderungen unter `apps/`, `core/`, `cli/`, `mcp/`.

### Acceptance Criteria
- `.agent/plans/phase-1d-browser-playground.md` existiert nicht mehr; `.agent/plans/archive/phase-1d-browser-playground.md` existiert mit `isActive: false`.
- `AGENTS.md` referenziert den archivierten Pfad und enthält keine Behauptung mehr, der 1d-Plan sei aktiv.
- `.agent/status.md` reflektiert den archivierten Zustand.
- `uv run pytest` weiterhin grün (Sanity, keine Code-Änderungen erwartet → 183 Tests).

# Technical Design

### Current Implementation

- **Phasen-Plan**: `.agent/plans/phase-1d-browser-playground.md` mit Frontmatter `sessionId: session-260519-105200-1d`, `isActive: true`. Alle Steps 0–6 abgehakt (Z. 167–208), Plan-internes Wrap-up dokumentiert.
- **AGENTS.md** (Abschnitt „Aktuelle Phase"): verweist aktuell auf `.agent/plans/phase-1d-browser-playground.md` als finalen Phasen-Plan. Archivliste enthält 1a/1b/1c im Schema `archive/<file>.md`.
- **`.agent/status.md`**: Meta-Block (Z. 5) und Phase-1d-Detail-Block (Z. 9–17) dokumentieren Step 6 als abgeschlossen, „nächster Schritt = Phasen-Plan archivieren analog 1a/1b/1c" steht bereits drin (Z. 17).
- **Archiv-Konvention** (aus `archive/`-Listing bestätigt): `phase-1a-resolver-lockfile.md`, `phase-1b-react-codegen.md`, `phase-1c-mcp-server.md` — identisches Namensschema, also `phase-1d-browser-playground.md` 1:1 verschieben.

### Key Decisions

1. **`git mv` statt `cp + rm`**, damit die Datei-History im Repo erhalten bleibt (analog 1a/1b/1c).
2. **Frontmatter-Flip `isActive: false`** als einzige Inhalts-Änderung — alles andere bleibt byte-identisch, damit der Plan als historisches Dokument lesbar bleibt.
3. **Tag-Vorschlag `v0.4.0-phase-1d` bleibt ungesetzt** und wird in `AGENTS.md` + `status.md` als offene User-Aktion stehen gelassen (vgl. `.agent/rules.md`, analog zu `v0.3.0-phase-1c`).
4. **Kein Phase-2-Plan in diesem Schritt** — `status.md` führt weiterhin „Phase-2-Plan-Entwurf nach User-Tag" als nächsten Schritt; eigene Aufgabe.

### Proposed Changes

**1. Plan verschieben**
- `git mv .agent/plans/phase-1d-browser-playground.md .agent/plans/archive/phase-1d-browser-playground.md`.
- In der verschobenen Datei: Frontmatter `isActive: true` → `isActive: false` (Zeile 3). Keine weiteren inhaltlichen Änderungen.

**2. `AGENTS.md` aktualisieren**
- Abschnitt „Aktuelle Phase": Verweis auf den 1d-Plan auf den `archive/`-Pfad umstellen (analog zum bestehenden 1c-Eintrag im selben Block).
- „Aktiver Plan: keiner" beibehalten; ergänzen, dass der 1d-Plan archiviert wurde und der Tag-Vorschlag `v0.4.0-phase-1d` weiterhin offen ist.
- Archivierten-Pläne-Liste prüfen — 1d dort als „archiviert" eintragen, falls noch nicht enthalten.

**3. `.agent/status.md` aktualisieren**
- Meta-Block (Z. 5): Satz um Hinweis erweitern, dass der Phasen-Plan jetzt unter `.agent/plans/archive/` liegt.
- „Nächste Schritte"-Liste: 1d-Archivierung als erledigt markieren (`[x]`); „Phase-2-Plan-Entwurf (Registry-MVP) nach User-Tag" als nächster offener Punkt.

**4. `.agent/log.md` (falls vorhanden)**
- Kurzer Eintrag mit Datum: „Phase 1d Phasen-Plan archiviert (`archive/phase-1d-browser-playground.md`, `isActive: false`)."
- Falls die Datei nicht existiert → überspringen (keine neue Datei nur deswegen).

### File Structure

```
.agent/
├── plans/
│   └── archive/
│       └── phase-1d-browser-playground.md   (NEU: verschoben aus plans/)
├── status.md                                 (MODIFIZIERT)
└── log.md                                    (ggf. MODIFIZIERT, sonst übersprungen)
AGENTS.md                                     (MODIFIZIERT)
```

Keine Änderungen an `apps/`, `core/`, `cli/`, `mcp/`, `codegen/`, `schema/`, `specs/`, `registry-fixtures/`, Tests oder CI.

### Risks

- **History-Verlust** bei nicht-Git-mv: vermeiden durch explizites `git mv` im Terminal.
- **Dangling Links**: andere Dokumente könnten auf `plans/phase-1d-browser-playground.md` verweisen → vor Commit per Repo-Suche prüfen und mit umstellen.
- **Frontmatter-Bruch**: nur eine Boolean-Zeile ändern, keine Strukturänderung.

# Delivery Steps

###   Step 1: Phasen-Plan in archive/ verschieben und isActive flippen
Der 1d-Phasen-Plan liegt als historisches Dokument unter `.agent/plans/archive/` und ist als inaktiv markiert.

- `git mv .agent/plans/phase-1d-browser-playground.md .agent/plans/archive/phase-1d-browser-playground.md` ausführen, damit die Datei-History erhalten bleibt.
- In der verschobenen Datei nur die Frontmatter-Zeile `isActive: true` auf `isActive: false` ändern; keine weiteren inhaltlichen Edits.
- Per Repo-Suche prüfen, ob andere Markdown-Dateien (außer den in Stage 2 abgedeckten) auf den alten Pfad `plans/phase-1d-browser-playground.md` verweisen, und dort ggf. den `archive/`-Pfad eintragen.

###   Step 2: AGENTS.md, status.md und log.md auf Archiv-Zustand umstellen
Die Onboarding-/Status-Dokumente reflektieren, dass Phase 1d archiviert ist und der Tag-Vorschlag `v0.4.0-phase-1d` weiterhin beim User liegt.

- `AGENTS.md` Abschnitt „Aktuelle Phase": Verweis auf den 1d-Plan auf den neuen `archive/`-Pfad umstellen (analog zum bestehenden 1c-Eintrag); ergänzen, dass der Phasen-Plan archiviert ist; Tag-Vorschlag `v0.4.0-phase-1d` weiterhin als offen-an-User markieren.
- `AGENTS.md`: 1d in die Liste archivierter Phasen-Pläne aufnehmen (gleicher Stil wie 1a/1b/1c).
- `.agent/status.md`: Meta-Block (Z. 5) um den Archiv-Hinweis ergänzen; in der „Nächste Schritte"-Liste die 1d-Archivierung als `[x]` ergänzen und „Phase-2-Plan-Entwurf (Registry-MVP) nach User-Tag" als nächsten offenen Punkt stehen lassen.
- `.agent/log.md` (nur falls existent): kurzen, datierten Eintrag „Phase 1d Phasen-Plan archiviert" anhängen; falls die Datei nicht existiert, Schritt überspringen (keine neue Datei anlegen).
- Abschließend `uv run pytest` als Sanity-Check laufen lassen (Erwartung: 183 grün, da keine Code-Änderungen).