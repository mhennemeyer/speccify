---
station: Doing
order: 39
created: 2026-09-14
needs_human: true
ready: true
open_question: null
parent: null
---
# QA-Brücke: die laufende App von außen prüfen

## Why

Speccify ist eine Tauri-App. Auf macOS gibt es keinen WebDriver dafür und
der WKWebView bietet kein Chrome-DevTools-Protokoll. Playwright kann darum
nur das Mock-UI steuern, nicht die gebündelte App mit echten Rust-Befehlen,
echtem PTY-Terminal und echter Zwischenablage. Abnahmen wie Spec 011
brauchten deshalb eine menschliche Checkliste. Das QA-Werkzeug
`speccify-qa` (tec-e2e-Muster: Abnahme = automatische Tests) braucht einen
Weg in die echte App.

## What

- Ein HTTP-Endpunkt im App-Prozess auf `127.0.0.1`, nur aktiv mit
  `--qa-bridge=<port>` (oder `SPECCIFY_QA_BRIDGE=<port>`), geschützt durch
  ein Bearer-Token (`SPECCIFY_QA_TOKEN` oder zufällig erzeugt). Port, Token
  und PID stehen in `<tmp>/speccify-qa-bridge.json` (0600), damit Tests sie
  finden.
- Befehle: `GET /health`, `GET /windows` (Label, Titel, sichtbar, fokussiert,
  Position, Größe, Skalierung), `POST /eval` (JavaScript als Funktionsrumpf
  in einem Fenster ausführen, Ergebnis zurück, Timeout), `POST /invoke`
  (Tauri-Befehl aus dem Fenster aufrufen), `POST /focus`, `POST /screenshot`
  (macOS: `screencapture -R` mit dem Fensterrechteck; sonst 501).
- Frontend-Haken `window.__speccifyQa`: Terminalpuffer als Text und
  Terminal-Bereitschaft, damit Tests lesen, was im Agent-Terminal steht.
- `scripts/dev.sh --qa-bridge=<port>` reicht das Flag an die gebündelte App
  durch.
- Out of scope: Aufzeichnung, Windows/Linux-Screenshots, Zugriff in
  sandboxed iframes (Ad-hoc-UI aus Spec 038) — dort ist nur der äußere
  Rahmen sichtbar.

## Acceptance

- Wenn die App ohne Flag und ohne Umgebungsvariable startet, dann lauscht
  kein Brücken-Port und es entsteht keine Discovery-Datei.
- Wenn die App mit `--qa-bridge=<port>` läuft, dann antwortet `/health`
  nur mit gültigem Token; ohne Token 401.
- Wenn ein Test `/eval` mit `return document.title` gegen ein Fenster
  schickt, dann kommt der Titel zurück; ein Fehler im Skript kommt als
  `ok: false` mit Meldung zurück, ein Endlos-Skript als Timeout.
- Wenn ein Projektfenster mit laufendem Terminal offen ist, dann liefert
  `window.__speccifyQa.terminalText()` den sichtbaren Pufferinhalt.
- Wenn `speccify-qa` die Abnahme `speccify-011-auftrag` gegen die App mit
  Brücke fährt, dann laufen die fünf Prüfschritte als Tests ohne Checkliste.

## Decisions

- D1 (2026-09-14, BO): Die Brücke ist nie im Normalbetrieb aktiv; für
  Abnahmen läuft die gebündelte App bewusst mit dem Flag.
- D2 (2026-09-14, BO): Die menschliche Checkliste bleibt im QA-Kern nur für
  technisch nicht automatisierbare Punkte (Optik); automatisierbare
  Schritte werden Tests.
- D3 (2026-09-14): JavaScript-Ausführung über `WebviewWindow::eval` mit
  Rückkanal über den Tauri-Befehl `qa_eval_result`; kein WebDriver.
- D4 (2026-09-14): Die Discovery-Datei ersetzt das Weiterreichen von Token
  per Umgebung, weil `open` auf macOS die Shell-Umgebung nicht vererbt.

## Tasks

