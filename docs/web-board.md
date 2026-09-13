# Das Web-Board: ein Dienst für beliebig viele Repos

Spec 032. Ein Team betreibt pro Projekt, Projektordner oder Projektgruppe ein
Web-Board, das die Spec-Register mehrerer Repositories liest, anzeigt, von
selbst aktuell hält und kleine Änderungen (Station, Tasks) zurückschreibt.
Grundlage ist das gemeinsame Register aus `docs/specs-register.md`: der Branch
`specs` jedes Repos ist die geteilte Wahrheit; das Board ist ein Leser und
ein vorsichtiger Schreiber davon, kein zweiter Speicher.

## Starten

```bash
# aus dem Speccify-Checkout
uv run speccify-board --config board.yaml --data ./board-data --port 8765

# als Container (Beispiel-Compose liegt in apps/board/)
cd apps/board && cp board.example.yaml board.yaml && docker compose up -d
```

Umgebungsvariablen: `BOARD_CONFIG`, `BOARD_DATA`, `BOARD_HOST`, `BOARD_PORT`,
`BOARD_PASSWORD` (HTTP Basic, Nutzername beliebig), `GIT_TOKEN` (für
`${GIT_TOKEN}` in URLs). SSH-URLs brauchen einen gemounteten Schlüssel unter
`/home/board/.ssh` im Container.

## Konfiguration

```yaml
title: Team Alpha
refresh_seconds: 60                 # Untergrenze 5
author: Speccify Board <board@example.com>   # Autor der Board-Commits
repos:
  - name: app                       # Buchstaben, Ziffern, . _ -
    url: https://github.com/org/app.git      # flacher Klon des Branch specs
  - name: portal
    url: git@github.com:org/portal.git
    branch: specs                   # Standard
  - name: lokal
    path: /projects/projekt         # Ordner mit .agent/specs …
  - name: alle
    path: /projects                 # … oder ein Ordner voller solcher Projekte
```

`url`-Einträge werden mit `--depth=1` auf ihrem Register-Branch geklont und
im Takt von `refresh_seconds` per `fetch` und `reset --hard` aufgefrischt.
`path`-Einträge werden direkt gelesen; ein Ordner mit mehreren Projekten
bindet jedes Unterverzeichnis mit `.agent/specs` als `name/unterordner` an.
Tokens und Schlüssel gehören in die Umgebung, nie in die Datei.

## Oberfläche und API

| Weg | Inhalt |
|---|---|
| `GET /` | alle Repos: Kennzahlen (auch je Repo), Aktivität 30 Tage, Doing nach Person, Board mit Repo-Kennung und Repo-Filter |
| `GET /r/<name>/` | ein Repo |
| `GET /api/board.json` | Zusammenfassung, Repos mit Commit/Fehler, Specs als JSON |
| `POST /api/refresh` | sofort auffrischen |
| `GET /healthz` | `ok` und Zustand je Repo (ohne Passwort) |
| `POST /api/r/<name>/specs/<id>/station` `{ "station": "Doing" }` | Station wechseln |
| `POST /api/r/<name>/specs/<id>/tasks/<n>` `{ "done": true }` | Task abhaken |

Jede Karte trägt dafür ein Stations-Feld und die Task-Liste. Der Dienst ändert
nur die `station:`-Zeile bzw. die eine Checkbox (byte-stabil, wie die App),
hängt eine History-Zeile mit Akteur `board` an, committet als konfigurierter
Autor (`spec(<id>): … (Web-Board)`) und pusht in den Register-Branch. Wird der
Push abgelehnt, weil das Register weitergelaufen ist, holt er nach, rebased
und pusht erneut; bei einem echten Konflikt meldet er das und lässt die
Entscheidung der App. Lokale `path`-Einträge werden direkt geschrieben.

Nicht enthalten: Login je Person (ein gemeinsames Passwort), Bearbeiten von
Spec-Text, Anlegen von Specs, Echtzeit-Push in den Browser (die Seite lädt
nach Aktionen neu). Ein nicht erreichbares Repo wird oben auf der Seite und
in `/healthz` gemeldet; die anderen Repos laufen weiter.
