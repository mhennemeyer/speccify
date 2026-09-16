---
station: Doing
order: 45
needs_human: true
ready: true
---

# Gemeinsames Board und Wissenslisten im Workspace

## Why

Der Mensch und der vom Root gestartete Agent arbeiten am gesamten Workspace.
Für Specs, Skills, Tools, MCPs und Playbooks behindert eine strikt nach Projekt
getrennte Navigation diese Arbeit. Herkunft ist zur Orientierung und für
korrekte Aktionen wichtig, muss aber keinen Bereichswechsel erzwingen.

## What

Specs standardmäßig auf dem bestehenden gemeinsamen Board zeigen. Für Skills,
Tools, MCPs und Playbooks jeweils eine gemeinsame Liste mit Suche, Herkunft und
optionalem Quellfilter anbieten. Root und erkannte Projekt-/Wissensordner im
konfigurierten Erkennungsbereich berücksichtigen, einschließlich Quellen ohne
Git. Dateien und Git bleiben nach konkretem Ziel getrennt.

Dem Root-Agenten einen auflösbaren Katalog mit kanonischen Quellpfaden und
Verfügbarkeitsstatus bereitstellen. Bestehende Core-/Host-/MCP-Verträge
weiterverwenden; keine Dateien verschieben, kein automatisches Expand aller
Skills und keine stille Zusammenführung von Zugangsdaten oder Allowlists.

Registeridentität und Team-Synchronisierung werden in 046 vertieft; Drafts in
047. Beide Zustände müssen in der Liste darstellbar sein.

## Acceptance

- Ein Fixture mit Root-Wissen sowie zwei Unterprojekten zeigt alle Specs auf
  einem Board und alle Skills/Tools/MCPs/Playbooks jeweils in einer Liste.
  Der Default benötigt keinen Projektwechsel; ein Filter begrenzt nur die Ansicht.
- Jeder Eintrag zeigt eine unterscheidbare Herkunft (Root bzw. relativer
  Ordner/Projekt). Zwei gleichnamige Quellen oder Skills bleiben auswählbar.
  Namensgleichheit führt weder zum Überschreiben noch zur stillen Priorisierung.
- Auswahl, Editor, Anlegen, Löschen, Expand und Übergabe behalten Quelle und
  Ziel auch nach Filtern, Aktualisieren oder Projektwechsel. Ein neues Element
  benötigt einen eindeutigen Speicherort; kein Schreiben ins zufällig aktive Repo.
- Ein Root-Agent kann einen Skill aus Unterprojekt A gezielt lesen und ein
  Tool von B mit dessen korrekten relativen Abhängigkeiten verwenden. Der
  Ausführungsauftrag benennt Quelle, Ziel und cwd; das Terminal bleibt am Root.
  Projektregeln und Host-Berechtigungen gelten weiterhin.
- MCP-Definitionen mit gleichem Namen, unterschiedlichen Befehlen/Ports oder
  Auth-Kontexten werden unterscheidbar aufgelöst. Eine sichtbare Definition
  erscheint erst nach erfolgreicher Host-Anbindung als nutzbar; keine Tokens
  im Katalog, keine neu gestarteten Server allein durch Listenanzeige.
- Entfernte oder unlesbare Quellen zeigen einen Zustand und bieten keine
  veraltete Schreib-/Ausführungsaktion. Andere Quellen bleiben nutzbar.
- Editorentwürfe, Quellfilter und Herkunft bleiben nach Wiederöffnen konsistent.
  Draft-Playbooks werden als unverbindliche Inhalte behandelt (047).

## Decisions

1. 2026-09-16: Refinement aus Nutzerauftrag; pro Bereich eine Liste, kein
   gemeinsamer Mischkatalog mit Specs, Skills und Git-Einträgen in einer Tabelle.
2. 2026-09-16: Das gemeinsame Board aus 026 wird weiterverwendet. Die
   Quellkennzeichnung muss im normalen Nutzungspfad sichtbar sein.
3. 2026-09-16: Root-cwd allein garantiert keine automatische Skill-/MCP-Erkennung
   durch Codex oder Claude. Host-Verfügbarkeit ausdrücklich integrieren und
   testen; unbekannte Host-Konfiguration nicht ungefragt umschreiben.
