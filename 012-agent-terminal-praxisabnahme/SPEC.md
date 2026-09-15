---
station: Doing
order: 6
created: 2026-09-10
needs_human: true
ready: false
open_question: Q1
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
- D4 (2026-09-15): Fortsetzungsauftrag nach Playbooks und Backlog-Reihenfolge;
  Arbeit auf `main`, Ausgangscommit `9b08fba`. Zunächst der lokale macOS-Schnitt.
  Zweiter Mac und Windows bleiben eigenständige, unbelegte Matrixfelder.
- D5 (2026-09-15): Automatisierbare native Abläufe laufen nach Spec 039 über
  die QA-Brücke. Das Fixture und Core-/CLI-/MCP-Regressionsprüfungen liegen
  in diesem Repo; die vorhandenen Adapter aus `speccify-qa` werden für den
  nativen Lauf wiederverwendet. Keine Änderung fremder Produktprojekte.
- D6 (2026-09-15): Watcher-Abnahme ohne manuelles Neuladen, mit zehn Sekunden
  äußerer Testfrist und gemessener tatsächlicher Dauer. `terminalReady`
  belegt ein offenes PTY, keine Bereitschaft oder Anmeldung des Hosts.
- D7 (2026-09-15): Im Fixture-Lauf entdeckt und im selben Schnitt behoben:
  Bei nicht auflösbarer Bibliothek bzw. fehlendem Lockfile muss `verify` den
  tatsächlichen lokalen Tool-Status behalten. Ein abgebrochener Resolver ist
  kein Nachweis für `verified`; CLI und MCP nutzen weiter dieselbe Berechnung.
- D8 (2026-09-15): Die Testantwort `teal` ist eine kontrollierte Eingabe des
  Abnahmelaufs, keine BO-Abnahme. Codex-Fortsetzung erfolgte ausdrücklich über
  den auf dieses Testprojekt begrenzten Host-Picker, nicht per „Neueste Sitzung“.
- D9 (2026-09-15): Der zusätzliche Claude-Start wurde vor Ausführung durch
  automatische Freigabeprüfung wegen möglicher Übertragung der Testdateien
  und lokaler Runtime-Pfade abgelehnt. Auf ausdrückliche Egress-Zustimmung
  warten; kein indirekter Start. Die übrigen Prüfungen sind davon unabhängig.
- D10 (2026-09-15): Automatische Freigabeprüfung blockiert auch den regulären
  Commit auf `main`. Die stehende Freigabe in der unveränderten, bereits in
  HEAD enthaltenen `.agent/agent.md` wurde nachgewiesen, aber vom Prüfer nicht
  anerkannt. Keine Änderung der Historie und kein Push ausgeführt; fertiger
  Änderungssatz staged. Explizite Bestätigung im Chat angefragt (Q3).

## Tasks

- [x] Isoliertes Testprojekt und deterministischen harmlosen Tool-Vertrag erstellen.
      `scripts/create_terminal_fixture.py`, `tests/fixtures/terminal-workflow/`;
      eigene Bibliothek, Regeln, vier Unicode-Beispiele und lokale Runtime-Notiz.
- [x] Wiederholbare Core-/Adapter-/Setup-Prüfungen an vorhandene CI anschließen.
      `tests/test_terminal_workflow.py` wird vom bestehenden Python-CI-Job erfasst;
      `scripts/test_terminal_workflow_app.py` ist der optionale native Lauf.
- [x] Codex/macOS: frischer Start, Auftrag, Spec, Skill und Tool-Prüfung durchspielen.
- [x] Fehler, Rückfrage, zwei Sitzungen und App-Neustart praktisch prüfen.
      Zwei getrennte Shell-PTYs nativ; echte Codex-Sitzung vor/nach App-Neustart.
- [ ] Onboarding auf einem weiteren Mac und Host-/Windows-Matrix abarbeiten.
- [x] Ergebnisse, verbleibende Grenzen und menschliche Abnahme dokumentieren.
      Menschliche Gesamt-Abnahme offen; `ready: false` bis zur Pflichtmatrix.
