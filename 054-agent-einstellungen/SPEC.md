---
station: Doing
order: 54
created: 2026-09-16
needs_human: true
ready: true
parent: 051-terminal-findings-08
---
# Agent-Einstellungen mit verständlicher Hilfe

## Why

Die bisherigen Startkommandos reichen nicht, um Berechtigungen und Arbeitsweise
übersichtlich anzupassen. Häufige Windows-Rückfragen unterbrechen den Alltag.

## What

Strukturierte editierbare Codex-/Claude-Konfiguration, Erläuterungen und
offizielle Referenzen. Breite Einstellungen zugänglich machen, komplexe Werte
erhalten. Ein Profil für möglichst selbstständige Arbeit anbieten; Herkunft,
Gültigkeitsbereich und notwendiger Terminal-Neustart sichtbar.

## Acceptance

- Nutzer kann Einstellungen finden, verstehen, ändern, speichern und zurücknehmen.
- Bestehende/unbekannte Einstellungen bleiben erhalten, ungültige Eingaben
  überschreiben keine funktionierende Konfiguration.
- Das angebotene Autonomieprofil erklärt Sandbox, Netzwerk und Freigaben.
  Host-/Admin-Vorgaben und Versionsgrenzen werden nicht als übersteuerbar versprochen.
- Einstellungen wirken beim nächsten Agent-Start unter macOS/Windows/Linux.

## Decisions

1. 2026-09-16: Offizielle aktuelle Referenzen und installierte CLI prüfen.
   „Wie hier“ bedeutet möglichst wenige Rückfragen, keine pauschale Behauptung
   identischer Host-Funktionen zwischen verschiedenen CLI-Versionen.

## Tasks

- [x] Konfigurationsschema, Gültigkeitsbereich und verfügbare Hosts prüfen.
- [x] Sichere Persistenz und Übergabe an den Host.
- [x] Strukturierte UI, Hilfe, Auswahl und Autonomieprofil.
- [x] Roundtrip-/Start-/UI-Prüfung und Dokumentation.

## Verification

Acht native Tests grün: TOML-Kommentare, unbekannte Schlüssel, Regeln, Enum/Typ/Null, Legacy-Werte, stale-editor-Konflikt, Symlink-Erhalt und Profile. Browser-Suite grün: Suche/Hilfe, Entwurfsprofil, Speichern/Rücknahme, ungültige Eingaben, Konflikt und Hostwechsel ohne stillen Entwurfsverlust. Native JSON/TOML-Parse/Patch mit Teststrings grün; echter modaler Einstellungsdialog schreibfrei geöffnet/geschlossen. Codex 0.154.0 akzeptiert das angebotene Profil über `features list`; Claude 2.1.273 vorhanden, Auto-Verfügbarkeit laut Konto/Modell/Policy erklärt. Keine Benutzerdatei für Tests geändert. Schema-Snapshots mit Apache-2.0-Lizenz und Referenzen; Quelltext erlaubt zusätzliche Schlüssel. Kein Versprechen effektiver Sitzungseinstellungen oder vollständiger CLI-Semantikvalidierung.

## Questions

Keine.