- [x] Rust-Modul `qa_bridge.rs`: Konfiguration, Token, Discovery-Datei,
      tiny_http-Server, Routen, Eval-Register mit Condvar.
      Fensterabfragen und `eval` über `run_on_main_thread` mit 5-s-Timeout
      (added): ein blockierter Hauptthread liefert 503 statt zu hängen.
- [x] `lib.rs`: Registry verwalten, Server im Setup starten, Befehl
      `qa_eval_result` registrieren.
- [x] Frontend: `lib/qa.ts` mit `window.__speccifyQa`; TerminalPanel meldet
      den Puffer an.
- [x] `scripts/dev.sh --qa-bridge=<port>`.
- [x] Tests: Konfigurationsparser, Wrapper-JS, Auth-Ablehnung; Browser-Suite
      für den Frontend-Haken am Mock.
- [x] Playbooks (`stand-und-ui.md`, `weiterentwicklung.md`) und
      `docs/app-bedienen.md` ergänzen.
- [x] Gegenstück in speccify-qa (Adapter, Page-Objects, Abnahme 011 als
      Tests) — Spec 003 dort.

## Verification

2026-09-14 (Build läuft, Klick-Abnahme steht aus):

- `cargo test -p speccify-desktop`: 115 grün (fünf neue für Konfiguration,
  Autorisierung, Wrapper-Skript, Eval-Register mit Timeout); `cargo fmt`,
  `pnpm typecheck` grün. Mock-Suite `test_handover` grün, jetzt mit Prüfung
  des QA-Hakens (`terminalReady`/`terminalText` folgen dem Terminal).
- Gebündelte App mit `--qa-bridge=18769`: Discovery-Datei mit Rechten 0600,
  `/health` ohne Token 401, mit Token `{ok, pid, version}`.
- Befund: Der erste Build hing bei `/windows` und `/eval`, weil der neue
  Build die macOS-Freigabe für den Ordner „Schreibtisch“ erneut erfragt und
  der Systemdialog den Hauptthread blockiert. Seitdem laufen Fensterabfragen
  und `eval` mit Timeout auf dem Hauptthread; die Brücke antwortet dann mit
  `503 Der Hauptthread der App antwortet nicht (offener Systemdialog?)`.
- Nach BO-Bestätigung des Dialogs: Abnahme `speccify-011-auftrag` aus
  `speccify-qa` gegen die gebündelte App (`abnahme run`): 6 Tests grün, zweimal
  hintereinander (fünf Stufe 2 über die Brücke, einer Stufe 0 gegen den Mock).
  Die Tests öffnen dieses QA-Repo als zweites Projektfenster mit reiner Shell
  (Agent-Befehl leer per localStorage), stellen zu, kopieren, ändern eine Datei
  und stellen sie wieder her, schließen das Fenster.
- Befunde am Werkzeug, behoben: umgebrochene Terminalzeilen (`isWrapped`)
  werden zusammengefügt; Page-Objects zählen nur sichtbare Elemente (die App
  hält inaktive Bereiche mit `hidden` im DOM), schalten den Inspektor-Tab
  zurück, wenn das Terminal rechts liegt, und klicken eine gewählte Karte nicht
  erneut (das würde abwählen); ein Fenster schließt ohne Warten auf die Antwort.
- Befund am Produkt (in Spec 011 als F-QA-1): Zustellung in Claudes
  „Trust this folder“-Dialog geht verloren, die App meldet trotzdem „Eingefügt“.
- Screenshot-Route: aus der Shell funktioniert `screencapture -R` mit dem
  Fensterrechteck, aus dem App-Prozess fehlt die Freigabe „Bildschirmaufnahme“
  → Fehlertext statt Bild. Dokumentiert, nicht blockierend.
- Jeder lokale Debug-Build löst die macOS-Freigabe „Schreibtisch“ neu aus
  (Ad-hoc-Signatur wechselt); die Brücke meldet das als 503. Vorschlag: lokalen
  Build in `dev.sh` mit der Developer-ID signieren — BO-Entscheid, nicht Teil
  dieser Spec.

## Questions