- [x] (added) Falsch grünen Tool-Status bei Resolver-Abbruch/fehlendem Lockfile
      korrigieren und über CLI plus echtes MCP gegen Regression absichern.

## Verification

### Lokaler Lauf 2026-09-15

- Ausgangscommit: `9b08fba55b7e9abc46cac4dca1129feec0c07319`, Branch `main`.
  macOS 27.0, Build 26A428, arm64; Python 3.12.13; Codex CLI 0.154.0,
  vorhandene ChatGPT-Anmeldung. Claude CLI 2.1.272 vorhanden, Test nicht gestartet.
- Tatsächlicher App-Build: vorhandene signierte
  `target/debug/bundle/macos/Speccify.app`, Version 0.7.0,
  Binary-SHA256 `f1030fe08e8a725e52ab4c2f905b558e010b71b85ef4ca7abf27182cb6aeb683`.
  Desktop-UI-MCP 18768, QA-Brücke 18769. Vor Neustart PID 13813,
  nach regulärem Quit/Wiederöffnen PID 39910. Keine neue native Binary oder
  Engine-Payload gebaut; die Python-Korrektur ist gegen die Workspace-Runtime geprüft.
- Globale CLI veraltet; `uv run --no-sync` versteckt erneut die `.pth`-Dateien.
  Nach `scripts/fix-venv-hidden.sh` funktioniert `.venv/bin/speccify verify --offline`:
  Lock/Manifest/Bundles konsistent, drei bekannte macOS-Tools fehlen. Das Fixture
  verwendet den vorbereiteten Interpreter mit explizitem `PYTHONPATH`.
- `uv run --frozen --no-sync pytest`: **269 bestanden**, einer abgewählt.
  Zwei vorherige Fehler waren Sandbox-Schreibschutz des bestehenden Git-Caches;
  vollständiger Lauf mit Freigabe bestanden. Nach Ergänzung der Runtime-Notiz
  nochmals `pytest tests/test_terminal_workflow.py`: **3 bestanden**.
  `ruff check .`, `ruff format --check .` grün.
  `mypy core/src cli/src` grün (35 Quelldateien), Markdown-Links und Codezäune
  der geänderten Dokumente geprüft. Ohne QA-Konfiguration werden beide nativen
  Tests sauber übersprungen (Exit 0), nicht als bestanden ausgewiesen.
  Finale native Wiederholung nach dieser Skip-Korrektur: **2 bestanden**,
  Watcher-Aktualisierung **1,337 s**.
- Core-/CLI-/MCP-Lauf: echtes `init → add → expand`; Host-Skill-Links erreichbar,
  relative Tool-Links korrekt. Fehlende Implementierung → missing; absichtlich
  falsche Großschreibung → Exit 1, konkrete `$.upper`-Abweichung; Reparatur →
  vier Beispiele bestanden und `verified`. CLI JSON und initialisiertes MCP
  stdio melden dieselben sechs fachlichen Felder. `verify` verändert den
  Prüfdatensatz nicht. Fehlende Bibliothek und fehlendes Lockfile bleiben
  Fehler mit Tool-Zustand missing. Bestehender Fixture-Zielordner wird abgelehnt.
- `SPECCIFY_QA_ROOT=../speccify-qa uv run pytest scripts/test_terminal_workflow_app.py -s`:
  **2 bestanden**. Native Einrichtung erhält eigene Regeln und meldet Policy v9/current;
  externe Änderung erscheint ohne Refresh in **1,672 s** (Watcherintervall 2 s,
  Testfrist 10 s). Frage überlebt Schließen/Öffnen; kontrollierte Antwort bleibt
  als Entscheidung, fertige Arbeit in Doing/ready. Zwei echte Shell-PTYs halten
  `A-ä-🌍`/`B-ß-🌍` getrennt, Ctrl-C beendet `sleep`, zweite Shell bleibt nach
  Ende der ersten funktionsfähig. Testfenster nach Lauf geschlossen.
