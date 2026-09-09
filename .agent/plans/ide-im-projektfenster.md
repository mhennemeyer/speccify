---
lifecycle: active
status: I1 + I2 geliefert (2026-09-06); I3-Kern geliefert 2026-09-09 (BO-Auftrag „Aktionen, konfigurierbare Toolbar, Git vollständig, Datei-Historie im Inspektor, Inspektor-Tabs") — Hunk-Staging, Verwerfen, Commit-Details, Branches, Datei-Historie in Git- und Dateien-Inspektor, Toolbar-Knöpfe (eingebaut + Aktionen) wählbar und sortierbar; I3-Rest ebenfalls 2026-09-09: Projektsuche (ripgrep-Bausteine), Blame-Gutter, pfad:zeile-Links im Terminal, Dateien anlegen/umbenennen/löschen (Papierkorb) — I3 komplett, es bleibt „Zuletzt geöffnet je Projekt" und Tastaturkürzel für den Editor
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

## Entscheidungen

> **BO (2026-09-06):** „git library kannst du selbst entscheiden. Welche
> besser passt." → Entscheide E1–E5 wie empfohlen getroffen:

* **E1 System-`git`.** Ausschlag: Credentials (osxkeychain, Windows
  Credential Manager, SSH-Agent) funktionieren ohne eigenes Zutun; kein
  TLS-/OpenSSL-Vendoring im Windows-Build; `git` ist bei jedem Nutzer
  von Speccify installiert (Skill-Quellen laufen ohnehin über Git). Preis:
  Ausgabe-Parsing, gelöst über die `-z`/`--porcelain=v2`-Formate.
* **E2 CodeMirror 6**, **E3 Editor + Git + Aktionen** (kein LSP),
  **E4 Konflikte nur anzeigen**, **E5 eigene Navigator-Gruppe „Dateien"**.

## Entscheidungen (ursprüngliche Fragen)

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

## Stand

**I1 ✅ 2026-09-06 — Dateien: Baum + Editor.** Rust `files_cmd.rs`:
`project_tree(dir)` lazy je Ordner über das `ignore`-Crate (.gitignore,
.git/info/exclude, `.git` immer zu, Ordner zuerst), `project_file_info`
(Größe, Änderungsdatum RFC 3339, Zeilen bis 5 MB, Binär-Erkennung per
NUL im Kopf); Tests für Baum und Info. Frontend: Navigator-Gruppe
**Dateien** (⌘2, die Bereiche rücken auf ⌘1–5), `FilesTab.tsx` (Baum mit
Filter, Tabs offener Dateien mit Dirty-Punkt, Schließen fragt bei
Ungespeichertem, Watcher lädt offene Ordner und ungeänderte Dateien
nach), `CodeEditor.tsx` auf CodeMirror 6 (`basicSetup`, Sprache nach
Endung für md/ts/tsx/js/py/rs/json/yaml/html/css, `oneDark` folgt
`data-theme` per MutationObserver, `Mod-s` speichert, Tab rückt ein),
Inspektor mit Größe/Zeilen/Datum/Zustand/Cursor und Speichern,
Verwerfen, Als Prompt kopieren (`Pfad:Zeile`), Pfad kopieren. Speichern
läuft als Aktivität. Bewusst nicht: Anlegen/Umbenennen/Löschen von
Dateien (I3), Binärdateien nur als Hinweis.

**I2 ✅ 2026-09-06 — Git über System-git.** Rust `git_cmd.rs`: `git`
per argv (kein Shell), cwd Projekt, `GIT_TERMINAL_PROMPT=0`, `LC_ALL=C`,
30-s-Timeout, Windows `CREATE_NO_WINDOW`; `project_git_status`
(`--porcelain=v2 --branch -z`, Parser mit Branch/Upstream/ahead-behind,
Records 1/2/u/?, exaktes `splitn`, damit Pfade mit Leerzeichen ganz
bleiben), `project_git_diff` (Index/Arbeitsbaum, Untracked gegen
/dev/null bzw. NUL), `project_git_stage` (`add -A` / `restore --staged`,
ohne HEAD `rm --cached`), `project_git_commit`, `project_git_log`
(Unit-Separator-Format), `project_git_init`. Tests: Parser (Rename,
Konflikt, Untracked), Log, echter Roundtrip in einem Temp-Repo (init →
untracked → stage → unstage → commit → log). Frontend `GitTab.tsx` als
zweiter Tab der Gruppe Dateien: Branch-Kopf mit fetch/pull/push über
`project_action_run` (run_id `git:…`, Live-Ausgabe, Aktivität), Listen
Staged/Änderungen mit +/− und alle-Knöpfen, Commit-Box, Diff-Ansicht
(eingefärbte Zeilen), letzte 20 Commits; Inspektor mit Zustand, Stagen,
„Im Editor öffnen" (Event `speccify:open-file` → FilesTab klappt die
Ordner auf) und „Diff als Prompt". Leerzustände: kein Repo → `git init`
per Knopf, sauber → „Alles committet". **BO-Finding 2026-09-06 („auch
via Button, mit Nachricht oder durch den Agenten"):** Commit-Panel in den
Inspektor (ohne Dateiauswahl), Knopf *Commit…* im Branch-Kopf fokussiert
es, ⌘⏎ committet, *Alles committen* staged vorher, *Agent committen
lassen* tippt den Auftrag per `speccify:type-command` ins Terminal
(Enter dort bestätigt; kein Terminal → Hinweis). **BO-Finding
2026-09-06 („geänderte Datei fehlte im Git-Tab"):** der Watcher kennt nur
die `.agent`-Bereiche, nicht den Arbeitsbaum, und Tabs bleiben gemountet
→ Git- und Dateien-Tab laden beim Sichtbarwerden neu, der Git-Tab fragt
sichtbar alle 4 s `git status` (versteckt gar nicht), Speichern im Editor
meldet `speccify:worktree-changed`. Bewusst nicht:
Hunk-Staging, Branch-Wechsel, Merge-UI (I3/E4).

**Dogfooding-Voraussetzung ✅ 2026-09-07 — Agent-Sitzung überlebt den
Neustart (BO-Frage: „Hook beim Runterfahren, Memory persistieren?").**
Antwort: kein Hook — `tauri dev` killt den Prozess ohne zu warten, und
Claude Code/Codex schreiben ihr Protokoll ohnehin fortlaufend. Stattdessen
Fortsetzen: Merker `speccify.project.agentSession:<root>` beim Start
eines Agent-Terminals; beim nächsten Öffnen des Fensters startet das
Terminal automatisch mit `continueCommand()` (`claude --continue`,
`codex resume --last`, freie Kommandos unverändert), Aktivität
„Agent-Sitzung fortgesetzt". Option `resumeAgent` im Layout/Settings-
Sheet (Default an); aus → Knöpfe „Letzte Sitzung fortsetzen" / „Neu
starten". Verloren geht nur der gerade laufende Werkzeugaufruf. Mock:
Playwright — Reload startet mit `--continue`, Option aus → manuell.

**Autosave + Entwurfs-Speicher ✅ 2026-09-07 (BO-Vorfall: ein Rust-Rebuild
startete die Dev-App neu, ein halb geschriebener Plan war weg).**
`lib/autosave.ts`: `useAutosave` hält den Editorinhalt gegen die Datei
gespeichert — Entwurf synchron in localStorage bei jedem Tastenanschlag
(`speccify.draft:<projekt>:<datei>`), Datei 1,2 s nach dem Tippen, Rest
beim Unmount; Status „Entwurf gesichert · speichert gleich…/Gespeichert".
Plan- und Playbook-Editor: kein Abbrechen mehr (Git ist die Historie),
*Jetzt speichern* + *Fertig*; liegt beim Öffnen ein Entwurf ≠ Datei, wird
er wiederhergestellt (Hinweis), und die Plan-Ansicht zeigt schon vor dem
Bearbeiten „Ungespeicherter Entwurf vorhanden — Wiederherstellen".
Code-Editor: Entwurf bei jedem Tastenanschlag, ⌘S bleibt; beim Öffnen
kommt der Entwurf als ungespeicherter Zustand zurück. **Lehre für die
Arbeitsweise:** Rust-Änderungen starten die Dev-App des BO neu —
bündeln und vorher ankündigen.

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
