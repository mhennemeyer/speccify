---
station: Doing
order: 0
created: 2026-09-10
needs_human: true
ready: true
parent: null
---
# Lokale App verfügbar halten und Startkonflikte richtig diagnostizieren

## Why

Die App soll während der Weiterentwicklung für Nutzung, Feedback und Abnahme
offen bleiben. `dev.sh` verwechselt einen belegten Port 8768 mit einer laufenden
Speccify-App. Tatsächlich hält hier Lima (PID 52270) eine Portweiterleitung;
eine native Speccify-App und Vite laufen nicht.

## What

Lesender Startstatus, frühe Portdiagnose mit tatsächlichem Besitzer, explizit
wählbarer Desktop-UI-MCP-Port und ein lokaler macOS-App-Build ohne Dev-Watcher.
Bestehende Instanzen und fremde Dienste nicht automatisch beenden. Vorhandene
MCP-Konfiguration nicht ungefragt überschreiben. Laufende App nicht bei jeder
Quelländerung neu starten; Updates und Abnahme bewusst koordinieren.

## Acceptance

- Ein fremder Listener wird nicht als Speccify bezeichnet oder beendet.
- Status/Portkonflikt werden vor Installation und Build erkannt.
- Ein ausdrücklich gewählter freier Port wird beim App-Start und in neu
  angelegten Desktop-UI-MCP-Konfigurationen konsistent verwendet.
- Die lokale gebündelte App öffnet ohne Vite/Watcher und bleibt bei späteren
  Quelländerungen unabhängig vom Buildprozess nutzbar.
- Ein vorhandener App-Build lässt sich ohne erneute Installation/Build öffnen.
- Ein nutzbarer Start wird anhand Prozess und MCP-Handshake geprüft;
  menschliche Sicht-/Terminal-Abnahme wird davon getrennt festgehalten.

## Decisions

- Nutzerauftrag 2026-09-10: Startproblem beheben und laufende Nutzung ermöglichen.
- Lima/VM nicht stoppen; für die lokale Instanz explizit Port 18768 verwenden.
- Keine parallelen App-Instanzen mit derselben Identität erzwingen; Single-Instance
  bleibt bestehen. Dev-Watcher und Alltagsinstanz sind alternative Betriebsarten.
- Lokaler Debug-App-Build mit gebündeltem Frontend; kein Release/Tag/Upload.

## Tasks

- [x] Status und frühe Portdiagnose im Startscript implementieren und testen.
- [x] Expliziten Port zwischen App-Server und neuen Konfigurationsvorlagen teilen.
- [x] Gebündelten lokalen App-Modus und schnellen Wiederöffnungsweg ergänzen.
- [x] App starten und Prozess/Handshake prüfen; für Nutzer offen lassen.
- [x] Playbooks und Entscheidungsreihenfolge aktualisieren.

## Verification

- Ausgangsbefund: `lsof` zeigt Lima auf 127.0.0.1:8768, keinen Listener auf 1420;
  Prozessprüfung zeigt keine native Speccify-App. Keine Prozesse beendet.
- Speccify-Skill: Suche nach `development` ohne Bibliothekstreffer; Projekt-Spec
  und überprüfbare Fehlerfälle verwendet. Kein Signierungs-/Notarisierungslauf.
- `python scripts/test_dev_runtime.py`: 7 Tests bestanden; fremder Listener,
  freier Port, ungültige/gültige Ports, frühe Ablehnung vor Vorbereitung und Status.
- `cargo test -p speccify-desktop`: 61 bestanden, 1 bestehender Test ignoriert.
  Zwei neue Tests zu Portauswahl und gültigen JSON-/TOML-Vorlagen mit gleichem Endpoint.
- Frontend-Typecheck und Build bestanden; bestehende große Vite-Chunk-Warnung.
  `cargo fmt --all --check`, Ruff für den neuen Test und `git diff --check` grün.
- `dev.sh --app --prepared --ui-port=18768`: Frontend gebaut, native App gebündelt,
  ohne Signierung. `open` innerhalb der Ausführungssandbox meldete irreführend
  `kLSNoExecutableErr`; Binary und Bundle waren vorhanden. Derselbe Öffnungsaufruf
  außerhalb der Sandbox erfolgreich, kein erneuter Build nötig.
- Laufende App: PID 37974, Bundle `target/debug/bundle/macos/Speccify.app`,
  Listener ausschließlich 127.0.0.1:18768. Kein Vite-Listener auf 1420. Lima PID
  52270 hält weiterhin 8768. Stand dieser Beobachtung: 2026-09-10, 12:43 UTC.
- MCP: initialize 200 mit `speccify-desktop-ui-mcp`, Version 0.6.0,
  Protokoll 2025-03-26; initialized 202; tools/list enthält ask_bo/ask_bo_result.
  Skill `mcp-client-streamable-http`: Identität und Handshake geprüft, kein
  vollständiger Transport-Konformitätstest. Fremder Origin wird mit 200 akzeptiert;
  bestehender Core-Befund separat in Spec 014, Sicherheitsprüfung damit offen.
- `dev.sh --app --prepared --ui-port=18768` bei laufender App verweigert Neubau
  vor Vorbereitung; `--open --ui-port=18768` aktiviert dieselbe PID ohne Neustart.
- App für Nutzung offen gelassen. Menschliche Sicht-/Terminal-Abnahme und
  vollständiger Workflow-Roundtrip bleiben offen; daher Doing/ready/needs_human.

## Questions

- Menschliche Abnahme: Ist das App-Fenster sichtbar und lässt sich das Projekt
  öffnen sowie das Agent-Terminal im gewünschten Host nutzen?
