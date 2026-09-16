---
station: Doing
order: 51
created: 2026-09-16
needs_human: true
ready: false
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

- [ ] 052 Terminaldarstellung.
- [ ] 053 Rückfragen und Systemmeldungen.
- [ ] 054 Editierbare Agent-Einstellungen und Hilfe.
- [ ] 055 Enter-Recherche.
- [ ] Zusammenhängende Prüfung, Playbooks/Doku und lokale App aktualisieren.

## Verification

Ausgangsstand 0.8.1: Terminalfarbe fest #0f172a, Schrift 12 px; PTY-Schreiben
kann Steuerzeichen übertragen, normale Übergabe nutzt ausschließlich Paste.

## Questions

Keine.
