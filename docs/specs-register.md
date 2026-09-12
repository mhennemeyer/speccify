# Das gemeinsame Spec-Register (Branch `specs`)

Spec 028, Entscheidung D-TEAM-02. Für Teams, die in Feature-Branches arbeiten
und trotzdem bei allen dasselbe Board sehen wollen.

## Modell

- Der Branch `specs` des Code-Repositories trägt den Inhalt von `.agent/specs`
  als Wurzel: `<NNN-slug>/SPEC.md`, `history.jsonl`, `archive/` und eine
  `.gitattributes` mit `*.jsonl merge=union`.
- Die App hängt ihn per `git worktree add .agent/specs specs` in jeden Checkout
  ein. Erkennbar an der `.git`-**Datei** in `.agent/specs`.
- Die Code-Branches ignorieren `.agent/specs/` (`.gitignore`). Board, Editor,
  Tasks, History und Agenten arbeiten unverändert auf demselben Pfad; Commits
  dort landen auf `specs`, egal welcher Code-Branch ausgecheckt ist.
- Projekte ohne Register verhalten sich wie bisher (Specs im Code-Branch).

## Zustände (Board-Kopf im Projektfenster)

| Zustand | Bedeutung | Was „Einrichten“ tut |
|---|---|---|
| kein Hinweis | kein Git, kein Remote oder Specs nicht getrackt | nichts |
| **Register einrichten…** | Remote vorhanden, `.agent/specs` im Code getrackt, noch kein `specs` | Migration (unten), nach Bestätigung |
| **Einhängen** | `specs` bzw. `origin/specs` existiert, Worktree fehlt (frischer Klon) | `git worktree add`, Branch wird von `origin/specs` verfolgt |
| **blockiert** | Register existiert, aber der aktuelle Code-Branch trackt `.agent/specs` noch | nichts; Branch auf main rebasen |
| **Register `specs` · …** | eingehängt; Stand: aktuell / n nicht gesendet / n zu pushen / n neu vom Team / Konflikt | Sync-Knopf |

## Migration

Läuft nur auf `main`/`master`, mit sauberem `.agent/specs` und Remote `origin`:

1. Orphan-Commit aus dem Baum `HEAD:.agent/specs` plus `.gitattributes`
   (temporärer Index, kein Arbeitsbaum-Zugriff) → Branch `specs`.
2. `git rm -r .agent/specs`, `.agent/specs/` in `.gitignore`, ein Commit
   `chore: .agent/specs wird Worktree des Branch specs (Spec 028)`.
3. `git worktree add .agent/specs specs`.
4. `git push -u origin specs`, dann `git push origin <main>`. Scheitert ein Push
   (z. B. geschützter Branch), bleibt der lokale Stand konsistent; der Fehler
   steht im Board-Kopf.

**Vorher offene Branches rebasen.** Git hält ignorierte Dateien für
entbehrlich: der Checkout eines alten Branches, der `.agent/specs` noch trackt,
gelingt und überschreibt den Worktree mit dem alten Stand (Zustand
*blockiert*, kein Sync). Beim Wechsel zurück auf `main` entfernt Git diese
Dateien wieder; der nächste Sync erkennt, dass alle `SPEC.md` fehlen, und
stellt das Register aus dem Branch wieder her, statt Löschungen zu committen.

## Sync

Die App synchronisiert von selbst: drei Sekunden nach der letzten
Board-Änderung und mindestens jede Minute, sowie per Knopf.

1. Geänderte Dateien committen: `spec(<id>[, …]): aktualisiert`.
2. `git fetch origin specs`.
3. Liegt das Team vorn: `git rebase origin/specs` (History-Dateien mergen per
   `union`; die Anzeige sortiert nach Zeitstempel).
4. Eigene Commits pushen. Nie `--force`.

Offline bleiben Commits lokal („n zu pushen“, Fehlerzeile „Fetch: …“); ein
späterer Sync holt alles nach, ohne History-Zeilen oder Specs zu verdoppeln.

## Konflikte

Ändern zwei Personen dieselbe Zeile (typisch `station:` oder `owner:`), stoppt
der Rebase. Der Board-Kopf zeigt je Datei beide Fassungen — *Team*
(`origin/specs`) und *Meine Fassung* — und drei Wege: Team-Fassung übernehmen,
eigene behalten oder die im Editor bereinigte Datei als gelöst markieren.
*Abbrechen* stellt den eigenen Commit her und lässt Register und Team
auseinander stehen, bis es erneut versucht wird. Solange ein Konflikt offen
ist, wird nicht synchronisiert; eine `SPEC.md` mit Konfliktmarkern erscheint
bis dahin nicht auf dem Board, wohl aber in der Konfliktliste.

## Besitzer und Branch (Spec 029)

Beim Übernehmen (Backlog → Doing per Drag oder Knopf *Übernehmen* im
Inspektor) trägt die App `owner: Name <email>` (Git-Identität des Checkouts)
und `branch:` ein — den aktuellen Feature-Branch oder den Vorschlag
`spec/<NNN>-<slug>`; `main`/`master` gelten nicht als Arbeitsbranch. *Abgeben*
(oder Drag zurück ins Backlog) entfernt `owner`, `branch` bleibt als Spur.
Done behält beide als Nachweis. Projekte ohne Git setzen nichts.

Karten zeigen Initialen (Tooltip Name) und Branch. Über dem Board filtert
**meine** nach der eigenen E-Mail; **Doing nach Person** listet alle
Doing-Specs gruppiert mit Branch und letzter Bewegung. Der Inspektor zeigt
Besitz, Branch und Abweichungen, die die App aus Git beobachtet, aber nie
korrigiert: Checkout steht woanders (Wechseln erst nach Bestätigung, ggf. mit
Anlegen), Branch fehlt lokal oder auf origin, zuletzt hat jemand anderes
gepusht, seit N Tagen keine Bewegung. Die Beobachtung holt höchstens einmal pro
Minute `git fetch --prune origin`.

Zwei gleichzeitige Übernahmen ändern dieselbe `owner`-Zeile und werden beim
Sync des Registers als Konflikt sichtbar.

## Nummern

Neue Specs nehmen die nächste freie Nummer über lokale Ordner **und**
`origin/specs` (Stand des letzten Fetch). Kollisionen bleiben möglich, wenn
zwei Personen offline gleichzeitig anlegen; sie werden beim Sync als zwei
Ordner sichtbar und von Hand umbenannt.

## Regeln für Agenten

Stehen in der Workflow-Policy (v6) unter „Shared spec register“: Specs nur
unter `.agent/specs` bearbeiten, nicht selbst committen, solange die App
läuft; sonst `add`/`commit`/`pull --rebase`/`push` ohne Force; gestoppte
Rebases melden, nicht auflösen; in frischen Klonen den Worktree einhängen;
`.agent/specs` nie in einen Code-Branch committen.

## Release

Zum Release den Commit des Branch `specs` in den Release-Notizen nennen
(`git -C .agent/specs rev-parse HEAD`), damit der Anforderungsstand zum Code
reproduzierbar bleibt.
