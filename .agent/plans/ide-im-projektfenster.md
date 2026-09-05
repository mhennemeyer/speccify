---
lifecycle: draft
status: Recherche 2026-09-05 abgeschlossen — Vorschlag steht, wartet auf BO-Entscheide E1–E5
---
# Plan: IDE-Bausteine im Projektfenster

> **BO (2026-09-05):** „Wir hatten mit iKanbanAI schonmal eine relativ
> vollständige IDE eingebaut. Bitte Recherche/Plan, ob/wie wir das hier
> auch tun könnten. iKanbanAI litt unter der Sandbox. Hier wären wir freier
> … committen/pushen/pullen, Dateien browsen und über Aktionen das Projekt
> starten/testen, ohne nebenbei IntelliJ offen zu haben."

## Was iKanbanAI hatte — und woran es litt

Aus dem Quelltext (`~/Desktop/Work/iKanbanAi`, Paket `iKanbanAiKit`) und
dem stillgelegten Plan `ide-durch-ai.md`:

* **Dateien:** `ProjectFiles` + `FilesUI` — Projektbaum mit Cache,
  Editor-Tabs, Navigations-Historie, Projektsuche, Datei-Inspektor,
  Datei-Zusammenfassungen (`FileSummaries`).
* **Editor:** CodeEditSourceEditor (nur im App-Target), Emacs-Keymap,
  Wort-Navigation, Symbol-Sprung auf Basis eigener Outline-Indizes.
* **Git:** `InProcessGit` auf **libgit2** (`Clibgit2`, statisch gelinkt):
  Status, Commit, Branches, Remotes (Spike), Hunk-Staging, Datei-History,
  Ticket-Commits — plus `GitUI` mit Panel.
* **Aktivität:** `Activity`/`ActivityUI` — das Vorbild für unsere
  Aktivitätsanzeige (W7d).
* **Die Sandbox-Wand:** Als App-Store-App durfte sie keine
  User-Binaries spawnen (node, mvn, dotnet, git …). Deshalb der Umweg
  **Exec-MCP als externer Prozess** und libgit2 im Prozess statt `git`.
  Genau diese Wand gibt es bei Speccify nicht: Tauri-App, Developer-ID-
  signiert, **nicht** sandboxed, spawnt heute schon Shell, Agent und
  Aktionen.

## Was Speccify heute schon hat

