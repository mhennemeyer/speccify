---
station: Backlog
order: 11
created: 2026-09-12
needs_human: true
ready: false
open_question: null
parent: null
---
# Teamsignale über Git: neu seit Sync, Fragen an Personen, optionaler Webhook

## Why

Ein Team braucht drei Signale: „etwas hat sich geändert“, „Frage an Dich“,
„jemand hat übernommen“. Alle drei sind im Register aus
[028](../028-spec-branch-als-register/SPEC.md) bereits Commits. Ein eigenes
Messaging-System würde einen Dienst, Auth und Offline-Sync verlangen; Git und
die vorhandenen Team-Chats decken den Bedarf für den Pilot ab (V1-09,
Abschnitt „Braucht es ein Messaging-System?“).

## What

Erstens „neu seit letztem Sync“: nach jedem Fetch markiert das Board Specs, die
sich durch fremde Commits geändert haben (Station, Tasks, Fragen, Besitzer),
mit Kurzfassung aus den Commit-Nachrichten; ein Klick räumt die Markierung.
Zweitens Fragen an Personen: `### Q1 · open · <ts> · an: <E-Mail>` adressiert
eine Frage; beim Adressaten hebt das Board sie hervor („1 Frage an Dich“),
`open_question` bleibt wie gehabt. Antworten laufen wie heute über `A1`.
Drittens ein ausgehender Webhook (Slack/Teams/Mattermost-kompatible JSON-
Nachricht) für `station_changed`, `ready`, neue Frage und Konflikt, konfiguriert
in `.agent/settings.json` ohne Secrets (URL kommt aus der Rechnerumgebung oder
den globalen Settings), standardmäßig aus.

Nicht enthalten: eingehende Nachrichten, Chat oder Kommentare in der App,
Push-Benachrichtigungen des Betriebssystems, Lesebestätigungen, ein eigener
Dienst. Ein Kommentarstrom je Spec (`comments.jsonl`, union-merged) ist als
möglicher zweiter Schnitt notiert, nicht Teil dieser Spec.

## Acceptance

- Wenn ein Fetch fremde Änderungen an einer Spec bringt, dann trägt die Karte
  eine Markierung mit Kurzfassung, bis sie bestätigt wird; eigene Änderungen
  markieren nicht.
- Wenn eine Frage an die eigene E-Mail adressiert ist, dann ist sie im Board
  hervorgehoben und in „Doing nach Person“ gezählt; nach der Antwort verschwindet
  die Hervorhebung.
- Wenn ein Webhook konfiguriert ist, dann löst jeder der vier Ereignistypen
  genau eine Nachricht aus, mit Spec-ID, Titel, Person und Link auf den Ordner;
  ohne Konfiguration passiert nichts und nichts fehlt lokal.
- Wenn das Remote nicht erreichbar ist, dann fehlen Markierungen, aber das
  Board arbeitet unverändert.

## Decisions

- D1, 2026-09-12: Kein eigener Nachrichtendienst; Git-Commits sind die
  Ereignisquelle, Webhook nur ausgehend und optional.
- D2, 2026-09-12: Adressierung über E-Mail der Git-Identität (029 D1).

## Tasks

- [ ] Vertrag: Markierungsregeln, Fragen-Adressierung, Webhook-Nutzlast.
- [ ] Native Befehle: Änderungsliste seit letztem gesehenen Commit je Spec;
      Webhook-Versand mit Fehleranzeige.
- [ ] Board: Markierung, Hinweis „Fragen an Dich“, Einstellungsseite Webhook.
- [ ] Tests mit Fixture-Remote und Mock; Hilfe und Stand-Playbook.

## Verification

Noch nichts geprüft; Entwurf, abhängig von 028 und 029.

## Questions

Keine blockierende Frage für den Entwurf.
