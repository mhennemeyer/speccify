---
station: Backlog
order: 3
created: 2026-09-10
needs_human: true
ready: false
open_question: null
parent: null
---
# Terminal-Ausgabe und Fortsetzen einer Sitzung verlässlich machen

## Why

Beim Arbeiten an Speccify können Rust-Rebuilds die App neu starten. Die
Fortsetzung soll die beabsichtigte Sitzung öffnen. Frühe Ausgabe und über
Byteblöcke geteilte Zeichen dürfen dabei nicht verloren gehen.

## What

Terminal-Lebenszyklus und Fortsetzung als überprüfbarer Vertrag für Codex und
Claude: Host, Projekt, bekannte Sitzungsidentität, Start-/Endzustand und
Fehler. Bestehende Host-Protokolle weiterverwenden, keine eigene Kopie des
Chatverlaufs führen. Unbekannte freie Kommandos bleiben explizit unterstützt,
aber ohne erfundene Resume-Garantie. Baut auf der Startdiagnose aus 007 auf.

## Acceptance

- Wenn direkt nach PTY-Start Ausgabe entsteht, kommt sie vollständig im
  Terminal an, auch bevor die Startantwort an das Frontend zurückkehrt.
- Wenn UTF-8-Zeichen auf mehrere Lesevorgänge verteilt sind, erscheinen sie
  unverändert. Ein unvollständiges letztes Zeichen wird definiert behandelt.
- Wenn zwei Sitzungen im selben Projekt existieren, öffnet Fortsetzen die
  zugeordnete Sitzung. Ist sie unbekannt oder verschwunden, wird dies sichtbar
  und die Auswahl erfolgt ausdrücklich; es gibt keine unbemerkte Ersetzung.
- Wenn Host-Kommando oder Optionen geändert werden, wird kein ungültiger
  Resume-Aufruf durch bloßes Anhängen gebaut; freie Kommandos bleiben erhalten.
- Wenn der Start scheitert, meldet die UI einen Fehler statt bereits
  „fortgesetzt“. Terminal-Ausgabe allein gilt nicht als erfolgreicher Auftrag.
- Wenn neu gestartet oder beendet wird, bleiben keine verwaisten Listener
  oder durch diesen Terminal-Lebenszyklus verursachten Prozesse zurück.

## Decisions

- D1 (2026-09-10): Unterstützte Resume-Syntax und verfügbare Sitzungsmetadaten
  an den installierten Host-Versionen verifizieren.
- D2 (2026-09-10): Falls eine Host-Version keine belastbare Identifikation
  erlaubt, ist sichtbare Auswahl der Fallback; `--last` bleibt eine kenntliche
  Komfortfunktion und wird nicht als exakte Wiederherstellung bezeichnet.
- D3 (2026-09-10): Rust-Änderungen bündeln und den möglichen Dev-Neustart ankündigen.

## Tasks

- [ ] Start-/Ausgabe-/Ende-Protokoll einschließlich Listener-Reihenfolge festlegen.
- [ ] Inkrementelle UTF-8-Verarbeitung und frühe Ausgabe absichern.
- [ ] Hostbezogene Start-/Resume-Aufrufe und Sitzungszuordnung implementieren.
- [ ] Fehler, unbekannte Sitzung und freie Kommandos in der UI abbilden.
- [ ] Neustart, zwei Sitzungen, Ctrl-C und Prozessende in der echten App prüfen.

## Verification

F6–F7 in [006](../006-bestandsaufnahme-agent-terminal/SPEC.md).
Der vorhandene PTY-Test besteht; er prüft nicht die Tauri-Eventzustellung oder
Codex-/Claude-Resume. Umsetzung und echte Host-Fortsetzung noch nicht geprüft.

## Questions

Keine blockierende Frage für den Entwurf; technische Host-Grenzen bei
Umsetzung dokumentieren.