Agent-Terminal (PTY, Rust), **Aktionen** mit Live-Output, Stop und
Fortschritt (= „Projekt starten/testen"), Watcher mit Live-Reload,
Markdown-Rendering und -Editor für Pläne/Playbooks/Tickets, Inspektor mit
Slots, Navigator mit Gruppen. Fehlt für „kein IntelliJ nebenbei":
**Dateibaum, Code-Editor, Git.**

## Vorschlag: drei Bausteine, in dieser Reihenfolge

### I1 — Dateien: Baum + Editor (die Basis)

* **Navigator-Gruppe „Dateien"** (fünftes Icon): Projektbaum aus Rust
  (`project_tree(path)`, lazy je Ordner, `.gitignore` respektiert über
  das `ignore`-Crate, `.git`/`node_modules`/`target` zu), Suche nach
  Dateinamen. Der bestehende Watcher meldet Änderungen → Baum lädt nach.
* **Editor in der Mitte:** **CodeMirror 6** (leicht, ~300 kB, MIT,
  Syntax für Markdown/TS/Rust/Python/JSON/YAML/TOML, Suche/Ersetzen,
  Mehrfach-Cursor, Emacs-Keymap-Paket vorhanden). Monaco wäre die
  VS-Code-Parität, wiegt aber ~3 MB und braucht Worker-Setup unter
  Tauri — als spätere Option offen (E2). Tabs für offene Dateien, „Als
  Prompt kopieren" mit `Pfad:Zeile`, Speichern mit Cmd-S über das
  vorhandene `project_write_file` (Traversal-Guard bleibt).
* **Inspektor:** Dateiinfo (Größe, geändert, Git-Status, letzte Commits
  der Datei ab I2).
* **Kein LSP, kein Refactoring** in I1 — das ist der Punkt, an dem eine
  IDE zur IDE wird und den der Agent im Terminal besser abdeckt als wir
  ihn nachbauen (E3).

### I2 — Git: Status, Diff, Commit, Push/Pull

* **Weg über das System-`git`** statt libgit2 (E1). Begründung: keine
  Sandbox; `git` ist bei jedem Nutzer da, der Speccify nutzt; **Credentials
  laufen über die vorhandenen Helper** (osxkeychain, Windows Credential
  Manager, SSH-Agent) — genau das war mit libgit2 mühsam (TLS-Backend,
  Credential-Callbacks, Windows). Rust ruft `git` mit `--porcelain`-
  Formaten (`status --porcelain=v2`, `diff --numstat`, `log --format`),
  parst zeilenweise, Timeout und cwd = Projektwurzel. Kein Shell, argv
  wie bei den Aktionen.
* **Panel** (Gruppe „Dateien", Tab „Git" oder eigener Tab in der Toolbar):
  Branch + ahead/behind, geänderte Dateien mit Status, Diff-Ansicht
  (CodeMirror-Merge-View), Datei-weises Stagen, Commit mit Nachricht,
  **Pull/Push mit Live-Output** über die Aktions-Mechanik (Aktivität zeigt
  „Push läuft"). Hunk-Staging wie in iKanbanAI erst in I3 — Datei-weise
  reicht für den Alltag, der Agent committet ohnehin ganze Tickets.
* **Zusammenspiel mit dem Board:** Commits, die eine Ticket-Id nennen,
  erscheinen in der Ticket-Historie (`ticket_commits`, wie iKanbanAI).
* Konflikte: anzeigen, Datei im Editor öffnen, keine Merge-UI (E4).

### I3 — Komfort nach Gebrauch

Hunk-Staging, Datei-History im Inspektor, Blame am Rand, Projektsuche in
Inhalten (`ripgrep` via Rust-Crate `grep`), Springen aus Terminal-Ausgaben
(`pfad:zeile`) in den Editor, Zuletzt-geöffnet je Projekt, Tastaturkürzel.

## Entscheidungen für den BO

* **E1 — Git-Anbindung:** System-`git` (Empfehlung) oder `git2`-Crate
  (libgit2 statisch; unabhängig von installiertem Git, aber TLS- und
  Credential-Handling selbst, Windows-Build mit OpenSSL-Vendoring).
* **E2 — Editor:** CodeMirror 6 (Empfehlung, leicht, gut in React) oder
  Monaco (VS-Code-Gefühl, schwer).
* **E3 — Anspruch:** „Editor + Git + Aktionen" (Empfehlung: das ersetzt
  IntelliJ für Agent-geführte Arbeit) oder echte IDE mit LSP/Refactoring
  (Größenordnung anders, eigener Plan).
* **E4 — Merge-Konflikte:** nur anzeigen (Empfehlung) oder 3-Wege-UI.
* **E5 — Wo im Fenster:** eigene Navigator-Gruppe „Dateien" (Empfehlung)
  oder Dateien in „Technik".

## Aufwand und Reihenfolge

Iterativ, jeder Baustein für sich nutzbar: I1 zuerst (Baum + Editor sind
die Basis für alles andere und sofort nützlich), dann I2 (Git ist der
eigentliche Grund, IntelliJ noch offen zu haben), I3 nach Gebrauch. Die
Risiken liegen nicht in Tauri (kein Sandbox-Thema, Prozesse spawnen wir
längst), sondern in der Editor-Ergonomie (Cmd-S, Tabs, große Dateien)
und im Git-Parsing über Plattformen (Pfade mit Leerzeichen, Windows-
Zeilenenden, Umlaute → `-z`-Modi nutzen).

## Nicht in diesem Plan

LSP/Autovervollständigung, Debugger, Datenbank-Panels (iKanbanAI-Idee
„Ad-hoc-Tool-UIs" — bleibt Aktionen-/toolui-Thema), Remote-Repos ohne
lokalen Klon.
