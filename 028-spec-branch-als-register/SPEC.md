---
station: Doing
order: 8
created: 2026-09-12
needs_human: true
ready: true
open_question: null
parent: null
---
# Spec-Branch als gemeinsames Register: Worktree unter `.agent/specs` und Sync

## Why

Das Team arbeitet in Feature-Branches, aber das Board soll bei allen denselben
Spec-Stand zeigen — ohne Code-Merges, ohne Branchwechsel und ohne ein zweites
Repository. Die Kopie der Specs im jeweiligen Code-Branch ist heute die einzige
Wahrheit; sie ist für andere erst nach Push und Merge sichtbar und kollidiert
beim Merge. Vorschlag D-TEAM-02 im
[Visionsplaybook](../../playbooks/weiterentwicklung.md#v1-09--team-board-trotz-feature-branches)
(V1-09), abgeleitet aus D-TEAM-01; löst den Pilot aus
[016](../016-gemeinsames-spec-register/SPEC.md) ab.

## What

Ein Branch `specs` im selben Repository trägt `.agent/specs` als Wurzel
(Ordner `<NNN-slug>/SPEC.md`, `history.jsonl`, `archive/`, `.gitattributes`).
Die App hängt ihn per `git worktree add .agent/specs specs` in jeden Checkout
ein; die Code-Branches ignorieren `.agent/specs/`. Board, Editor, Tasks,
History und Agenten arbeiten unverändert auf demselben Pfad.

Sync als expliziter Vertrag in der App: Änderungen im Register werden
gebündelt committet (Nachricht `spec(<id>): <was>`), dann `fetch`,
`rebase` auf `origin/specs`, `push`. Kein Force-Push. `history.jsonl`
mergt per `merge=union`; die Anzeige sortiert nach Zeitstempel. Konflikte
in `SPEC.md` (dieselbe Zeile, z. B. `station`) stoppen den Sync, markieren
die Spec als „Konflikt“, zeigen beide Fassungen und lassen die Person
entscheiden; nichts geht verloren. Offline-Stände sind als „n Änderungen
nicht gesendet“ sichtbar. Ein periodischer `fetch` (Standard 60 s, abschaltbar)
holt fremde Änderungen, wenn lokal nichts Unversendetes offen ist.

Einrichten: der bestehende „Einrichten“-Knopf erkennt drei Zustände —
(a) `origin/specs` fehlt: Migration anbieten (Orphan-Branch aus dem aktuellen
`.agent/specs`, Ignore-Regel, Worktree) mit Hinweis auf offene Branches;
(b) `origin/specs` existiert, Worktree fehlt (frischer Klon): Worktree anlegen;
(c) alles vorhanden: Sync-Status zeigen. Die Migration verweigert, wenn der
aktuelle Branch `.agent/specs` noch trackt und nicht `main` ist, und nennt
den Grund (Checkout alter Branches bricht sonst mit „untracked working tree
files would be overwritten“). Nummernvergabe neuer Specs prüft vor dem
Anlegen gegen `origin/specs`.

Nicht enthalten: Besitzer/Branch je Spec (029), Benachrichtigungen und
Fragen an Personen (030), Migration fremder Repos, Änderungen am
Workspace-Board (024 liest weiter je Repo), Konflikteditor für Code.

## Acceptance

- Wenn zwei Klone denselben `specs`-Branch eingehängt haben und in einem eine
  Task getickt und synchronisiert wird, dann zeigt der andere nach Sync den
  Tick, ohne dass ein Code-Branch gewechselt oder gemergt wurde.
- Wenn beide Klone gleichzeitig History-Zeilen anhängen und verschiedene
  Zeilen derselben Spec ändern, dann enthält das Ergebnis nach Sync alle
  Zeilen und beide Änderungen ohne Konflikt.
- Wenn beide dieselbe Front-Matter-Zeile ändern, dann stoppt der Sync, die Spec
  ist als Konflikt markiert, beide Fassungen sind sichtbar, und erst die
  ausdrückliche Entscheidung setzt den Sync fort; kein Force-Push.
- Wenn das Remote nicht erreichbar ist, dann bleiben Änderungen lokal
  committet und als nicht gesendet sichtbar; ein späterer Sync dupliziert keine
  History-Zeilen und keine Specs.
- Wenn ein frischer Klon geöffnet wird, dann bietet „Einrichten“ den Worktree
  an und das Board zeigt danach das Register; ohne Worktree zeigt es klar
  „Register nicht eingehängt“ statt eines leeren Boards.
- Wenn die Migration in einem Repo läuft, dessen aktueller Branch
  `.agent/specs` noch trackt, dann wird sie mit Begründung verweigert.
- Wenn ein Projekt kein `origin/specs` hat und die Migration nicht ausgelöst
  wurde, dann verhält es sich unverändert (lokale Specs im Code-Branch).
- Wenn der Agent im Terminal Specs ändert, dann synchronisiert die App sie
  ohne weiteres Zutun; die Policy sagt dem Agenten, wann er selbst committen
  darf (App aus) und dass er nie forciert.

## Decisions

- D1, 2026-09-12: Branch im selben Repo statt separates Repo (Vorschlag
  D-TEAM-02). Gründe: gleiche Rechte und Remote, ein Ordner zum Öffnen,
  derselbe Pfad für Agenten, je Repo ein Register passt zum Workspace-Modell.
  Probelauf mit zwei Klonen (`probe-worktree.sh` neben dieser Spec)
  erfolgreich: Sync, Union-Merge, Konflikt, Migrationsfalle — siehe
  Verification.
- D2, 2026-09-12: Die App synchronisiert das Register; Agenten bearbeiten
  Dateien wie bisher. Rebase statt Merge-Commits, Union-Merge nur für
  `*.jsonl`. Kein automatisches Auflösen von `SPEC.md`-Konflikten.
- D3, 2026-09-12: Branchname `specs`, Worktree-Pfad `.agent/specs`; beides
  fest, keine Konfiguration im ersten Schnitt.
- D5, 2026-09-12: BO bestätigt D-TEAM-02 („Leg los“); Umsetzung gestartet.
- D4, 2026-09-12: Die Migration des Speccify-Repos selbst ist Teil dieser
  Spec, läuft aber erst nach BO-Freigabe (offene Branches rebasen; prüfen, ob
  CI oder Website Specs aus dem Code-Branch lesen).

## Tasks

- [x] Vertrag `docs/specs-register.md`: Branch, Worktree, Sync, Konflikte,
      Offline, Einrichten-Zustände, Policy-Ergänzung (Vorlage
      `workflow-policy.md` v6, Abschnitt „Shared spec register“; v5 im
      Vorlagen-Archiv).
- [x] Native Befehle: Registerstatus (Branch/Worktree/ahead/behind/Konflikte),
      Einrichten (Migration, Worktree), Sync (commit → fetch → rebase → push),
      Konflikt lesen/entscheiden; Nummernvergabe gegen `origin/specs`.
      `spec_register.rs`: `project_register_status/setup/sync/resolve/abort`;
      `next_spec_number` zählt `origin/specs` mit.
- [x] Watcher: Registeränderungen gebündelt committen; periodischer Fetch.
      `project_watch.rs`: Sync 3 s nach Board-Ruhe und jede Minute, Ereignis
      `register-changed`.
- [x] UI: Sync-Status in Toolbar/Board (aktuell, n ungesendet, Konflikt),
      Konfliktansicht je Spec, „Einrichten“ mit den drei Zuständen.
      `RegisterBar.tsx` über dem Board; Karten mit Badge „Konflikt“.
- [x] Rust-Tests mit zwei Klonen (Sync, Union, Konflikt, Offline, frischer Klon,
      Migrationsverweigerung); Mock-Fixture und Browser-Suite für die UI.
- [x] Release-Playbook: Commit des `specs`-Branch im Release notieren.
- [x] Schutz vor Git-Verhalten „ignorierte Dateien sind entbehrlich“: alter
      Branch überschreibt den Worktree → Zustand blockiert, kein Sync; Rückkehr
      auf main räumt ihn → Sync stellt aus `specs` wieder her, committet nie
      die Totalräumung (added).
- [x] Migration des eigenen Repos nach BO-Freigabe; Stand-Playbook und Hilfe.
      2026-09-12 auf `main` (Commit `ea481b0`), Register-Commit `fac75cb`, beide
      gepusht; diese Spec liegt seitdem im Register.

## Verification

Umsetzung 2026-09-12 (Arbeitsbaum auf `326ea59`):

- `cargo test -p speccify-desktop`: 102 bestanden, 3 ignoriert. Neue Tests in
  `spec_register.rs` mit echten Git-Repos (Bare-Remote, Klone A/B): Migration
  baut `specs`, Code-Checkout sauber, Ignore-Regel, Worktree, Push; Verweigerung
  auf Feature-Branch, bei uncommitteten Specs und ohne Remote; zwei Klone
  synchronisieren ohne Code-Merge (A auf `spec/001-x`, B auf `main`), Commit-
  Betreff `spec(001-x): aktualisiert`, Union-Merge der History (4 Zeilen),
  Konflikt auf `station` mit beiden Fassungen, Entscheidung Team/Meine,
  Abbrechen, `remote_max_number`; Offline (Remote-URL ungültig) hält Commits
  lokal, kein Doppel-Commit, nach Rückkehr alles gepusht; alter Branch →
  `blocked`, Rückkehr → Wiederherstellung ohne Löschungs-Commit. Befund dabei:
  Git überschreibt **ignorierte** Dateien beim Checkout (anders als
  untracked im Probelauf) — deshalb der Schutz in Task 7. `cargo fmt --check`,
  `pnpm typecheck` grün.
- Browser-Suiten gegen `dev/mock.html`: neue Suite `test_spec_register`
  (none/migratable mit Bestätigung/detached/blocked/mounted mit Sync und
  Live-Ereignis/conflict mit beiden Fassungen, Karten-Badge, Entscheidung/
  abort) plus die elf bestehenden grün.
- Policy v6 in `.agent/agent.md` gespiegelt; markdownlint über die geänderten
  Dokumente 0 Befunde (Vorlagen sind nicht im Lint-Umfang).

Migration des eigenen Repos 2026-09-12 mit den dokumentierten Schritten
(Orphan-Commit aus `HEAD:.agent/specs` + `.gitattributes`, `git rm`, Ignore-
Regel, Commit `ea481b0` auf `main`, `git worktree add`, Push von `specs`
(`fac75cb`) und `main`): Code-Checkout sauber, Worktree eingehängt (31 Einträge,
`.git`-Datei), Register-Status sauber. Offene lokale Alt-Branches (`archive/*`,
`dev`, `feat/oss-pivot`, `feature/landing-page`) tracken `.agent/specs` noch:
ihr Checkout überschreibt den Worktree (Zustand blockiert, Rückkehr stellt
wieder her) — vor einer Weiterarbeit auf ihnen rebasen. Nicht geprüft: Klick-
Durchlauf im Projektfenster mit dem neuen Build und ein zweiter Rechner
(Einhängen im frischen Klon) — menschliche Abnahme, daher `ready`.

Probelauf 2026-09-12 (`probe-worktree.sh` neben dieser Spec; Git lokal, zwei
Klone A/B gegen ein Bare-Remote): Migration per Orphan-Branch und `git rm` +
Ignore auf `main`; Worktree in A und B; Tick auf Code-Branch `spec/001-x` in A
ist nach `pull --rebase` in B sichtbar, B bleibt auf seinem Code-Branch;
beidseitige History-Anhänge plus verschiedene Zeilen → Rebase ohne Konflikt
(4 History-Zeilen, beide Ticks, geänderte `order`); dieselbe `station`-Zeile →
`CONFLICT (content)`, `rebase --abort` stellt den Stand her, äußerer Checkout
sauber; Checkout eines Branches mit getracktem `.agent/specs` scheitert mit
„untracked working tree files would be overwritten“; frischer Klon hat keinen
Worktree. Umsetzung in der App noch nicht begonnen.

## Questions

Keine blockierende Frage; Migration des eigenen Repos wartet auf Freigabe (D4).
