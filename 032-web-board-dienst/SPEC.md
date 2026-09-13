---
station: Doing
order: 13
created: 2026-09-13
needs_human: true
ready: false
open_question: null
parent: null
---
# Web-Board als Dienst: beliebig viele Repos lesen, zeigen, aktualisieren

## Why

Das statische Board aus [031](../031-team-board-im-web/SPEC.md) zeigt ein Repo
und lebt vom Deploy der Website. Ein Team will ein Board **pro Projekt,
Projektordner oder Projektgruppe** einfach selbst betreiben (etwa per Docker),
beliebig viele Repos anbinden, deren Specs lesen und darstellen, den Stand von
selbst aktuell halten und kleine Änderungen (Station, Tasks) direkt aus dem
Browser ins Register zurückschreiben. Nutzerauftrag 2026-09-13.

## What

Ein kleiner Dienst `speccify-board` (Python, FastAPI, im Workspace unter
`apps/board`), konfiguriert über eine YAML-Datei:

```yaml
title: Team Alpha
refresh_seconds: 60
repos:
  - name: app
    url: https://github.com/org/app.git      # Branch specs, shallow geklont
  - name: portal
    url: git@github.com:org/portal.git
    branch: specs
  - name: lokal
    path: /work/projekt                       # Ordner mit .agent/specs
```

Repos mit `url` werden mit ihrem Register-Branch (`specs`, Spec 028) in ein
Datenverzeichnis geklont und im Takt von `refresh_seconds` per `fetch` und
`reset --hard` aktualisiert; Repos mit `path` werden direkt gelesen (auch ein
Projektordner mit `.agent/specs`). Ein Eintrag `path` auf einen Ordner mit
mehreren Repos (Workspace) bindet alle Unterordner mit `.agent/specs` an.
Zugang zu privaten Repos über `${GIT_TOKEN}` in der URL oder gemountete
SSH-Schlüssel; nichts davon steht in der Konfiguration selbst.

Oberfläche: dieselbe Seite wie `speccify board` (Core `board.py`) mit Repo-
Kennung je Karte und Repo-Filter, Kennzahlen je Repo, `GET /` (alle),
`GET /r/<name>/` (ein Repo), `GET /api/board.json` (Daten), `POST /api/refresh`,
`GET /healthz`. Optionaler Zugangsschutz per `BOARD_PASSWORD` (HTTP Basic).

Aktualisieren aus dem Browser: Station wechseln und Tasks abhaken. Der Dienst
schreibt die Datei im Klon byte-stabil, hängt die History-Zeile an, committet
als konfigurierbarer Autor (`author: Speccify Board <board@…>`) und pusht in
den Register-Branch; scheitert der Push, holt er nach, rebased und versucht es
einmal erneut, sonst meldet er den Fehler. Lokale `path`-Repos werden direkt
geschrieben (die App-Watcher dort synchronisieren). Weitergehende Edits
(Text, Fragen, Übernehmen mit Besitzer) bleiben der App und dem Editor.

Docker: `apps/board/Dockerfile` und ein `docker-compose.yml`-Beispiel mit
Volume für Daten, Konfiguration und optionalem SSH-Schlüssel.

Nicht enthalten: Login je Person (nur ein gemeinsames Passwort), Echtzeit-Push
in den Browser (Seite lädt nach Aktionen neu; sonst Reload), Bearbeiten von
Spec-Text, Anlegen neuer Specs, Aggregation über mehrere Board-Instanzen.

## Acceptance

- Wenn die Konfiguration zwei Repos mit `url` und eines mit `path` nennt, dann
  zeigt `GET /` alle Specs mit Repo-Kennung, Repo-Filter und Kennzahlen je Repo;
  `GET /r/<name>/` nur das eine Repo.
- Wenn in einem angebundenen Repo ein Commit auf `specs` landet, dann zeigt das
  Board ihn spätestens nach `refresh_seconds` (oder sofort nach
  `POST /api/refresh`).
- Wenn im Browser eine Station gewechselt oder eine Task abgehakt wird, dann
  liegt die Änderung als Commit auf `specs` des Repos, die History hat eine
  Zeile mit Akteur „board“, und die App eines Teammitglieds sieht sie nach
  ihrem Sync.
- Wenn ein Push fehlschlägt, weil das Register inzwischen weiterging, dann
  wird nachgeholt und erneut gepusht; nichts geht verloren, kein Force-Push.
- Wenn ein Repo nicht erreichbar ist, dann zeigt das Board den Fehler je Repo
  und die anderen Repos weiter.
- Wenn `BOARD_PASSWORD` gesetzt ist, dann verlangen alle Seiten und die API
  HTTP Basic; ohne Variable ist das Board offen (für interne Netze).
- Wenn `docker compose up` mit der Beispielkonfiguration läuft, dann antwortet
  `http://localhost:8765/` mit dem Board.

## Decisions

- D1, 2026-09-13: Ein Dienst pro Board-Instanz mit YAML-Konfiguration; die
  Gruppe „welche Repos gehören zusammen“ ist die Konfiguration selbst.
- D2, 2026-09-13: Lesen über flache Klone des Register-Branches, nie über den
  Code-Branch; Schreiben nur Station und Tasks, mit derselben Byte-Stabilität
  und History wie die App. Alles andere bleibt in der App.
- D3, 2026-09-13: Rendering und Lesart bleiben im Core (`board.py`,
  `editable=True` schaltet Bedienelemente frei); der Dienst ist ein dünner
  Adapter wie CLI und MCP.
- D4, 2026-09-13: Kein Nutzerkonzept; Commits des Boards tragen einen
  konfigurierten Autor und den Akteur `board` in der History.

## Tasks

- [ ] Core: `repo` je Spec, Repo-Filter und -Kennzahlen, `editable`-Steuerung.
- [ ] `apps/board`: Konfiguration, Quellen (url/path/Workspace), Registry mit
      Auffrischung, FastAPI-Routen, Schreiben mit Commit/Push/Retry, Basic Auth.
- [ ] Tests mit Bare-Remotes: Klonen, Auffrischen, Schreiben, Push-Nachholen,
      Fehler je Repo, Auth.
- [ ] Dockerfile, compose-Beispiel, Beispielkonfiguration, README, Doku-Seite.
- [ ] Lokaler Lauf gegen das Speccify-Repo plus ein zweites Repo; Docker-Build.

## Verification

Noch nichts geprüft.

## Questions

Keine.
