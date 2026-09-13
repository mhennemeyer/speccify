---
station: Backlog
created: 2026-09-13
needs_human: true
ready: false
open_question: null
parent: null
---
# Rückkanal: Spec-Stand und Jira-Updates aus Speccify (TBD)

## Why

Der PO soll in itsdcloud Entwicklungsstand, Entscheidungen und offene Punkte
einer Spec sehen, ohne das Board zu befragen — und zugeordnete Jira-Tickets
sollen, falls freigegeben, aus Speccify aktualisiert werden. Beides braucht
definierte Schreibwege (V1-03, Schritte 4–5).
[Integrationsplaybook](../../playbooks/itsdcloud-integration.md), Phase 5.

## What

Vorschlag: itsdcloud erhält ein dauerhaftes Wissensobjekt „Entwicklungsnotizen“
je Projekt (nicht die Chat-Zusammenfassung), mit Endpunkt `PUT
/api/projects/{id}/dev-notes/{spec_id}` (Spec-ID, Repo/Branch/Commit, Status,
überprüfte Ergebnisse, offene Punkte, Revision, Idempotency-Key). Speccify
schreibt bei Stationswechsel/`ready` über den Web-Board-Dienst oder die App,
nur mit Freigabe je Projekt. Jira: Stationswechsel → Status, `ready` →
Kommentar, mit Freigabe.

## Acceptance

- Wenn eine Spec `ready` wird, dann erscheint der Stand nach bestätigtem
  Schreiben in itsdcloud und überlebt eine erneute Chat-Extraktion; ein
  Retry erzeugt keine Dublette.

## Decisions

- D1, 2026-09-13: Idee ohne `order`; abhängig von 034/035 und der
  Jira-Entscheidung (036).

## Tasks

- [ ] itsdcloud-Spec für Entwicklungsnotizen (Endpunkt, Rechte, Idempotenz).
- [ ] Speccify-Schreibweg (Board-Dienst oder App) mit Freigabe je Projekt.
- [ ] Jira-Updates nach 036.

## Verification

Noch nichts geprüft.

## Questions

Keine.
