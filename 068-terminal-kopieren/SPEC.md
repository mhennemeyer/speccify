---
station: Doing
order: 68
created: 2026-09-24
needs_human: true
ready: true
parent: 051-terminal-findings-08
---
# Kopieren aus dem Agent-Terminal

## Why

Text im Agent-Terminal lässt sich markieren, aber ⌘C quittiert macOS mit dem
Fehlerton und die Zwischenablage bleibt leer (Nutzer-Finding 2026-09-24).
Ergebnisse, Pfade und Fehlermeldungen des Agenten sind so nicht weiterverwendbar.

## What

⌘C (bzw. Strg+Umschalt+C) kopiert die xterm-Auswahl zuverlässig, unabhängig
davon, wo im Fenster der Fokus liegt, und schließt das Tastenereignis ab, damit
kein Systemton entsteht. Menü „Bearbeiten → Kopieren" und Kontextmenü bedienen
dieselbe Auswahl. Das Ergebnis ist im Terminalkopf sichtbar („Kopiert" oder der
Fehlergrund). Ohne Auswahl bleibt Ctrl-C SIGINT; ⌘V fügt weiter ein.

Nicht enthalten: eigenes Kontextmenü im Terminal, Kopieren-auf-Auswahl wie in
iTerm, Windows-/Linux-Nativabnahme.

## Acceptance

- Wenn Text markiert ist und ⌘C gedrückt wird, dann steht der Text in der
  Zwischenablage, kein ^C erreicht den PTY, und das Ereignis ist als erledigt
  markiert (kein Fehlerton).
- Wenn der Fokus außerhalb des Terminals liegt und keine fremde Auswahl
  besteht, dann kopiert ⌘C trotzdem die Terminalauswahl.
- Wenn ein anderes Feld eine eigene Auswahl hat, dann gehört ⌘C diesem Feld.
- Wenn nichts markiert ist, dann bleibt ⌘C bzw. Ctrl-C dem Terminal überlassen.
- Wenn das Kopieren scheitert, dann nennt der Terminalkopf den Grund statt
  still nichts zu tun.

## Decisions

1. 2026-09-24: Ursache aus dem Verhalten abgeleitet: xterm hält seine Auswahl
   selbst, der DOM hat keine; WebKit deaktiviert deshalb das Menü „Kopieren",
   und ein Tastenereignis ohne `preventDefault` gilt als unbehandelt → Fehlerton.
   Der bisherige Handler lief nur bei Fokus im xterm-Textfeld und rief das
   Plugin ohne Rückmeldung auf. Kopiert wird jetzt fensterweit in der
   Capture-Phase, mit Rückfallwegen (Plugin → `navigator.clipboard` →
   `execCommand`) und sichtbarem Ergebnis.
2. 2026-09-24: `macOptionClickForcesSelection` an, damit ⌥-Ziehen auch dann
   markiert, wenn ein TUI die Maus beansprucht. Claude Code 2.1.281 aktiviert
   beim Start kein Maus-Tracking (im PTY geprüft: nur Modi 1004/2004/2026/2031).

## Tasks

- [x] Ursache eingrenzen (Code, Capabilities, Host-Modi, Tastenhandler).
- [x] Fensterweites Kopieren, `copy`-Ereignis, Hinweis und Prüfhilfen umsetzen.
- [x] Browser-Regression (Tastatur, Fokus außerhalb, ohne Auswahl) ergänzen.
- [x] Lokale App neu bauen, mit QA-Brücke am echten PTY prüfen, Doku nachziehen.

## Verification

2026-09-24, lokaler Debug-Build 0.8.6 (Developer-ID-signiert, `codesign --verify
--deep --strict` bestanden), Claude Code 2.1.281:

- `pnpm --filter speccify-desktop typecheck` bestanden.
- `node scripts/test_terminal_preferences.mjs` bestanden, neu darin: ⌘C mit
  Auswahl ist `defaultPrevented`, schreibt über das Plugin, sendet kein ^C;
  Fokus außerhalb kopiert ebenfalls; ohne Auswahl keine Schreibung.
- Gebündelte App über die QA-Brücke in einem Wegwerfprojekt mit echtem PTY
  (Claude-Trust-Dialog als Puffer): echte ⌘C-Tastendrücke über System Events
  kopierten dreimal in Folge das markierte Wort in die Systemzwischenablage
  (`pbpaste`), Hinweis „Kopiert" im Terminalkopf, Ereignis als behandelt
  markiert; mit Fokus auf dem Fenster statt dem Terminal ebenfalls. Der PTY
  blieb unberührt (kein ^C, Dialog stand weiter). Ohne Auswahl blieb die
  Zwischenablage unverändert. Zwischenablage des Nutzers danach wiederhergestellt,
  Wegwerffenster geschlossen.
- Menüpfad: ein natives copy-Ereignis kommt nachweislich an (Bearbeiten →
  Kopieren); der Handler dafür ist eingebaut, aber nicht per Menüklick geprüft.
- Offen: menschliche Sichtabnahme (Fehlerton hörbar weg?), Windows/Linux.

## Questions

Keine.
