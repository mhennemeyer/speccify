---
station: Backlog
order: 6
created: 2026-09-10
needs_human: true
ready: false
open_question: null
parent: null
---
# Vollständige Arbeit im Agent-Terminal praktisch nachweisen

## Why

Grüne Komponenten-Tests belegen noch nicht, dass ein frisch gestarteter Agent
in Speccify den ganzen Arbeitsablauf bewältigt. Es braucht einen reproduzierbaren
Nachweis ohne Vorwissen aus einer alten Unterhaltung oder persönliche Pfade.

## What

Ein kleines entbehrliches Testprojekt mit einer Spec, einem lokalen Skill und
einem ungefährlichen Tool-Vertrag. Durchlauf in der echten App vom Einrichten
über einen Auftrag bis zu Verifikation, Rückfrage, Wiederaufnahme und Abnahme.
Automatisierbare Prüfungen ergänzen die CI; echte Host-/GUI-Prüfungen bleiben
als solche gekennzeichnet. Durchführung nach 007–011.

Das ist ein kleiner Vorlauf zu M2 aus Spec 001. Der Neubau eines alten Produkts
und die drei macOS-Bibliotheks-Tools bleiben dort. Keine Release-Veröffentlichung
und keine Änderung fremder Projekte als Testnebenwirkung.

## Acceptance

- Wenn ein frisches Testprojekt geöffnet wird, kann eine neue Codex-Sitzung
  allein aus dessen Dateien Regeln, Spec und Skill finden. Die benötigte
  CLI oder MCP-Verbindung ist tatsächlich erreichbar.
- Wenn der Umsetzungsauftrag gegeben wird, entstehen Implementierung und
  fortgeschriebene Spec im richtigen Projekt; das Board zeigt die Änderungen
  innerhalb des vorgesehenen Watcher-Intervalls zuzüglich Verarbeitung an.
- Wenn das Beispiel-Tool absichtlich ein falsches Ergebnis liefert, schlägt
  `tool check` fehl. Nach Korrektur wird es auf der getesteten Plattform
  nachweislich geprüft; CLI-JSON und MCP berichten konsistent.
- Wenn eine Rückfrage offen bleibt, bleibt sie nach Schließen/Öffnen lesbar.
  Eine Antwort wird als Entscheidung verarbeitet und dieselbe Frage nicht
  unbegründet wiederholt.
- Wenn die App neu startet, wird die beabsichtigte Sitzung fortgesetzt oder
  die fehlende Zuordnung kenntlich gemacht. Bereits gespeicherte Spec-Arbeit
  und Entscheidungen bleiben erhalten.
- Wenn menschliche Abnahme erforderlich ist, bleibt die fertige Arbeit
  `Doing` mit `ready: true`, bis sie abgenommen wird.
- Wenn die Ergebnisse dokumentiert werden, sind App-/Host-Version,
  Betriebssystem, Prüfdatum und tatsächlich geprüfter Umfang angegeben.
  Nicht ausgeführte Plattformen bleiben ausdrücklich offen.

## Decisions

- D1 (2026-09-10): Erste Pflichtabnahme: Codex auf macOS im echten
  Speccify-Projektfenster. Ein weiterer Mac ohne Entwickler-Vorbereitung
  prüft anschließend das Onboarding.
- D2 (2026-09-10): Claude auf macOS und die unterstützten Windows-Hosts
  erhalten dieselben Kernfälle; Ergebnisse separat führen. Die vollständige
  Plattformabnahme bleibt offen, solange ein erforderliches System fehlt.
- D3 (2026-09-10): Host-Aufrufe können laufende Authentifizierung benötigen.
  Fehlende Zugangsdaten werden als konkrete Voraussetzung dokumentiert;
  ein Mock ersetzt diesen Nachweis nicht.

## Tasks

- [ ] Isoliertes Testprojekt und deterministischen harmlosen Tool-Vertrag erstellen.
- [ ] Wiederholbare Core-/Adapter-/Setup-Prüfungen an vorhandene CI anschließen.
- [ ] Codex/macOS: frischer Start, Auftrag, Spec, Skill und Tool-Prüfung durchspielen.
- [ ] Fehler, Rückfrage, zwei Sitzungen und App-Neustart praktisch prüfen.
- [ ] Onboarding auf einem weiteren Mac und Host-/Windows-Matrix abarbeiten.
- [ ] Ergebnisse, verbleibende Grenzen und menschliche Abnahme dokumentieren.

## Verification

Noch nicht durchgeführt. Ausgangsbasis: 216 Python- und 55 Desktop-Rust-Tests
grün, Typecheck grün; siehe [006](../006-bestandsaufnahme-agent-terminal/SPEC.md).
Das sind keine Ergebnisse der hier beschriebenen Praxisabnahme.

## Questions

Vor dem plattformübergreifenden Abnahmelauf verfügbare Testgeräte und
Host-Anmeldungen feststellen. Das blockiert nicht die vorherigen
Implementierungsspecs.
