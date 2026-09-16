---
station: Doing
order: 44
needs_human: true
ready: true
---

# Root-Dateien und gewöhnliche Ordner im Workspace

## Why

Ein Parent-Ordner mit Repositories enthält häufig auch normale Arbeitsordner
und lose Dateien. Aktuell verschwinden diese aus den erreichbaren Dateizielen,
wenn die Projekterkennung Unterprojekte findet. Beispiel: ein normaler
Ressourcenordner neben mehreren Code-Repos.

## What

Jeder geöffnete Workspace erhält einen Dateikontext für seinen Root, auch
ohne Git- oder Projektmarker. Der Dateibaum zeigt gewöhnliche Ordner und lose
Dateien mit den bestehenden Dateioperationen. Git bleibt pro tatsächlichem
Repository; keine automatische Git-/Workflow-/Register-Initialisierung.
Die automatische Projekt-Erkennungstiefe bleibt standardmäßig 1 und unabhängig
von der Tiefe, bis zu der man einen Dateibaum manuell aufklappen kann.

Das gemeinsame Wissensmodell ist Gegenstand von 045; Registerbindungen von 046.

## Acceptance

- Bei `workspace/` mit `repo-a/.git`, `repo-b/.git`, `Resourcen/nested/info.md`
  und `notes.md` zeigt Dateien die beiden gewöhnlichen Root-Inhalte. Beide
  Dateien lassen sich bei Erkennungstiefe 1 öffnen und bearbeiten.
- Ein tiefer verschachteltes Repo wird nicht allein durch Aufklappen des Baums
  als neues Projekt aufgenommen. Eine explizite Tiefenänderung nutzt den
  vorhandenen Erkennungsvertrag aus 040.
- Dateien/Git zeigen ihr eindeutiges Ziel. Änderungen unter `Resourcen`
  verändern keinen fremden Git-Index; Git-Aktionen am Root ohne Git werden
  nicht angeboten. Ein Root mit Git benutzt dessen tatsächlichen Repo-Kontext.
- Repo-Unterordner sind im Root-Dateibaum erreichbar; die getrennten Git-Ziele
  bleiben eindeutig. Mehrere Ansichten derselben Datei teilen den Entwurf
  oder erkennen einen Schreibkonflikt, statt sich still zu überschreiben.
- Ein leerer Root, ein reiner Dateiordner, ein Root mit eigenem Repo und ein
  gemischter Workspace funktionieren nach Aktualisieren und Wiederöffnen.
- Bestehende Datei-Ausschlüsse, Symlink-/Pfadgrenzen und Lesefehler bleiben
  wirksam. Ein unlesbarer Unterordner verdeckt keine anderen Root-Einträge.

## Decisions

1. 2026-09-16: Refinement aus Nutzerauftrag, noch nicht implementiert.
2. 2026-09-16: Normale Ordner sind zuerst Dateien, nicht automatisch Projekte
   oder eigene Register. Der Root-Dateikontext darf unabhängig von der
   Erkennung existieren; keine Vertiefung der Projektsuche als Umgehung.
3. 2026-09-16: Vorhandene native Dateioperationen und deren Schutzgrenzen
   wiederverwenden. Root- und Unterprojektpfad bleiben beim UI-Wechsel stabil.
4. 2026-09-16: Nutzerauftrag „leg los“ startet die Umsetzung. Root-Dateiziel
   separat von der erkannten Projektliste halten. Speichern prüft den zuletzt
   gelesenen Inhalt, damit Root-/Unterprojekteditoren einander nicht überschreiben.

## Tasks

- [x] Workspace-Modell und Navigation um den dauerhaften Root-Dateikontext ergänzen.
- [x] Öffnen/Bearbeiten/Entwürfe sowie Git-Zielbindung für gemischte Roots integrieren.
- [x] Akzeptanzfälle mit isolierten Fixtures nativ und in der Oberfläche prüfen.
- [x] Workspace-Doku, Produktvision und Bestandsbuch nachführen; zur lokalen Abnahme bereitstellen.

## Verification

Refinement: `apps/desktop/src-tauri/src/workspace_cmd.rs`, Funktion `scan`:
Aufnahme nur bei Git/Markern; `found.is_empty()` schaltet den Root-Fallback.
Struktureller Nutzerordner-Befund bestätigt normale Root-Inhalte neben Repos.

Umsetzung am 2026-09-16:

- `cargo test -p speccify-desktop`: 119 bestanden, drei bestehende Umgebungstests
  ausgelassen. Root-Ziel unabhängig von Erkennung, normale/tiefe Dateien und
  veralteter Schreibversuch aus zweitem Projektkontext nativ geprüft.
- `cargo fmt --check`, Desktop-Typecheck, `git diff --check`: grün.
- `test_workspace_root.mjs`: normale Ordner und Root-Datei, manuelles tiefes
  Aufklappen, Git-Grenze, Konflikt mit zweitem Editor, Entwürfe nach Refresh
  und Wiederöffnen grün. Konflikt lässt den Entwurf weiter bearbeiten.
- `test_workspace_shell.mjs`: bisherige Datei-/Git-Ziele, gemeinsames Terminal,
  Gruppenwechsel, Board und Ausfall eines Unterprojekts weiterhin grün.
- Lokaler signierter App-Build erfolgreich; `codesign --verify --deep --strict`
  grün. Native QA-Prüfung mit zwei temporären Repos und Resourcen/nested/info.md:
  Root-Dateibaum geöffnet, Inhalt sichtbar, Speichern korrekt, veraltete Änderung
  abgewiesen, kein Git/Workflow am Root angelegt. Test-Workspace entfernt.
- App-PID 76213, alle vier ursprünglichen Fenster wiederhergestellt, keine
  laufenden Terminals beendet. Kein Kundenrepo geändert. Menschliche Abnahme offen.
- Website-Hilfe aktualisiert; Marketing-Build mit 101 Seiten und Doku-Sync grün.

Umsetzung zur Abnahme geparkt; weitere autorisierte Specs können bearbeitet werden.

## Questions

Keine für den beschriebenen Umsetzungsschnitt.
