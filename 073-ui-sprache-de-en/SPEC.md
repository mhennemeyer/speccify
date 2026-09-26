---
station: Doing
order: 73
created: 2026-09-26
needs_human: true
ready: true
modules: desktop-frontend, settings
---
# Oberfläche auf Englisch, umschaltbar zwischen Deutsch und Englisch

## Why

Die Desktop-App spricht heute durchgehend Deutsch, die Website und Doku
Englisch. Für Kollegen und für die Produktreife (Spec 071) braucht die App eine
englische Oberfläche; wer Deutsch gewohnt ist, soll es behalten können
(Nutzerauftrag 2026-09-26: „Bitte einmal das UI auch in en. Und umschaltbar
machen zwischen de/en“).

## What

- Eine Spracheinstellung `language` in den App-Einstellungen
  (`~/.speccify/settings.json`): `system` (Vorgabe), `de`, `en`. Umschaltbar im
  Dashboard unter Einstellungen und im Einstellungsblatt der Projekt- und
  Workspace-Fenster; wirkt sofort in allen Fenstern, ohne Neustart.
- Alle sichtbaren Texte des React-Frontends (57 Ansichten und Komponenten,
  Größenordnung 500 Texte inklusive Titeln, Platzhaltern, Hinweisen,
  Statuszeilen) laufen über eine Übersetzungsfunktion; Deutsch bleibt der
  Quelltext, Englisch kommt aus einem Wörterbuch. Fehlt ein Eintrag, erscheint
  der deutsche Text, nie ein Schlüssel.
- `document.documentElement.lang` folgt der Sprache; Datums- und Zahlformate
  folgen ihr, wo das Frontend formatiert.
- Mock und Browser-Tests bleiben auf Deutsch (der Mock liefert `language: de`),
  ein neuer Test prüft Umschalten, Persistenz und Sofortwirkung.

Nicht enthalten (eigene Folge-Spec): Meldungen aus dem Rust-Teil (rund 60
deutsche Fehler- und Statustexte, etwa aus `terminal_open`, Register,
Einrichten) — sie erreichen die Oberfläche als Text und bleiben vorerst
deutsch; ebenso die Vorlagen für `agent.md`/Policy (bewusst Englisch bzw.
Projektsache) und die Website.

## Acceptance

- Wenn `language` auf `en` steht, dann zeigt jedes Fenster englische
  Bedienelemente, Titel, Hinweise und Dialoge; Umschalten zurück auf `de`
  stellt Deutsch her — beides ohne Neustart und in allen offenen Fenstern.
- Wenn `system` gewählt ist, dann folgt die Sprache der Systemsprache: Deutsch
  bei `de*`, sonst Englisch.
- Wenn ein englischer Eintrag fehlt, dann steht der deutsche Text da, kein
  Schlüssel und kein leerer String.
- Wenn die bestehenden Browser-Suiten laufen, dann bleiben sie grün (Mock auf
  Deutsch); der neue Test prüft den Wechsel.
- Wenn ein Text Platzhalter trägt (Zahlen, Namen, Pfade), dann ist er in beiden
  Sprachen korrekt eingesetzt.

## Decisions

1. 2026-09-26: Deutsch als Schlüssel (`t("Neu starten")`) statt abstrakter
   Schlüssel: der Bestand ist deutsch, die Änderung bleibt lokal lesbar, und
   Fehlübersetzungen fallen zurück auf verständlichen Text. Eigene kleine
   Funktion mit `useSyncExternalStore`, keine Bibliothek.
2. 2026-09-26: Die Einstellung liegt in den App-Einstellungen neben `theme`
   und wird wie das Theme über alle Fenster synchronisiert.
3. 2026-09-26: Rust-Meldungen und Vorlagen bleiben außen vor (Folge-Spec), damit
   diese Spec in einer Abnahme prüfbar bleibt.
4. 2026-09-26: Texte, die an den Agenten gehen (Übergabe-Aufträge in
   `handover.ts`, Commit-Aufträge im Git-Tab, MCP-/Tool-Prompts,
   Host-Anbindungsprüfung), bleiben deutsch — sie sind keine Oberfläche,
   und die deutschen Fassungen sind die erprobten Prompts.
5. 2026-09-26: Labels in Modul-Konstanten (Tab-Namen, Presets, Status-Maps,
   Toolbar-Knöpfe, Done-Fenster, Feldhilfen) bleiben deutsche Rohwerte und
   werden erst an der Render-Stelle mit `t(label)` übersetzt; sonst würde die
   Sprache beim Import eingefroren. `scripts/check_i18n.py` zählt solche
   Rohwerte als benutzt.
