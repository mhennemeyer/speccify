---
station: Doing
order: 51
created: 2026-09-16
needs_human: true
ready: true
---
# Terminal und Agent-Bedienung für 0.8.x

## Why

Vor der Integrationsarbeit für 0.9.0 stören unleserliche Terminaldarstellung,
übersehene Rückfragen und schwer zugängliche Agent-Einstellungen den Alltag.

## What

Nutzer-Findings in einzeln prüfbaren Teil-Specs 052–055 umsetzen bzw. recherchieren.
Kein neues Release ohne gesonderten Zuruf; itsdcloud/0.9.0 bleibt geparkt.

## Acceptance

- Terminal folgt Hell/Dunkel und hat eine einstellbare Schriftgröße.
- Rückfragen/Berechtigungsdialoge werden sichtbar, auch bei verborgenem Terminal.
- Codex/Claude-Einstellungen sind strukturiert editierbar und erklärt; ein
  angebotenes Profil reduziert Rückfragen mit sichtbaren Berechtigungsgrenzen.
- Enter-Zustellung ist technisch und praktisch geprüft und dokumentiert.

## Decisions

1. 2026-09-16: Nutzer priorisiert diese Findings für 0.8.x vor 0.9.0.
2. 2026-09-16: 052 Darstellung, 053 Aufmerksamkeit, 054 Agent-Konfiguration,
   055 Enter-Recherche. Nur eine Teil-Spec gleichzeitig aktiv bearbeiten.
3. 2026-09-16: Bestehende Host-Konfiguration nicht still überschreiben; keine
   automatische Antwort auf eine Berechtigungsfrage aufgrund einer Texterkennung.

## Tasks

- [x] 052 Terminaldarstellung.
- [x] 053 Rückfragen und Systemmeldungen.
- [x] 054 Editierbare Agent-Einstellungen und Hilfe.
- [x] 055 Enter-Recherche.
- [x] Zusammenhängende Prüfung, Playbooks/Doku und lokale App aktualisieren.

## Verification

Abgeschlossen auf main, noch unveröffentlicht: 134 Rust-Tests bestanden (3 bestehende ignoriert), vollständige Python-Suite grün, TypeScript und Ruff/Format grün. Browser: Terminaldarstellung/-hinweise, Agent-Einstellungen, bestehende Auftragsübergabe und Sitzungswahl grün. Native gebündelte App: echte PTYs, UTF-8, Theme/Schrift ohne Prozessverlust, zwei Fenster, Popup, Paste ohne Enter, explizites CR, Ctrl-C, Exit/Neustart grün. Einstellungsdialog nativ geöffnet; macOS-Testnotification ohne API-Fehler. Developer-ID-Signatur inklusive Sidecars gültig. Vier bestehende Fenster nach Neustart wiederhergestellt. Lokale App bleibt offen; keine echte Host-Konfiguration für Tests verändert. Doku/Playbooks aktualisiert. Windows-/Linux-Systemzustellung und menschliche Sichtabnahme bleiben offen; kein neuer Tag.

## Questions

Keine.
