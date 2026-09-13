---
station: Backlog
created: 2026-09-13
needs_human: true
ready: false
open_question: Q1
parent: null
---
# Jira-Zuordnung je Spec (TBD)

## Why

Der PO will zu einer Spec das zugehörige Jira-Ticket sehen (Link) und
umgekehrt; später sollen zugeordnete Tickets aus Speccify aktualisiert
werden. Jira-Integration ist noch nicht entschieden (Produkt, Zugang, Pflege).
[Integrationsplaybook](../../playbooks/itsdcloud-integration.md), Phase 4.

## What

Vorschlag: Front Matter `jira: KEY-123` (optional `jira_url` je Projekt in
den Settings, sonst aus einer konfigurierten Basis-URL). Anzeige als Link in
der App (Karte, Inspektor), im statischen Board, im Web-Board und in
`list_specs` des Board-MCP; Filter „mit Jira“. Pflege durch die Person, die
die Spec anlegt oder übernimmt; die App bietet ein Feld im Editor.

Nicht enthalten: Schreiben nach Jira (037), automatische Zuordnung, Import
von Tickets als Specs.

## Acceptance

- Wenn `jira:` gesetzt ist, dann zeigen App, Board, Web-Board und MCP den
  Schlüssel als Link; ohne Feld ändert sich nichts.

## Decisions

- D1, 2026-09-13: Idee ohne `order`, bis Jira-Produkt und Zugang entschieden
  sind (BO).

## Tasks

- [ ] Entscheidung: Jira Cloud/Server, Zugang (itsdcloud-Provider wie Confluence?), Basis-URL.
- [ ] Feld und Anzeige in App, Board, Web-Board, MCP.

## Verification

Noch nichts geprüft.

## Questions

### Q1 · open · 2026-09-13T08:00:00Z

Welches Jira (Cloud oder Server), welcher Zugang (persönlicher Token, itsdcloud-Provider) und wer pflegt die Zuordnung?
