---
sessionId: session-260603-134934-1pw0
---

# Requirements

### Overview & Goals

Die `.agent/agent.md` ist inkonsistent mit `.agent/plans/active.json`:
- `active.json` zeigt `phase-6-landing-and-docs` als aktiven Plan.
- `agent.md` behauptet im Abschnitt "Aktuelle Phase" noch "Kein aktiver Plan in `.agent/plans/` (außer Master-Plan)".

Ziel: Diese Inkonsistenz beheben, sodass `agent.md` korrekt Phase 6 als aktuell laufende Phase ausweist und auf den Plan verlinkt.

### Scope

**In Scope**
- Anpassung des "Aktuelle Phase"-Blocks in `.agent/agent.md` (Symlink-frei, nur diese Datei).
- Kurzer neuer Absatz für **Phase 6 — Landingpage + Doku-Site**, inkl. Status (Stage 0 abgeschlossen, Stages 1–7 offen) und Link auf `./.agent/plans/phase-6-landing-and-docs.md`.
- Erwähnung, dass Phase 7 (Visual-Regression-Vertiefung) als optionaler Backlog-Plan existiert, inkl. Link.

**Out of Scope**
- Keine Änderungen an `phase-6-landing-and-docs.md`, `phase-7-...md`, `speccify-plan.md`.
- Kein Code-Change im Projekt.
- Keine neuen Verifikationszahlen (Test-Counts bleiben Phase-5c-Stand, bis Phase 6 abgeschlossen ist).

### Acceptance Criteria

- Im Block "Aktuelle Phase" steht **Phase 6** als aktiver Plan an erster Stelle.
- Der Satz "Kein aktiver Plan in `.agent/plans/`" ist entfernt oder umformuliert.
- Link `./.agent/plans/phase-6-landing-and-docs.md` ist klickbar und auflösbar.
- Bestehende Phasen-5c/5b/5a/4/3/2/0-Absätze bleiben unverändert (Historie).

# Technical Design

### Current State

Datei: `/Users/mhennemeyer/Desktop/Work/speccify/.agent/agent.md`.

Relevanter Block (am Anfang des Phasen-Abschnitts):

> **Phase 5c abgeschlossen (2026-05-29) — Visual-Regression-Skeleton produktiv.** …
>
> … (Phase 5b, 5a, 4, 3, 2 Absätze) …
>
> Kein aktiver Plan in `.agent/plans/` (außer Master-Plan); Phase-5c-Plan archiviert: …

Dieser Schlusssatz ist veraltet — `active.json` zeigt `phase-6-landing-and-docs`, und die Plan-Datei existiert.

### Proposed Change

**Eine** gezielte Text-Anpassung: vor dem bestehenden "Phase 5c abgeschlossen…"-Absatz einen neuen Absatz für die aktive Phase 6 einfügen, und den veralteten "Kein aktiver Plan…"-Satz ersetzen.

Vorgeschlagener neuer Block (ersetzt den jetzigen "Kein aktiver Plan…"-Satz, eingefügt **oberhalb** des Phase-5c-Absatzes):

```markdown
**Phase 6 aktiv — Landingpage + Doku-Site (`speccify.io`).** Stage 0 abgeschlossen (10 Open Questions vom User bestätigt, 2026-06-02): Astro Starlight, neuer Workspace-Member `apps/marketing/`, Vercel-Hosting, Plausible, Iframe-Playground, EN-only. Stages 1–7 noch offen. Plan: [`phase-6-landing-and-docs.md`](./.agent/plans/phase-6-landing-and-docs.md). Optionaler Folge-Backlog: [`phase-7-visual-regression-deepening.md`](./.agent/plans/phase-7-visual-regression-deepening.md) (S1–S7, frei wählbar).
```

Der veraltete Satz "Kein aktiver Plan in `.agent/plans/` (außer Master-Plan); Phase-5c-Plan archiviert: …" wird gekürzt auf nur noch den Archiv-Hinweis-Teil (Phase-5c-Plan archiviert + Vorgänger-Tags), ohne den irreführenden "Kein aktiver Plan"-Vorspann.

### File Structure

Nur **eine** Datei wird angefasst:
- `.agent/agent.md` (modify)

Keine neuen Dateien, keine Symlinks, keine Code-Änderungen.

### Risks

 Risiko | Mitigation |
---|---|
 Versehentliches Überschreiben anderer Abschnitte | Punktuelle Replace-Operation nur auf den beiden identifizierten Sätzen, Rest unangetastet. |
 Drift erneut bei Phase-6-Abschluss | Phase-6-Stage 7 sieht ohnehin ein `agent.md`-Update vor — dann wird dieser Block wieder ausgetauscht. |

# Delivery Steps

###   Step 1: Phase-6-Block in agent.md einfügen
Neuer Absatz "Phase 6 aktiv …" steht oberhalb des Phase-5c-Absatzes in `.agent/agent.md`.

- In `.agent/agent.md` direkt **vor** dem bestehenden Absatz `**Phase 5c abgeschlossen (2026-05-29) …**` einen neuen Absatz einfügen.
- Inhalt: Status Phase 6 (Stage 0 done, Stages 1–7 offen), Verweis auf Stage-0-Entscheidungen (Astro Starlight, `apps/marketing/`, Vercel, Plausible, Iframe, EN-only).
- Markdown-Link auf `./.agent/plans/phase-6-landing-and-docs.md` einbauen.
- Markdown-Link auf optionalen Backlog `./.agent/plans/phase-7-visual-regression-deepening.md` einbauen.

###   Step 2: Veralteten "Kein aktiver Plan"-Satz korrigieren
Der irreführende Satz ist entfernt; Archiv-Hinweise bleiben erhalten.

- Im Schluss-Absatz den Vorspann "Kein aktiver Plan in `.agent/plans/` (außer Master-Plan); " entfernen.
- Der nachfolgende Teil ("Phase-5c-Plan archiviert: … Phase-5b-Plan archiviert: … Phase-5a-Plan archiviert: …") bleibt unverändert.
- Sicherstellen, dass alle anderen Phasen-Absätze (5c, 5b, 5a, 4, 3, 2, 0, 1a-0) wortgleich erhalten bleiben.
- Visueller Smoke-Check: Datei in Markdown-Vorschau öffnen, Links auf beide Plan-Dateien klicken — beide müssen auflösbar sein.