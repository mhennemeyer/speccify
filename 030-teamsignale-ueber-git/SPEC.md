---
station: Doing
order: 11
created: 2026-09-12
needs_human: true
ready: true
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
- D3, 2026-09-12: Webhook nur für Ereignisse, die auf diesem Rechner entstehen
  (im Register: uncommittete Dateien der Spec zum Zeitpunkt der Erkennung),
  damit nicht jedes Teammitglied dieselbe Nachricht nach dem Sync erneut
  sendet. Ereignisse werden im Watcher aus dem Board-Diff abgeleitet, nicht
  aus den App-Aktionen — so zählen auch Agentenänderungen.
- D4, 2026-09-12: „gesehen“-Merker je Spec im lokalen UI-Speicher; ohne Merker
  gelten fremde Commits der letzten sieben Tage als neu.

## Tasks

- [x] Vertrag: Markierungsregeln, Fragen-Adressierung, Webhook-Nutzlast.
      `docs/specs-register.md` Abschnitt „Teamsignale“; Policy v8 (`· an: <email>`).
- [x] Native Befehle: Änderungsliste seit letztem gesehenen Commit je Spec;
      Webhook-Versand mit Fehleranzeige.
      `team_signals.rs`: `project_register_changes(since)`, `project_webhook_test`,
      Board-Diff + `locally_originated` im Watcher, Konflikt-Flanke aus dem
      Register-Sync, Ereignis `webhook-error`; `webhook_url` in den App-Settings.
- [x] Board: Markierung, Hinweis „Fragen an Dich“, Einstellungsseite Webhook.
      Chips „neu · n von Person“ mit Bestätigen, „Frage an Dich“ auf Karte und
      als Zähler, *braucht mich* berücksichtigt es; Projekt-Zahnrad → Teamsignale
      (Schalter, Testnachricht), Dashboard-Settings → Webhook-URL.
- [x] Tests mit Fixture-Remote und Mock; Hilfe und Stand-Playbook.

## Verification

2026-09-12:

- `cargo test -p speccify-desktop`: 108 bestanden, 3 ignoriert. Neu: Board-Diff
  (Stationswechsel, `ready`-Flanke, neue Frage, keine Meldung für neue Specs
  oder Unverändertes), Ereignistext und Webhook-Konfiguration (Default alle vier
  Ereignisse, `events` aus `.agent/settings.json`), fremde Register-Commits je
  Spec mit zwei Klonen (B committet als „ben“, A sieht `001-x`/`002-y` mit Autor
  und Betreff; eigene Commits zählen nicht; nach dem Sync nichts Uncommittetes →
  nicht lokal entstanden). `cargo fmt --check`, `pnpm typecheck` grün.
- Browser-Suite `test_team_signals` (Mock `?changes=1`, `?question=me|other`):
  Markierung „neu · 2 von Ben Kollege“ mit Commit-Betreffs, Klick bestätigt und
  überlebt Reload, ohne Merker erneut markiert; „Frage an Dich“ nur beim
  Adressaten, Zähler im Kopf, *braucht mich* filtert; Webhook-Schalter im
  Projekt-Zahnrad ruft `project_settings_set`, Testnachricht ruft
  `project_webhook_test`. Dazu `spec_owner`, `spec_register`, `workflow_ui`,
  `spec_navigation`, `ui_colors`, `action_output`, `workspace_layout` grün.
- Nicht geprüft: echter Webhook-Empfänger (Slack/Teams), Klick-Durchlauf in der
  App, zwei Rechner. Deshalb `ready`.

## Questions

Keine blockierende Frage für den Entwurf.