4. 2026-09-16: Reihenfolge als Vorschlag: Root-Dateikontext 044, Listen/Identität,
   Host-Katalog. Gemeinsame Quell-IDs mit 046 abstimmen, kein paralleles Modell.
5. 2026-09-16: Umsetzung nach geprüften 044/047/046. Katalogeinträge verwenden
   Workspace-/Checkout-IDs und kanonische Quellpfade. Gemeinsame Listen steuern
   bestehende quellgebundene Details. MCPs werden über Quelle, Host und Namen
   referenziert; keine Zugangsdaten im Katalog und keine automatische Host-
   Installation. Gezielte Anbindung erfolgt als expliziter Auftrag an den Host;
   eine gelesene Konfiguration ist kein Nachweis eines erfolgreichen Handshakes.

## Tasks

- [x] Gemeinsamen Quell-/Zielvertrag und Kollisionsdarstellung mit 046 festlegen.
- [x] Workspace-Navigation, Listen, Filter und herkunftsgebundene Aktionen integrieren.
- [x] Root-Katalog und gezielte Host-Anbindung mit Verfügbarkeitsstatus ergänzen.
- [x] Gleichnamige Skills/MCPs, relative Tools, Ausfall und Entwurfserhalt prüfen.
- [x] Doku und beide Produktplaybooks aktualisieren; realen Root-Roundtrip durchführen und zur Abnahme bereitstellen.

## Verification

Umgesetzt und geprüft am 2026-09-16:

- Nativer Katalog über vorhandene Projektleser, inklusive Root und Wissensordnern
  ohne Git. IDs enthalten Quelle und Dateipfad bzw. Host/MCP-Name. Geheimnisse,
  Befehlsargumente und URLs aus MCP-Konfigurationen fehlen im Katalog.
- Gemeinsame Listen mit Suche, Quellfilter, Herkunft und Playbook-Status. Import,
  Neuanlage und Anbindungsauftrag haben explizite Ziele. Entfernte Quellen
  sperren veraltete Aktionen. Ein gefundener Editorfehler beim Wiederwählen
  derselben Datei wurde behoben; laufender Editor/Entwurf bleiben erhalten.
- Rust: 124 Tests bestanden, 3 bestehende umgebungsabhängige Tests ignoriert.
  Katalogtest mit drei Quellen, gleichnamigen Skills/Tools/MCPs, Drafts,
  ausgeschlossener Credential-Ausgabe und verschwundener Quelle grün.
- Typecheck und Format/Diff-Prüfung grün. Browser: gemeinsame Wissenslisten,
  Herkunft bei Übergabe, Importziel, Playbook-Neuanlage, Entwurfserhalt,
  Quellausfall und Filter nach Reload. Bestehende Workspace-/Root-/Register-
  sowie Handover-/Draft-Suites grün.
- Nativer Wegwerf-Workspace mit Root/api/web: gemeinsame Liste und Auswahl
  geprüft. Tatsächlicher Codex-Lauf vom Root mit dem nativen Kontext: Skill aus
  api vollständig gelesen; Tool aus web mit relativem Input im web-cwd
  ausgeführt; ausdrücklich als qa_web konfigurierter Test-MCP per Handshake/
  Tool-Aufruf genutzt. Root-cwd erhalten, alle Quelldateien byte-identisch.
  Keine Änderung globaler Host-Konfiguration. Temporärer Workspace entfernt,
  ursprüngliche vier Fenster erhalten.
- Lokaler App-Build und Signaturprüfung grün, App PID 24629 offen. Website:
  101 Seiten, Doku-Sync erfolgreich. Keine Veröffentlichung eines Release-Tags.

MCP-Status im Katalog bleibt bewusst Konfigurationsstatus. Eine tatsächliche
Root-Verbindung bestätigt der jeweilige Host; die App übernimmt keinen
Handshake-Erfolg aus einem fremden Prozess als Nutzbarkeitsnachweis. Anbindung
erfolgt gezielt über einen prüfbaren Auftrag, nicht durch automatisches Mergen
von Konfiguration oder Zugangsdaten. Offizieller Codex-Vertrag für Projekt-
Konfiguration und stdio-cwd geprüft:
[MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
Menschliche Gesamt- und Windows-Abnahme bleiben offen; daher Doing/ready.

## Questions

Keine Implementierungsfrage offen. Gesamtpaket zur menschlichen Abnahme bereit.