6. 2026-09-26: Das Einstellungs-Popover der Projekt-/Workspace-Fenster scrollt
   jetzt (`max-h`, `overflow-y-auto`): mit dem Sprachabschnitt lag der
   Webhook-Schalter sonst außerhalb des Fensters (Browser-Test `team_signals`).
7. 2026-09-26: `test_workspace_ui` erwartete „Nicht durchsucht: …“, die
   Fixture liefert seit 2026-09-15 „Suchbudget erreicht bei …“ — Test an die
   Fixture angepasst (Altlast, nicht durch diese Spec verursacht).

## Tasks

- [x] Infrastruktur: `src/i18n` (t, Sprache, Interpolation), Einstellung
      `language` in Rust-Settings und Frontend, Umschalter in beiden
      Einstellungsflächen, Sofortwirkung über Fenster hinweg, Mock auf `de`.
- [x] Alle Frontend-Texte über `t()` ziehen (je Ansicht), Platzhalter sauber.
      Drei Codemod-Durchgänge (JSX-Text, Attribute, UI-Aufrufe; Literale;
      Templates mit Ausdrücken) plus Handarbeit an Absätzen mit `<code>`.
- [x] Englisches Wörterbuch vollständig füllen; Prüfskript listet fehlende
      Einträge (`scripts/check_i18n.py`, 0 fehlend, 0 unbenutzt).
- [x] Browser-Test Sprachwechsel; bestehende Suiten grün; Typecheck.
- [x] Doku (`app-bedienen.md`, Website-Hilfe `terminal-settings`), Playbooks
      `stand-und-ui`, `website.md` („App hat deutsche Bedienelemente“
      ersetzt), lokale App neu gebaut.

## Verification

2026-09-26, Codebasis main nach 207d398, alles lokal:

- `pnpm --filter speccify-desktop typecheck`: grün.
- `python3 scripts/check_i18n.py --allow-code`: 802 Schlüssel im Quelltext,
  836 englische Einträge, 0 fehlend, 0 unbenutzt, keine
  Platzhalter-Abweichung.
- Browser-Suiten gegen den Mock (Vite auf 5199, Chrome): 27 von 27
  `scripts/test_*.mjs` ohne eigenen Server grün, darunter neu
  `test_language.mjs` (en aus den Einstellungen, Live-Wechsel de↔en im
  Einstellungsblatt, `language: "de"` per `save_settings` persistiert, Mock
  ohne Parameter deutsch); `test_landing_screenshots.mjs` braucht die
  Astro-Site auf 4321 und wurde nicht ausgeführt. Die vier Tests mit eigenem
  Server (`markdown_mermaid --serve`, `updates --serve`,
  `terminal_preferences`, `agent_settings`) grün.
- `cargo fmt --check`, `cargo test -p speccify-desktop`: grün (134 Tests).
- Lokale App (Bundle neu gebaut, QA-Bridge): Dashboard → Settings → English
  schaltet sofort um — Navigation („Projects, Library, Environment, Help“),
  Settings-View-Überschriften („Appearance, Language, Project detection, …“),
  Projekte-View; das offene Workspace-Fenster folgt ohne Neustart (Tabs
  „Files, Org, Tech, Specs, Help“, Toolbar-Titel „Hide navigator (⌘0)“,
  „Switch to light“). `~/.speccify/settings.json` trägt `language: "en"`;
  zurück auf „System“ liefert Deutsch (`lang="de"`), Datei wieder `system`.
  Erster Build zeigte die Settings-View noch deutsch: die Dashboard-Views
  hingen als konstante Elemente in `SECTIONS`, React übersprang sie beim
  Sprachwechsel — behoben (Komponententyp statt Element), im zweiten Build
  bestätigt.
- Beobachtung am Rande (nicht durch diese Spec): das gehostete
  Workspace-Terminal mountet xterm erst, wenn das Fenster einen Frame zeichnet
  (`requestAnimationFrame` im Mount-Effekt); bei `visibilityState: hidden`
  (Fenster verdeckt/anderer Space) bleibt der Container leer, die Host-Sitzung
  läuft weiter und `terminal_live` meldet sie. Kein Datenverlust, aber ein
  Wiederanhängen erst beim Sichtbarwerden.

## Questions

Keine.
