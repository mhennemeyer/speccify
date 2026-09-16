---
station: Doing
order: 45
needs_human: true
ready: false
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

- [ ] Gemeinsamen Quell-/Zielvertrag und Kollisionsdarstellung mit 046 festlegen.
- [ ] Workspace-Navigation, Listen, Filter und herkunftsgebundene Aktionen integrieren.
- [ ] Root-Katalog und gezielte Host-Anbindung mit Verfügbarkeitsstatus ergänzen.
- [ ] Gleichnamige Skills/MCPs, relative Tools, Ausfall und Entwurfserhalt prüfen.
- [ ] Doku und beide Produktplaybooks aktualisieren; realen Root-Roundtrip abnehmen lassen.

## Verification

Bestand: `WorkspaceShell.tsx` bindet Wissensbereiche je Worktree ein;
`WorkspaceBoardView` aggregiert Specs bereits. Es wurde kein neuer
Listen-/Host-Katalog implementiert oder als funktionsfähig abgenommen.

## Questions

Die konkrete Katalogdarstellung im jeweiligen Host wird beim Vertragsentwurf
gegen dessen verfügbare Schnittstellen geprüft; Anzeige ist kein Verfügbarkeitsnachweis.