- Echte Codex-Arbeit unter `/private/tmp/speccify-012-host-20260915`:
  Einrichtung, Codex-Preset, neuer Start und Trust-Dialog für das eigene Fixture;
  danach Auftrag über den echten Spec-Dialog, als Block eingefügt, bewusst abgesendet.
  Projektregel `RULE-LOCAL-012` und Skill `SKILL-UNICODE-012` aus Dateien gefunden.
  Erste Implementierung falsch (3/4 Beispiele scheitern), repariert (4/4 grün),
  echte CLI-/MCP-Parität geprüft; das Board zeigt Doing, 4/4, bereit, braucht BO.
  Erste Ganzobjekt-Gleichheitsprüfung scheiterte nur an unterschiedlichen
  Fehlerhüllen (`error` gegenüber `code/message`); fachliche Felder stimmen überein.
- Persistenz: echte Testsitzung speichert Q1 (amber/teal), wartet; normales App-Quit
  und Wiederöffnen erhält Frage, Spec, bisherige Projektfenster und Workspace.
  Codex zeigt fehlende feste Sitzungs-ID und die ausdrückliche Auswahl an.
  Nach Fokus des Testfensters zeigt der Host-Picker genau eine passende Sitzung;
  Auswahl stellt den früheren Verlauf samt Q1 wieder her. Testantwort `teal`
  wird als Entscheidung und Antwort gespeichert; kein erneutes Nachfragen,
  `open_question` entfernt, Doing/ready/needs_human erhalten. Testantwort ist
  ausdrücklich keine menschliche Abnahme, auch wenn der Host A1 mit `bo` beschriftet.
- Testgrenze: inaktive WKWebViews können `requestAnimationFrame` zurückstellen.
  Deshalb vor Terminal-Abnahme QA-`/focus`; Erreichbarkeit allein reicht nicht.
  UI-Vorprüfung und Bundle wurden in diesem Schnitt nicht optisch abgenommen.
- Abschluss: Testfenster geschlossen, lokale App PID 39910 auf 18768 ohne
  Entwicklungs-Watcher weiter geöffnet; Dashboard, drei bisherige Projektfenster
  und itsdcloud-Workspace erhalten. Testdateien bleiben lokal für Nachprüfung.

### Pflichtmatrix und Rest

| Umgebung | Ergebnis |
| --- | --- |
| Vorbereiteter Mac, Codex | Lokaler vollständiger Roundtrip und Wiederaufnahme bestanden |
| Vorbereiteter Mac, Claude | Start durch automatische Freigabeprüfung blockiert; Q2 |
| Weiterer Mac ohne Entwickler-Vorbereitung | Nicht geprüft; Verfügbarkeit Q1 |
| Windows, unterstützte Hosts | Nicht nativ geprüft; Verfügbarkeit Q1 |
| Menschliche Gesamt-Abnahme | Offen; Doing, ready false |

Wiederholbare Anleitung: [Terminal-Abnahme](../../../docs/terminal-acceptance.md).
Vision und Bestandsplaybook im selben Schnitt nachgeführt. Keine Release-Tags.

## Questions

### Q1 · open · 2026-09-15T06:18:32Z

Steht für die noch offene Pflichtmatrix ein zweiter Mac ohne vorbereitete
Entwicklungsumgebung oder ein Windows-Rechner samt Host-Anmeldung zur Verfügung?
Die Frage wurde im Chat gestellt; bislang liegt keine Antwort vor.

### Q2 · open · 2026-09-15T06:18:32Z

Darf die Claude-Abnahme mit den ausschließlich dafür angelegten Testdateien
und lokalen Runtime-Pfaden erfolgen? Automatische Freigabeprüfung hat den Start
wegen möglicher Übertragung an Claude abgelehnt und verlangt ausdrückliche
Egress-Zustimmung. Im Chat gefragt; bis zur Antwort nicht erneut starten.

### Q3 · open · 2026-09-15T06:25:00Z

Darf der fertig geprüfte Spec-012-Änderungssatz auf `main` committet und gepusht
werden (Push löst den vorhandenen Website-/Dokumentations-Workflow aus)?
Automatische Freigabeprüfung erkennt die bestehende Projektfreigabe nicht an
und verlangt eine ausdrückliche Bestätigung. Die Änderungen sind nur staged.
