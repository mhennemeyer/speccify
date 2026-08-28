# Log: Speccify

## 2026-08-28, abends (Projektfenster — BO-Findings nach P3-Gebrauch)
- Sieben Findings eingearbeitet (Plan: D21–D24 + neuer P4-Zuschnitt):
  Work-Repo pro Projekt überschreibbar (D21, Kundenprojekte mit eigenem
  Skill-Repo), Terminal rechts/unten (D22, **umgesetzt**: Toggle im
  Terminal-Kopf, pro Projekt gemerkt, kein Remount dank ResizeObserver),
  Agent-Config im Dashboard editierbar (D23; codex geprüft:
  `~/.codex/config.toml`, projektseitig `.codex/config.toml`, AGENTS.md),
  Skill-Quellen pro Projekt + Skill-Browser mit Ordner-Organisation und
  Import via expand (D24 → P4-Kern), Windows-Zielbild nativ ohne
  Parallels (P4-Notiz).
- **Rollen-Klarstellung** (BO): Speccify **definiert** Board-/Aktions-/
  ask_bo-Formate, iKanbanAI ist (unter anderem) ein **Client**. Alle
  iKanbanAI-Referenzen aus Produkt-Texten gedreht bzw. entfernt
  (BoardTab, project_cmd, AskBoPanel, desktop_ui, discovery-mcp,
  docs/toolkit.md); D19 heißt jetzt „Speccify-Board-Format".

## 2026-08-28, später (Projektfenster P3 — Board, Plan-Editor, alle Tabs, Composer-Rückbau)
- **BO-Erweiterung + Entscheide**: Board im Projektfenster (D19, Format:
  **iKanbanAI lesen** — das liegt ohnehin im Projekt: `.agent/board/<id>.md`,
  flaches Frontmatter, Stationen Backlog/Doing/Done, Backlog-Sortierung
  `order → created → id`); Pläne **editierbar** (D20, strukturiert + Body).
  Format aus dem iKanbanAi-Quelltext gelesen (Tickets/TicketStore.swift,
  nur lesend).
- **Board-Tab (D19)**: Rust `project_board` (eigener Flat-Parser, kein
  serde_yaml — byte-Stabilität) + `project_board_move` (ersetzt NUR die
  `station:`-Zeile; Guard: nur `.agent/board/`, nur bekannte Stationen).
  Frontend drei Spalten, Karten mit `ready`/`braucht BO`-Badges,
  Ticket-Detail als Markdown, Verschieben per Pfeil-Knopf. E2E auf macOS:
  Ticket verschoben, Datei diff-gleich bis auf die station-Zeile —
  iKanbanAI zieht per DirectoryWatcher live nach.
- **Plan-Editor (D20)**: `project_write_file` (gleicher Traversal-Guard wie
  read, geteilt in `safe_project_path`), Formular lifecycle/status +
  Body-Editor; unbekannte Frontmatter-Zeilen bleiben wörtlich erhalten.
  E2E: Status ersetzt, Body ergänzt, Frontmatter intakt.
- **Tools-/MCPs-/Agent-Tab**: `project_tools` (TOOL.md + `tools:`-Sektion
  aus expansions.yaml, Status je Plattform, „fehlt auf dieser Plattform"
  prominent + `project_platform`), `project_mcps` (`.mcp.json` +
  `permissions.allow` aus settings.json **und** settings.local.json),
  `project_agent_files` (CLAUDE.md/AGENTS.md/.agent/AGENT.md) + Agent-
  Kommando-Feld im Agent-Tab. Windows-Default des Agent-Kommandos jetzt
  **`claude.cmd`** (P2-Befund ExecutionPolicy).
- **Composer-Rückbau (D18)**: `apps/composer/` + ComposerView gelöscht;
  lib.rs ohne open_composer/BackendLaunch/free_port/wait_for_port;
  Web-Backend ohne `/ui`-Mount und `composer_dist`; ci.yml ohne
  `composer`/`composer-e2e`-Jobs; build_engine_payload.sh packt nur noch
  Engine + Skills; dev.sh/dev-up.sh/release.yml/Doku bereinigt;
  pnpm-workspace ohne apps/composer. Nebenfund: neuere mypy-Version
  moniert dict-Invarianz in `_resolve_reference` → `Mapping` (`fbd0dc2`).
- **Verifikation**: 228 Pytest, 25 Rust-Desktop-Tests, Frontend-Build,
  ruff + mypy clean; E2E am Fixture-Projekt auf macOS (alle sechs Tabs,
  Board-Move, Editor-Save per AX-Automation). Windows-Check läuft.

## 2026-08-28 (Projektfenster P2 — „Fertig heißt" bestanden)
- BO hat claude in der VM autorisiert (Claude Max, Opus 5). Frage per CDP
  in die laufende Session im Projektfenster-Terminal getippt: „Welche
  Skills stehen dir in diesem Projekt zur Verfügung?" → claude listet
  **alle elf Projekt-Skills hinter der Junction** (apple-developer-id-cert
  … storekit2-subscription-paywall, inkl. speccify), dazu seine eigenen
  gebündelten Skills. Der P2-Zielsatz — App startet, Projekt öffnet, Tabs
  zeigen Daten, im Terminal läuft claude und findet die Skills — ist damit
  wörtlich eingelöst. P2 zu; weiter mit P3.

## 2026-08-27, später (Projektfenster P2 fertig — Junction, CI, ENTRYPOINT geklärt, Claude Code am Login)
- **D17 ✅** `speccify link` (`9b0b71f`): erkennt Gits Symlink-Hülse (Checkout
  ohne Symlink-Recht = Textdatei mit Zielpfad) und ersetzt sie; ohne
  Symlink-Privileg **Junction-Fallback** (`_winapi.CreateJunction`, Ziel
  absolut). In der VM als normaler Benutzer verifiziert: `<JUNCTION>
  .claude\skills → C:\work\speccify\.agent\skills`, elf Skills sichtbar.
  Merker: ein von SYSTEM angelegter `.venv` blockiert den Benutzer —
  `uv sync`/`uv run` im Benutzerkontext laufen lassen.
- **CI-Job `desktop-windows`** (`90336b3`, windows-latest/x64): pnpm-Build,
  Sidecars aus dem Workspace bauen + `uv` vom Runner kopieren +
  resources-Platzhalter (beides gitignored; ohne sie scheitert schon
  `cargo check` am tauri-build-Skript — lokal nachgestellt). Dann
  `cargo test -p speccify-desktop`. Erster Lauf beim nächsten Push.
- **STATUS_ENTRYPOINT_NOT_FOUND war NIE VC-Redist** (Log von gestern
  korrigiert): dumpbin zeigte den Import `TaskDialogIndirect` — den
  exportiert nur comctl32 **v6**, und v6 kommt nur mit Common-Controls-
  Manifest. tauri-build embedded das Manifest nur in bin-Targets
  (`rustc-link-arg-bins`); Test-Exen starteten deshalb nicht. Erster
  Versuch `rustc-link-arg-tests` + Manifest (`a798b65`) scheiterte:
  cargo akzeptiert das nur mit Integrations-Test-Target und es deckt
  Lib-Unittests nicht ab. Lösung **`/DELAYLOAD:comctl32.dll`**
  (`50c0272` bzw. `07e296f`) — Tests rufen nie Dialoge, die App löst mit
  ihrem Manifest v6 wie bisher.
- Damit liefen die Tests erstmals wirklich auf Windows — **drei echte
  Bugs** (`50c0272`): PATH-Suche ohne PATHEXT (`git.exe` unauffindbar —
  betrifft Sidecar-Auflösung UND Doctor; jetzt `sidecar::find_in_dir`
  mit .exe/.cmd/.bat/.com), Backslash-Pfade nicht als explizit erkannt,
  Traversal-Guard ohne `has_root` (`/etc/passwd` ist auf Windows nicht
  `is_absolute`). Danach 21/22 grün (SYSTEM-Kontext).
- **PTY-Test**: hing (blockierendes `read` ohne wirksame Deadline) →
  Reader-Thread + `recv_timeout` (`966f932`, plus `drop(slave)` nach dem
  Spawn wie im echten `terminal_open`). ConPTY liefert im cargo-test-
  Harness trotzdem nichts — als SYSTEM **und** als interaktiver Benutzer
  (schtasks) reproduziert, während das App-Terminal mit demselben
  Codepfad nachweislich läuft. Ursache offen; der Test ist auf Windows
  jetzt `ignore` mit Begründung (`2b46458`), D16 bleibt E2E belegt.
- **Claude Code 2.1.247 in der VM** (`npm i -g`): im Projektfenster-
  Terminal per CDP gestartet — PowerShell blockt das npm-Shim
  `claude.ps1` (ExecutionPolicy), **`claude.cmd` startet** → Onboarding
  bis zum **Login-Prompt** (Screenshot). Login macht der BO; danach der
  „Fertig heißt"-Skill-Test. P3-Merker: Autostart auf Windows sollte
  `claude.cmd` bevorzugen.

## 2026-08-27 (Projektfenster P2 — die App läuft auf Windows)
- **Durchstich komplett in der Parallels-VM (Windows 11 ARM64), ohne die VM
  je anzufassen**: alles über den `speccify-parallels-mcp` (:8766, Allowlist
  erweitert: cmd/powershell/git/cargo/rustup/npm/pnpm/winget/where — BO hat
  die Freigabe pauschal erteilt), Diagnose über WebView2-CDP (:9222,
  `node`-Skripte in der VM), Sichtnachweis über `prlctl capture`,
  interaktive Starts über `schtasks /ru mhennemeyer /it` (prlctl exec läuft
  als SYSTEM; `--current-user` hängt).
- **Toolchain**: VS Build Tools (VCTools+ARM64+SDK) nach `C:\BuildTools`,
  LLVM 20 (woa64) für `ring`s clang-Zwang, pnpm 10, uv 0.12.0 ARM64 als
  Sidecar, VC-Redist ARM64 (Test-Binaries starteten sonst mit
  STATUS_ENTRYPOINT_NOT_FOUND). Git/Node/Rust (aarch64-msvc) waren schon da.
- **Drei echte Windows-Bugs gefunden und gefixt**: (1) `66fb7e6`
  Shell-Wahl `pwsh`/`powershell.exe` + `-l` nur auf Unix, `home_dir()` mit
  USERPROFILE-Fallback; (2) `25d000a` **`project_open` muss async sein** —
  synchroner Command blockiert auf Windows den Main-Thread beim
  Webview-Bau (wry#583), das Projektfenster blieb auf about:blank;
  (3) `ae0b75e` `\\?\`-Verbatim-Präfix von `canonicalize` abstreifen
  (Titel, Recent-Liste, Terminal-cwd).
- **Endzustand verifiziert**: Projektfenster auf Windows mit Pläne-Tab
  (2 aktive + Archiv 31), Skills-Tab (elf Skills), **Agent-Terminal =
  PowerShell über ConPTY, cwd `C:\work\speccify`, Autostart vorgetippt**
  (`whoami` → `mhennemeyer`). Screenshot im Termin; `cargo test` in der VM
  grün. Offen: CI (x64), D17 Junction, `claude` in der VM.
- **Arbeitsnotizen**: Repo-Klon vom Home-Share braucht
  `git config --global --add safe.directory '\\Mac\Home\...'`;
  `\\Mac\Home` zeigt nur Desktop/Documents/Downloads (Skript-Austausch über
  `~/Desktop/Work/vm-scripts/`); Rebuild erst nach `taskkill` (Exe-Lock);
  `%ERRORLEVEL%` nie in derselben cmd-Zeile.

## 2026-08-26 (Projektfenster P1 — Gerüst, Pläne-/Skills-Tab, Terminal im Projekt)
- **Neuer Plan [`plans/projektfenster.md`](./plans/projektfenster.md)**
  (parallel zu `skills-und-tools.md`, BO-Ausnahme): Projekte in eigenen
  Fenstern verwalten, Hauptziel Windows (iKanbanAi ist Swift/macOS-only).
  D14–D18 mit BO entschieden; **Composer entfällt** (D18, Rückbau in P3).
- **P1 geliefert**: `apps/desktop/src-tauri/src/project_cmd.rs` — Fenster je
  Projekt (`WebviewWindow`, Label `project-<hash>`, Registry Label→Wurzel,
  `project_current` statt URL-Zustand), Bestände nativ gelesen (D14):
  `.agent/plans/` + `archive/` (Frontmatter via `serde_yaml`),
  `.agent/skills/` + Herkunft aus `expansions.yaml`, `project_read_file` mit
  Traversal-Guard, Recent-Liste in `~/.speccify/recent-projects.json`
  (nicht in AppSettings — SettingsView-Roundtrip hätte sie geleert).
  `terminal_open` nimmt optional `cwd`/`autostart`; `ProjectShell` mit
  Drei-Bereiche-Layout, Pläne-/Skills-Tab (react-markdown), Tools/MCPs/
  Agent als P3-Platzhalter; Dashboard: Projekte-Tab ersetzt Composer-Tab.
  Capability-Fenster `["main", "project-*"]`.
- **Verifiziert**: cargo test 22 ok (4 neue), clippy/fmt clean, tsc + Vite
  grün; E2E per `tauri dev` + AX-Scripting (osascript) am eigenen Repo —
  Fenster öffnet, 2 aktive Pläne + Archiv (31), elf Skills mit
  Herkunfts-Banner, Terminal startet in der Projektwurzel, Autostart wird
  vorgetippt, Recent-Liste + Wiederöffnen + localStorage-Persistenz geprüft.
- **Gelernt**: AX-`click` fokussiert WKWebView-Inputs nicht — `set focused`
  + `keystroke` (echte Events, React sieht sie); AX-`set value` ginge an
  React vorbei. Fixture-Verzeichnisse in Rust-Tests je Test benennen
  (parallele Ausführung, gleiche PID).

## 2026-08-21 (T3 — Evaluate: `speccify tool check`)
- **`core/src/speccify_core/tool_check.py`**: Konformitätsläufer nach D7.
  Je Beispiel: Input als JSON auf stdin, stdout muss JSON sein und den
  erwarteten Output **abdecken** (Zusatzfelder erlaubt, fehlende/abweichende
  nicht; Listen längengleich, elementweise; `true` ≠ `1`), gegen das
  `outputs`-Schema validieren; bei `ok: true` Exit 0, bei `ok: false` ist der
  Exit-Code egal (beide Lesarten von D7 sind ehrlich). Crash → stderr ist das
  Detail; Timeout ist ein Fehler, kein Hänger. Start direkt wenn ausführbar,
  sonst Interpreter nach Endung (`.sh .py .js .ts .rb .pl .ps1`). cwd = Tool-
  Verzeichnis, damit `fixtures/…` neben der Implementierung liegen.
  Vorab-Stati: `not-implemented`, `not-applicable` (`platforms` passt nicht),
  `no-examples`, `missing-requirement` (`requires` nicht auf PATH), `invalid-spec`.
- **CLI `speccify tool check [NAMES] --platform --timeout --json`** (Typer-
  Subapp `tool`): schreibt den Status in `expansions.yaml` — alle Beispiele
  grün → `verified` + `checked: <Datum>`, sonst zurück auf `implemented`.
  Exit 1 bei Fehlschlag. `expand` setzt `verified` zurück, wenn sich der
  Spec-Hash geändert hat (der alte Vertrag zählt nicht für den neuen).
- **MCP `tool_check`** (13 Tools), Smoke erweitert. `gen_cli_docs.py` löst
  Typer-Gruppen auf (`tool check` → `cli/tool-check.md`).
- **Speccify-Skill v0.2.0**: Execute/Evaluate ausgeschrieben — mechanische
  Schicht (`tool check`), fachliche Schicht (Verify-Zeilen am Artefakt, nicht
  aus dem Gedächtnis), **Iterationsregel** (Gegenbeweise suchen; keine ⇒ `ok`;
  gefunden ⇒ Adaptation → Schritt 2, Execution → Schritt 3; drei Iterationen
  ohne Fortschritt ⇒ Skill ist falsch, Schritt 5), **Spur-Format** für `log.md`
  (`### Datum · Skill Version · iteration N · ok|open|abandoned`, dann tools/
  tried/found/fixed). Zwei neue Pitfalls.
- **Dogfooding-Befund**: der Versionssprung des Speccify-Skills auf 0.2.0
  brach `^0.1` in `speccify.yaml` — `lock` hat es korrekt verweigert;
  Constraint auf `^0.2`, `lock`+`expand` → `.agent/skills/speccify` updated,
  `## In this project` blieb. `tool check` im Repo: 3× `not-implemented`
  (Implementierungen sind Aufgabe von M2).
- **Verifikation**: 215 Pytest (+20: 14 Läufer, 5 CLI, 1 MCP), mypy 39
  Dateien, ruff check+format, MCP-Smoke, CLI-Doku regeneriert, `check skills/
  --links` 11/11, `verify` grün.

## 2026-08-21 (T2 — Expand nach .agent/)
- **Symlink-Probe** in der laufenden Claude-Code-Session: `.claude/skills`
  entfernt, `.agent/skills` angelegt, Symlink gesetzt → alle zehn Skills sofort
  wieder gelistet. `speccify link` verlinkt also, kopiert nicht.
- **`expansion.py`**: `expand_skill` (rein) streift `speccify.*`, biegt
  `](tools/` auf `](../../tools/` um, hängt `## In this project` an und trägt
  eine vorhandene Sektion unverändert weiter; `Expansions` (YAML-Nachweis mit
  Skill-Herkunft/Hash/Datum und Tool-Status je Plattform);
  `implementation_for` findet `<platform>.<ext>`.
- **CLI**: `expand` (Queue über den uses-Baum aus dem Lockfile; unchanged/
  updated/created; Assets wandern mit, `tools/` wird projektweit; Aufgabenliste
  mit Platzhaltern und Tools), `link`, `init` (+ `.gitignore`-Zeile + Link),
  `pull` → `.agent/speccify/cache`, `verify` + `expansion_status`.
- **MCP**: `expand` (12 Tools), `pull`-Default auf den Cache. Smoke angepasst.
- **`check`** kennt die Projektform (`.agent/skills/<name>`): Links auf
  Geschwister/`../../tools/` sind dort kein Befund; sonst weiterhin Fehler.
- **Speccify-Skill** `skills/speccify/SKILL.md` (v0.1.0): Suchen → Expand →
  Execute → Evaluate → Zurückgeben, mit Verify-Zeilen und Pitfalls.
- **Dogfooding**: `speccify.yaml` + `speccify.lock` im Repo-Root (elf Skills),
  `.agent/skills/` expandiert und committet, `.agent/tools/` mit drei Specs,
  `.claude/skills` Symlink im Git. iCloud hat während der Arbeit dreimal
  `reference 2.sh` erzeugt (gelöscht; ein Lock mit Konfliktkopie ergab Drift).
- **Verifikation**: 195 Pytest (+13), mypy 37 Dateien, ruff, `check skills/`
  11/11 und `.agent/skills` 11/11 sauber, `verify` grün, CLI-Doku regeneriert
  (expand/link), Marketing-Build 23 Seiten, CI-Smoke um expand erweitert.

## 2026-08-21 (T1 — Tool-Spec-Format)
- **`core/src/speccify_core/tool.py`**: `TOOL.md` = Frontmatter (`name`,
  `description`, `inputs`/`outputs` als JSON Schema, `effects`, `requires`,
  `runtime`, `platforms`) + freier Body; `## Examples` mit `### Fall` und
  `input:`/`output:`-JSON-Zeilen. `validate_tool` prüft Schema-Gültigkeit und
  jedes Beispiel gegen beide Schemas — ein lügendes Beispiel ist ein Fehler.
- **`skill_check`**: `load_tools`/`tools_from_bundle`/`check_tools`; Befunde
  unter `tools/<name>/…`. Neu: Warnung für jedes Skript in `assets|scripts|
  references` ohne gleichnamigen Spec — der Grund, warum es Specs gibt.
  `tools` ist reservierte Sektion; `BUNDLE_DIRS` (= `ASSET_DIRS` + `tools`)
  für Git-Quellen.
- **Drei Specs**: `verify-signatures` (notarize), `verify-stream`
  (sandboxed-exec), `build-libgit2`. Skripte nach `tools/<name>/reference.sh`
  verschoben; jede `SKILL.md` hat einen `## Tools`-Abschnitt mit Link.
- **Lesen**: `speccify show` + `skill_get` listen Tools flach; MCP `tool_get`
  liefert den ganzen Vertrag (11 Tools jetzt); Viewer-Backend `tools`,
  Viewer „Tools"-Karte (Chips öffnen die `TOOL.md` als Datei).
- **Verifikation**: 182 Pytest (+16), mypy 34 Dateien, ruff check+format,
  Playwright 1/1, `check`/`lint` 10/10 sauber, Viewer-Build, MCP-Smoke über
  die 11 Tools. Pfad-Umstellung in CI, Backend-/CLI-Tests, E2E-Spec, Doku.
- **Nicht getan**: `docs/playbooks.md`/Marketing erzählen weiter Playbooks
  (bekanntes offenes Ende); markdownlint-Befund in `storekit2-…` ist alt und
  außerhalb der Globs.

## 2026-08-21 (Plan: BO-Entscheide eingearbeitet)
- **`.agent/` ist das Zuhause** (D8): `.agent/skills/` = normale, expandierte
  Skills; `.agent/tools/` = Implementierungen je Plattform, alle committet;
  `.claude/skills` verweist nur (Symlink, Probe in T2). Herkunft in
  `.agent/speccify/expansions.yaml`, Upstream-Cache gitignored.
- **Expand = Normalisierung**: `uses`-Baum wird zu mehreren normalen Skills,
  `speccify.*` wird abgestreift, Projektspezifisches nur ergänzt (D12).
- JSON Schema für Inputs/Outputs bestätigt (D10); Exec-MCP raus (D13) — er
  ist für gesandboxte Clients, der Agent im Terminal ruft Tools direkt auf.
- Pristin/expandiert-Unterscheidung aus dem ersten Entwurf entfällt.

## 2026-08-20 (Plan: Skills und Tools — Dreischritt vor dem Testlauf)
- **Neuer aktiver Plan** [`plans/skills-und-tools.md`](./plans/skills-und-tools.md);
  `skills-als-format.md` archiviert (`lifecycle: superseded`), Produktdefinition
  gilt weiter.
- **BO-Auslöser**: Teilen fertiger Tools scheitert an Plattform/Version.
  Antwort: **Tool-Specs** im Skill (`tools/<name>/TOOL.md`), Agent
  programmiert vor Ort aus. Benutzung als **Expand → Execute → Evaluate**,
  iterativ; Choreografie im Speccify-Skill, nicht im Code (D11).
- **Entscheidungsvorschläge D7–D11**: stdin/stdout-JSON als einzige
  vorgeschriebene Form; expandierte Skills werden committet, pristine nicht;
  Tools liegen im Skill; Beispiele sind der Vertrag.
- **Reihenfolge**: T1 → T2 → T3 → M2. M2 (Neubau eines alten Projekts) bleibt
  der erste echte Testlauf, jetzt mit Dreischritt.
- Kein Code geändert. `status.md` und `agent.md` auf den neuen Plan gezogen.

## 2026-05-18 (Phase 1c Step 6 — Wrap-up + Master-Plan-Sync)
- **Step 6 abgeschlossen, Phase 1c damit fertig.** Reine Doku-/Plan-
  Synchronisation, kein Code-Change am Server.
- **`speccify-plan.md`** (Master-Plan): Eintrag „Phase 1c" von „nächster
  Schritt" auf „abgeschlossen 2026-05-16" umgestellt und inline um den
  öffentlichen MCP-Tool-Vertrag erweitert (Tools mit Signaturen, `verify`
  liefert strukturiert `{ok, problems}`, Resources `speccify://manifest|
  lockfile` + Template `spec://{scope}/{name}@{version}`, Prompt `add-
  spec`, Defaults `--offline` + `SPECCIFY_CACHE_DIR`, Project-Root als
  Startup-Argument, Smoke-Skript + CI-Step). Damit ist der Vertrag jetzt
  im Master-Plan dokumentiert, nicht nur im Phasen-Plan. Phase 1d steht
  als „nächster Schritt" markiert (Browser-Playground).
- **`AGENTS.md`** „Aktuelle Phase" auf „Phase 1c abgeschlossen (Tag-
  Vorschlag `v0.3.0-phase-1c`), nächste Phase 1d (Browser-Playground)"
  umgestellt; Verweise konsolidiert (Phase-1c-Plan als aktiv-für-Wrap-
  up, Phase 1a/1b-Tags zusammengefasst).
- **`.agent/plans/phase-1c-mcp-server.md`**: Step 6 viermal abgehakt;
  Front-Matter `isActive: false` (Plan abgeschlossen).
- **`.agent/status.md`**: Meta-Block auf „Phase 1c abgeschlossen
  (2026-05-18)" umgestellt, Schritt-6-Eintrag in der „Nächste Schritte"-
  Liste abgehakt, „nächster Schritt" auf Phase-1d-Plan-Entwurf nach
  User-Tag-Setzung.
- **Tag-Vorschlag `v0.3.0-phase-1c`**: bewusst **nicht** selbst gesetzt
  (vgl. `.agent/rules.md`: Tags sind User-Aktion, ebenso wie Commits).
  Empfohlener Annotated-Tag-Schnitt nach dem nächsten User-Commit:
  ```bash
  git tag -a v0.3.0-phase-1c -m "Phase 1c: speccify-mcp (stdio) — tools/resources/prompts + offline smoke"
  ```
- **Verifikation**: `uv run pytest` → **174 grün**; `uv run ruff check
  .` + `uv run ruff format --check .` clean (60 Dateien). Keine Code-
  Änderungen, daher keine `.venv`-Side-Quest.
- **Nächster Schritt**: Phase-1d-Plan-Entwurf (`.agent/plans/phase-1d-
  playground.md`) — Browser-Playground, der dieselbe Codegen-Pipeline
  (React-LLM + Replay-Cache) im Web ausführt. Vor Plan-Schreiben mit
  User abklären: Hosting-Stack (Next.js? Vite? SvelteKit?), Pyodide vs.
  Server-Side-Codegen, und ob der Playground den Replay-Cache aus dem
  Repo bündelt oder ein eigenes Cache-Layout bekommt.

## 2026-05-16 (Phase 1c Step 5 — CI-Smoke `speccify-mcp` (stdio, offline) + Doku)
- **Step 5 abgeschlossen.** Neues Skript `scripts/mcp_smoke.py` ist
  der einzige Smoke-Aufruf für den MCP-Server und wird gleichzeitig
  in CI (`.github/workflows/ci.yml`, Step `speccify-mcp smoke (stdio,
  offline)`) und im Repo-Pytest (`mcp/tests/test_stdio_smoke.py`)
  benutzt — derselbe Code, zwei Trigger.
- **Was das Skript prüft** (alles über echtes stdio, kein In-Process-
  Shortcut):
  1. Kopiert `example-project/` + `registry-fixtures/` nach `tmp`
     (Manifest verweist relativ auf `../registry-fixtures`).
  2. Startet `python -m speccify_mcp.cli --project <tmp/example-
     project>` als Subprocess via `mcp.client.stdio.stdio_client`
     mit `mcp.ClientSession`. Console-Script `speccify-mcp` wäre in
     CI brüchig (Pfad/Venv), deshalb der explizite `-m`-Aufruf mit
     `sys.executable`.
  3. `session.initialize()` (MCP-Handshake).
  4. `tools/list` muss exakt `{lint,lock,pull,render,resolve,verify}`
     liefern (sichert den Phase-1c-Vertrag).
  5. `tools/call render` für `@org/button` → `structuredContent.files`
     enthält mindestens eine Datei mit `export`, `generator_pin.kind
     == "llm"`. Damit ist der Replay-Cache-Path über stdio verifiziert.
  6. `resources/read speccify://manifest` muss `schema_version: 1` +
     `target: react` enthalten.
- **Offline-Garantie**: `SPECCIFY_CACHE_DIR` wird auf den eingecheckten
  Repo-Cache (`tests/fixtures/llm-cache/`) gepinnt, **und**
  `ANTHROPIC_API_KEY` / `AWS_*` werden aus der Env hart entfernt
  bevor der Subprocess startet. Damit produziert auch eine
  Dev-Maschine mit gültigen Bedrock-Creds reproducible Smokes.
- **Pytest-Wrapper** (`mcp/tests/test_stdio_smoke.py`): ruft das
  Skript via `subprocess.run([sys.executable, …])` und prüft
  Exit-Code 0 + `"speccify-mcp stdio smoke: OK"` auf stderr. Bewusst
  dünn — Detail-Assertions leben im Skript, damit CI-Logs sprechen.
- **Doku**: `mcp/README.md` neu geschrieben (war Phase-0-Stub):
  Installation/Start, Env-Vars, Tools-/Resources-/Prompts-Tabellen,
  `verify`-Vertrag (Drift ist Antwort, kein Error), Client-Configs für
  Claude Code/Junie/Cursor inkl. `uv`-Fallback, Smoke-Aufruf.
  Top-Level-`README.md` hat einen neuen Abschnitt „MCP-Server
  (`speccify-mcp`)" mit Config-Snippet + Verweis auf `mcp/README.md`;
  Phase-Liste und Status-Block auf Phase 1c aktualisiert.
- **CI**: Step `speccify-mcp smoke (stdio, offline)` als Letztes —
  `uv run python scripts/mcp_smoke.py`. Lokal verifiziert.
- **Verifikation**: `uv run pytest` → **174 grün** (173 + 1 neu;
  `test_mcp_stdio_smoke_offline`), `uv run ruff check .` + `uv run
  ruff format --check .` clean. Side-Quest: nach Erstellen der neuen
  Skript/Test-Dateien `uv sync --all-packages --reinstall` einmalig
  nötig (bekannte `_editable_impl_*.pth`-Falle).
- **Bewusst weggelassen**: Kein Cross-Consistency CLI↔MCP-stdio-
  Subprocess-Test — der direkte Funktions-Cross-Consistency in
  `test_tools_write.py::test_cli_and_mcp_pull_produce_identical_
  output` deckt Datendrift ab; der stdio-Test deckt Protokoll-Drift
  ab. Doppel würde nur die CI-Zeit verdoppeln.
- **Nächster Schritt** (Step 6 — Wrap-up): `speccify-plan.md` Phase
  1c als abgeschlossen markieren + MCP-Tool-Vertrag inline
  dokumentieren; `AGENTS.md` „Aktuelle Phase" auf 1d umstellen;
  Tag-Vorschlag `v0.3.0-phase-1c` an User (nicht selbst setzen).

## 2026-05-16 (Phase 1c Step 4 — Resources `speccify://manifest|lockfile` + `spec://...` + Prompt `add-spec`)
- **Step 4 abgeschlossen.** Zwei neue Module unter `mcp/src/speccify_mcp/`:
  - `resources.py`: `register_resources(server, config)` verdrahtet drei
    Read-only Resources über `@server.resource(uri)`:
    - `speccify://manifest` → liest `<project_root>/speccify.yaml` als
      UTF-8-YAML (mime_type `application/yaml`). Fehlende Datei →
      `FileNotFoundError`, FastMCP wickelt → `ResourceError`.
    - `speccify://lockfile` → liest `<project_root>/speccify.lock`.
      **Fehlt das Lockfile, geben wir bewusst keinen Fehler zurück**,
      sondern einen kurzen YAML-Kommentar-Hinweis (`# No speccify.lock
      … Call the lock tool …`). Begründung: „Lockfile fehlt" ist ein
      normaler Workflow-Zustand (frisch initialisiertes Projekt).
    - `spec://{scope}/{name}@{version}` als Template-Resource — Lazy
      via `WorkspaceContext.load` + `LocalRegistry.fetch` →
      `Spec.raw_bytes.decode("utf-8")`. Manifest wird pro Call neu
      geladen, damit Änderungen an `registry.path` ohne Neustart
      sichtbar sind (kein Caching, vgl. Decision 5).
  - `prompts.py`: Ein einziger Prompt `add-spec(spec_ref, out_dir=
    "./src/components")` rendert eine vierstufige Anleitung (resolve →
    lock → pull → verify) und nennt den Projekt-Root. Bewusst klein —
    Prompt-Form lernen wir in Phase 1d.
- **`server.py`**: `build_server` ruft jetzt zusätzlich
  `register_resources` und `register_prompts`. Die Imports sind lazy
  innerhalb von `build_server`, weil `resources.py`/`prompts.py`
  ihrerseits `ServerConfig` aus `server.py` importieren — ohne Lazy-
  Import gäbe das einen Modul-Zyklus.
- **Tests** (`mcp/tests/test_resources_prompts.py`, 8 Stück):
  manifest happy + missing (→ `ResourceError`); lockfile happy +
  missing (→ Hint-Text, kein Fehler); spec happy + unbekannte
  Version (FastMCP wickelt `RegistryError` in `ValueError` während
  der Template-Instanziierung); prompt happy + Custom-`out_dir`.
  `test_server_skeleton.py` aktualisiert: `resources/list` enthält 2
  fixe Resources (`speccify://manifest|lockfile`), `list_resource_
  templates` enthält das `spec://{scope}/{name}@{version}`-Template,
  `prompts/list` enthält `add-spec`.
- **Verifikation**: `uv run pytest` → **173 grün** (165 + 8 neu);
  `uv run ruff check .` + `uv run ruff format --check .` clean
  (57 Dateien). Side-Quest: nach Hinzufügen der neuen Module
  einmalig `uv sync --all-packages --reinstall` nötig (bekannte
  `_editable_impl_*.pth`-Falle).
- **Bewusst weggelassen**: Kein eigenes Tool/Resource für „liste alle
  verfügbaren Specs in der Registry" — `LocalRegistry` hat noch
  keinen Index (Phase 2). Agents nutzen `spec://...` mit bekannten
  Refs.
- **Nächster Schritt** (Step 5): CI-Smoke-Step `speccify-mcp` (stdio,
  offline) — Subprocess startet den Server, fährt MCP-Handshake,
  ruft `tools/list` + `tools/call render @org/button` + liest
  `speccify://manifest` und vergleicht gegen erwartete Bytes. Plus
  README/`mcp/README.md`-Doku mit Junie-/Claude-Code-Config-Snippet.

## 2026-05-16 (Phase 1c Step 3 — Write-Tools `lock`/`pull`/`verify` + Cross-Consistency CLI ↔ MCP)
- **Step 3 abgeschlossen.** Drei neue Adapter-Module unter
  `mcp/src/speccify_mcp/tools/`:
  - `lock.py`: `run_lock(project_root, registry_path?)` → `LockResult{target,
    lockfile_path, entries: [{spec_id, version, spec_sha256}]}`. Nutzt
    `Resolver` + `build_lockfile` und schreibt `<project_root>/speccify.lock`
    (Pendant zu `speccify lock`).
  - `pull.py`: `run_pull(project_root, out_dir, target?, registry_path?,
    offline=True, cache_dir?)` → `PullResult{target, out_dir, lockfile_path,
    files_written}`. Spiegelt `speccify pull` 1:1: lädt Lockfile, fetcht jede
    Spec, ruft `render_for_target` mit `ReplayCacheClient`, schreibt
    Output-Dateien atomar nach `out_dir`, aktualisiert `generated_files_sha256`
    + `LlmGeneratorPin` (`provider=bedrock`, `model`, `prompt_version`, `seed`,
    `cache_key=sha256:<digest>`) im Lockfile.
  - `verify.py`: `run_verify(project_root, out_dir, registry_path?,
    offline=True, cache_dir?)` → `VerifyResult{ok, problems}`. Fehler werden
    **strukturiert** im Result gemeldet, nicht als MCP-Exception — Agents
    bekommen `ok=False` + Problemliste statt `isError`. Drift-Checks 1:1 wie
    in `cli.commands.verify.run_verify` (Target/Versions/Spec-Hash/Generator-
    Pin/Re-Render/Disk).
- **`tools/_workspace.py`**: Eigener `WorkspaceContext` + `build_replay_client`
  + `resolve_cache_dir` ohne `speccify-cli`-Dep (Layering: MCP hängt nur an
  `speccify-core`). Repo-lokaler Default-Cache `tests/fixtures/llm-cache`,
  Env-Override `SPECCIFY_CACHE_DIR`. `render.py` aus Step 2 wird in einem
  Follow-up entkoppelt (heute zwei kleine Duplikate, funktional identisch).
- **`server.py`**: Neue Funktion `_register_write_tools(server, config)` mit
  drei `@server.tool()`-Wrappern (`lock`/`pull`/`verify`), englische
  `description`-Strings, Project-Root implizit aus `ServerConfig`, optionale
  Overrides für `out_dir`/`target`/`registry_path`/`offline`/`cache_dir` pro
  Call. `tools/__init__.py` re-exportiert die neuen `run_*`-Funktionen und
  Dataclasses.
- **Tests** (`mcp/tests/test_tools_write.py`, 10 Stück):
  - `lock`: happy path (Lockfile geschrieben, Target react, sha256-Präfix);
    fehlendes Manifest → `FileNotFoundError`.
  - `pull`: happy path (alle Dateien auf Disk, Lockfile mit `generated_files
    _sha256`); fehlendes Lockfile → `LockfileError`; Target-Mismatch →
    `LockfileError`; offline + leerer Cache → `CacheMissError`.
  - `verify`: grün nach `pull`; Disk-Drift (TSX manipuliert) → `ok=False` mit
    "Disk-Drift"-Eintrag; fehlendes Lockfile → `ok=False` mit
    "Kein Lockfile"-Eintrag (strukturiert, **kein** Raise).
  - **Cross-Consistency CLI ↔ MCP**: `test_cli_and_mcp_pull_produce_identical
    _output` ruft `speccify_cli.commands.pull.run_pull` und
    `speccify_mcp.tools.run_pull` gegen je eine eigene `example-project/`-Kopie
    und vergleicht **alle Output-Bytes + speccify.lock byte-identisch**. Damit
    ist Decision 4 ("Tools spiegeln CLI 1:1") als Test verankert — jede
    künftige Refaktorierung muss diese Invariante halten.
- **`test_server_skeleton.py`**: Test umbenannt auf
  `test_tools_list_contains_step2_and_step3_tools`; erwartet jetzt
  `['lint','lock','pull','render','resolve','verify']`. Resources/Prompts
  bleiben leer (Step 4).
- **Verifikation**: `uv run pytest` → **165 grün** (155 + 10 neu);
  `uv run ruff check .` + `uv run ruff format --check .` clean (54 Dateien
  nach Format-Run). Side-Quest: `uv sync --all-packages --reinstall` einmalig
  nötig (bekannte `_editable_impl_*.pth`-Falle, identisch zu Steps 0/1/2).
- **Bewusst weggelassen**:
  - **Kein** `subprocess`-Cross-Test gegen die `speccify`-Binary — der
    direkte `cli.run_pull`-Aufruf deckt dieselbe Codepath-Drift ab und ist
    ~10× schneller. Subprocess-Roundtrip kommt in Step 5 (CI-Smoke) als
    end-to-end-Test über stdio, dort gehört es hin.
  - **Kein** Wrap von `verify`-Fehlern in MCP-Exceptions: `verify` darf
    `ok=False` zurückgeben, ohne das Tool selbst als „fehlgeschlagen" zu
    markieren — sonst kann der Agent die `problems`-Liste nicht lesen.
- **Nächster Schritt** (Step 4): Resources `spec://<scope>/<name>@<version>`
  gegen `LocalRegistry`, `speccify://manifest` + `speccify://lockfile` für
  das Startup-Projekt, plus Prompt `add-spec` (Vorlage für Agents).

## 2026-05-15 (Phase 1c Step 2 — Read-only Tools `resolve`/`lint`/`render`)
- **Step 2 abgeschlossen.** Neue Modul-Hierarchie unter
  `mcp/src/speccify_mcp/tools/`:
  - `resolve.py`: `run_resolve(project_root, manifest_path?, registry_path?)`
    → `ResolveResult{target, resolutions: [{spec_id, version, spec_sha256}]}`
    via `ProjectManifest` + `LocalRegistry` + `Resolver`. Schreibt nichts
    (Pendant zu `speccify lock` ohne Lockfile-Write).
  - `lint.py`: `run_lint(spec_path, schema_path?)` → `LintResult{spec_path,
    ok, skipped, issues}` über `SpecLoader` + `SchemaValidator`. Projekt-
    Manifeste (kein `kind`) werden wie in der CLI als `skipped=True`
    durchgereicht.
  - `render.py`: `run_render(project_root, spec_id, target?, offline=True,
    cache_dir?)` → `RenderResult{spec_id, target, files: {path: utf8-text},
    generator_pin}`. Lädt Lockfile, fetcht Spec aus Registry, ruft
    `render_for_target` mit `ReplayCacheClient` (Default-Cache
    `tests/fixtures/llm-cache`, Env-Override `SPECCIFY_CACHE_DIR`,
    `cache_dir`-Override pro Call). Target-Drift gegen Lockfile-Target und
    fehlendes Lockfile werden als `LockfileError` signalisiert; unbekannte
    `spec_id` als `LookupError`.
- **`server.py`**: `_register_readonly_tools(server, config)` registriert
  die drei Tools über `FastMCP.tool()` mit englischen Descriptions. Bytes
  werden als utf-8-Text in `{path: text}` ausgeliefert (TSX/Markdown sind
  beide Text; Base64 bleibt späteren Targets vorbehalten).
- **Tests** (`mcp/tests/test_tools_readonly.py`, 12 Stück): `resolve`
  happy + fehlendes Manifest; `lint` valide Spec + Projekt-Manifest-Skip
  + Schema-Issues + fehlende Datei + invalides YAML; `render` happy path
  für `@org/button` (TSX + `generator_pin.kind=llm`), unbekannte spec_id,
  Target-Drift, fehlendes Lockfile, offline Cache-Miss. Test-Helper
  kopiert `example-project/` **und** `registry-fixtures/` nach
  `tmp_path`, weil `registry.path: ../registry-fixtures` aus dem
  Manifest sonst ins Leere zeigt — kleine, aber wichtige Erkenntnis für
  spätere Subprocess-Integrationstests in Step 3.
- **`test_server_skeleton.py`**: Test umgebaut von "leeres `tools/list`"
  auf "exakt `['lint','render','resolve']`". Resources/Prompts bleiben
  leer (Step 4).
- **Verifikation**: `uv run pytest` → **155 grün** (143 + 12 neu);
  `uv run ruff check .` + `uv run ruff format --check .` clean
  (49 Dateien). Side-Quest: nach Hinzufügen des `tools/`-Unterpakets
  einmalig `uv sync --all-packages --reinstall` nötig (bekannte
  `_editable_impl_*.pth`-Falle, vgl. Step 5c / Step 0).
- **Nächster Schritt** (Step 3): Write-Tools `lock`, `pull`, `verify`
  als dünne Adapter über `speccify_cli.commands.lock.run_lock` /
  `pull.run_pull` / `verify.run_verify` (oder direkt `speccify_core`),
  plus Cross-Consistency-Test CLI ↔ MCP (gleiche Inputs → byte-identischer
  `out/`-Inhalt).

## 2026-05-15 (Phase 1c Step 1 — Server-Skeleton + leeres `tools/list`)
- **Step 1 abgeschlossen.** Skeleton-Module unter
  `mcp/src/speccify_mcp/` angelegt:
  - `server.py`: `ServerConfig` (frozen dataclass mit `project_root`)
    + `build_server(config)` → `FastMCP(name="speccify-mcp",
    instructions=…)` **ohne** registrierte Tools/Resources/Prompts.
    Bewusst minimal — Tools kommen erst in Step 2/3.
  - `cli.py`: `build_parser`, `resolve_project_root` (CLI > Env
    `SPECCIFY_PROJECT_ROOT` > CWD), `configure_logging` (stderr, weil
    stdout für MCP-stdio-Frames reserviert ist), `main` ruft
    `server.run(transport="stdio")`.
  - `__init__.py` re-exportiert `main`, `build_server`, `ServerConfig`,
    `SERVER_NAME`.
- **`mcp/pyproject.toml`**: `[project.scripts] speccify-mcp =
  "speccify_mcp.cli:main"` ergänzt. `uv sync --all-packages` baut
  `speccify-mcp` neu; danach 1× `--reinstall` nötig (bekannte
  Editable-`.pth`-Artefakt-Falle).
- **Tests** (`mcp/tests/test_server_skeleton.py`, 9 Stück): Server
  benannt, `tools/resources/prompts list` jeweils leer
  (`asyncio.run(server.list_*())` gegen die `FastMCP`-API); Parser-
  Defaults und `--project`/`--log-level`-Parsing; `resolve_project_root`
  Priorität CLI > Env > CWD (jeweils via `monkeypatch.setenv`/`chdir`).
- **Verifikation**: `uv run pytest` → **143 grün** (134 + 9 neu);
  `uv run ruff check .` + `uv run ruff format --check .` clean
  (44 Dateien). MCP-SDK-API-Erkundung: `FastMCP.list_tools()`/
  `list_resources()`/`list_prompts()` sind Coroutinen und liefern bei
  einem leer registrierten Server `[]`.
- **Bewusst weggelassen**: kein expliziter Health-Check-Tool — MCPs
  Server-Liveness wird durch das stdio-Handshake nachgewiesen, ein
  zusätzliches Tool würde den „Tools spiegeln CLI 1:1"-Vertrag aus
  Decision 4 aufweichen. Falls Step 5 (CI-Smoke) ein eigenständiges
  Liveness-Signal braucht, ziehen wir `tools/list` heran.
- **Nächster Schritt** (Step 2): Read-only Tools `resolve`, `lint`,
  `render` als dünne Adapter über `speccify_core` mit Happy- und
  Fehlerpfad-Tests + Integrationstest gegen `example-project/` offline.

## 2026-05-15 (Phase 1c Step 0 — `mcp[cli]`-SDK gepinnt)
- **Step 0 abgeschlossen.** Aktuelle Latest-Version auf PyPI ist
  `mcp 1.27.1` (mit Extras `cli`, `rich`, `ws`; `requires-python>=3.10`).
- **`mcp/pyproject.toml`**: `dependencies` um `mcp[cli]>=1.27.1,<2.0`
  erweitert (kompatibler Major-Korridor laut SemVer; harte Untergrenze
  auf der aktuell auf PyPI verfügbaren Version).
- **`uv sync --all-packages`**: 23 neue Pakete installiert (`mcp==1.27.1`
  + Transitive: `anyio`, `httpx`, `httpx-sse`, `pydantic` 2.13,
  `pydantic-settings`, `python-multipart`, `sse-starlette`, `starlette`,
  `uvicorn`, …). `uv.lock` aktualisiert.
- **Side-Quest**: `.venv` hatte erneut präexistierende Editable-Pakete
  ohne abschließendes Newline in den `_editable_impl_*.pth`-Dateien
  (klassisches macOS/iCloud-Artefakt, vgl. Step 5c). Folge: `speccify_cli`/
  `speccify_mcp` waren nach `uv sync` nicht mehr importierbar, obwohl
  `uv pip list` sie als installiert anzeigte. Fix: `uv sync
  --all-packages --reinstall`. Kein Repo-Change nötig, nur als Hinweis.
- **Verifikation**: `uv run pytest` → **134 grün**; `uv run ruff check .`
  + `uv run ruff format --check .` clean.
- **Nächster Schritt** (Step 1): Server-Skeleton in
  `mcp/src/speccify_mcp/` anlegen (`cli.py` mit `--project`/`--log-level`,
  `server.py` mit leerem Tool-Registry + Health-Check), Unit-Test:
  Server instanziierbar und `tools/list` antwortet leer.

## 2026-05-13 (Tags gesetzt + Phase-1c-Plan angelegt)
- **Tags lokal gesetzt** (User-Freigabe in diesem Prompt: „Bitte setze
  den Tag und mache ausnahmsweise die aktionen im Git"):
  - `v0.1.0-phase-1a` annotated → `d28cb33` ("Complete Phase 1a:
    Finalize Codegen and CLI Enhancements"), Message: "Phase 1a:
    Resolver + Lockfile + Stub-Codegen + add/lock/pull/verify".
  - `v0.2.0-phase-1b` annotated → `8c90511` ("Complete Phase 1b:
    Finalize Step 6 with Master-Plan Sync"), Message: "Phase 1b:
    React-LLM-Codegen + speccify init + Replay-Cache + pull/verify
    --offline + CI-E2E".
  - `git remote -v` ist leer → kein Push möglich. User kann später bei
    Bedarf `git remote add` + `git push --tags` ausführen.
- **Phase 1c gestartet — Phasen-Plan geschrieben**:
  `.agent/plans/phase-1c-mcp-server.md` mit Scope (MCP-Server
  `speccify-mcp`, offizielles `mcp[cli]`-SDK, stdio-only, 6 Tools
  spiegeln CLI 1:1: `resolve`/`lock`/`render`/`pull`/`verify`/`lint`,
  plus Resources `spec://`+`speccify://manifest|lockfile` und Prompt
  `add-spec`), Technical Design (Modul-Layout `mcp/src/speccify_mcp/`
  mit `cli.py`/`server.py`/`tools/`/`resources.py`/`prompts.py`,
  Replay-Cache bleibt in `speccify_core`, MCP ist stateless),
  Implementation Plan (Steps 0–6: SDK pinnen → Skeleton → Read-Tools →
  Write-Tools + Cross-Consistency CLI↔MCP → Resources/Prompts →
  CI-Smoke+Doku → Wrap-up). Tag-Vorschlag `v0.3.0-phase-1c`.
- **Status-Sync**: `.agent/status.md` Meta-Phase auf "Phase 1c
  gestartet" gesetzt; Tag-Setzung und Plan-Anlage als `[x]` markiert;
  neue `[ ]`-Bullets für Steps 0–6.
- **Nächster Schritt**: Phase 1c Step 0 — `mcp[cli]`-Version
  recherchieren und in `mcp/pyproject.toml` pinnen.

## 2026-05-13 (Phase 1b Step 6 — Master-Plan-Sync + Phase-1b-Abschluss)
- **Step 6 abgeschlossen, Phase 1b damit komplett.** Sync der Plan-Dokumente
  nach dem Step-5c-Commit; keine Code-Änderungen.
- **`.agent/plans/archive/speccify-plan.md`**: Phase 1b in der Sub-Spike-Liste auf
  "abgeschlossen 2026-05-13" gesetzt; React-LLM-Strategie (Bedrock-Modell
  `bedrock/eu.anthropic.claude-opus-4-7` via `converse`, Reproduzierbarkeit
  durch Replay-Cache mit Cache-Key über `spec_sha256 + target + model +
  prompt_version + seed`, Lockfile-Generator-Pin um `kind: llm` erweitert,
  `pull`/`verify --offline/--cache-dir`, CI-E2E gegen `tests/fixtures/llm-cache/`,
  `scripts/record_llm_cache.py` als Maintainer-Tool) im Plan inline dokumentiert.
  Phase 1c als "nächster Schritt" markiert. Tag-Vorschlag `v0.2.0-phase-1b`
  im Plan vermerkt.
- **`AGENTS.md`** "Aktuelle Phase" auf "Phase 1b abgeschlossen, Phase 1c
  als nächste" umgestellt; Tag-Vorschläge `v0.2.0-phase-1b` und optional
  `v0.1.0-phase-1a` aufgeführt.
- **`.agent/plans/phase-1b-react-codegen.md`**: Sub-Step 5c und Step 6
  abgehakt (drei `[x]`-Bullets unter Step 6 für Plan-/AGENTS-/Sync-Arbeit;
  Tag-Bullet bewusst `[ ]`, da User-Action).
- **`.agent/status.md`**: Meta-Phase auf "Phase 1b abgeschlossen" gesetzt;
  Step-6-Bullet als `[x]` markiert; offene `[ ]`-Punkte: User-Tag-Setzung
  `v0.2.0-phase-1b`, optional `v0.1.0-phase-1a`, Phase-1c-Plan schreiben.
- **Verifikation**: `uv run pytest` → 134 grün, `uv run ruff check .` und
  `uv run ruff format --check .` clean (Plan-Sync ist Doku-only, kein
  Code-Drift erwartet).
- **Tag-Vorschlag an User**: `git tag -a v0.2.0-phase-1b -m "Phase 1b:
  React-LLM-Codegen + speccify init + Replay-Cache + pull/verify --offline + CI-E2E"`
  (bewusst nicht selbst gesetzt — `rules.md` "Ein Prompt = ein Commit",
  Tagging ist User-Entscheidung).
- **Nächster Schritt**: Phasen-Plan `phase-1c-mcp-server.md` skizzieren
  (MCP-Server, der `speccify_core` ans Protokoll bindet: `resolve`,
  `search`, `render`, `validate`, `lock`, `verify`).

## 2026-05-13 (Phase 1b Step 5c — CI-E2E-Smoke + README-Doku)
- **Step 5c abgeschlossen.** CI deckt jetzt End-to-End beide Pfade ab:
  bestehendes `example-project/` (`lock` + `pull --offline` + `verify --offline`)
  und einen **frischen Smoke-Pfad** aus `tmp` (`init` + `add` + `lock` +
  `pull --offline` + `verify --offline`) gegen `registry-fixtures/` und
  den eingecheckten Replay-Cache.
- **`.github/workflows/ci.yml`**:
  - Bestehender Step `speccify end-to-end smoke (lock + pull + verify)`
    erhält `--offline` Flags für `pull` und `verify` (Default-Verhalten,
    aber explizit für CI-Klarheit).
  - Neuer Step `speccify init + add + pull + verify smoke (offline)`:
    legt in `mktemp -d` ein Projekt via `speccify init smoke-app
    --target react` an, fügt `@org/button` hinzu (`--registry`-Override
    auf `registry-fixtures/`), lockt, pullt und verifiziert offline gegen
    `tests/fixtures/llm-cache/`. Ruft das Binary direkt aus dem venv
    (`$GITHUB_WORKSPACE/.venv/bin/speccify`), weil `uv run` aus einer
    fremden CWD den Workspace-Kontext verliert.
- **`README.md`** überarbeitet:
  - Neuer Abschnitt **End-to-End Smoke (offline)** mit den exakten
    Befehlen aus dem CI-Smoke (example-project + frisches Projekt).
  - Neuer Abschnitt **Replay-Cache neu aufnehmen (Maintainer)**
    dokumentiert `scripts/record_llm_cache.py` (Voraussetzungen:
    `uv sync --extra bedrock`, AWS-Credentials via Env oder `.env`;
    `--force` für Re-Record).
  - „Wo es weitergeht“ aktualisiert: Phase 1b verlinkt, Phase 1a
    abgeschlossen markiert, Rebrand-Plan ins Archiv verlinkt.
  - Status-Absatz auf Phase 1b umgestellt.
- **Lokale Verifikation der CI-Sequenz** (1:1 nachgestellt mit
  `.venv/bin/speccify`): beide Smoke-Pfade laufen grün, der frische
  Pfad erzeugt `out/org/Button.tsx`, der example-project-Pfad bleibt
  byte-identisch.
- **Side-Quest**: lokales `.venv` war durch macOS/iCloud-Duplikate
  korrumpiert (`_editable_impl_speccify_cli 2.pth` neben dem Original →
  `site` ignorierte beide Pfade). Fix: `.venv` gelöscht und neu
  `uv sync --all-packages`. Kein Repo-Change nötig, nur als Hinweis im
  Log.
- **Verifikation**: `uv run pytest` → 134 grün; `uv run ruff check .` +
  `uv run ruff format --check .` clean.
- **Nächster Schritt** (Step 6): Master-Plan-Sync, ggf. annotated Tag
  `v0.2.0-phase-1b`; optional `v0.1.0-phase-1a` für die abgeschlossene
  Phase 1a nachziehen.

## 2026-05-12 (Phase 1b Step 5b — `pull`/`verify` auf Dispatcher + Replay-Cache umgestellt)
- **Step 5b abgeschlossen.** `speccify pull` und `speccify verify` rufen
  jetzt den Codegen-Dispatcher `speccify_core.render_for_target(spec,
  target, llm_client=...)` statt direkt den Stub-Adapter. Für
  `target == "react"` wird ein `ReplayCacheClient` über dem eingecheckten
  Cache (`tests/fixtures/llm-cache/`) eingespeist.
- **Neue CLI-Flags** auf `pull` und `verify`:
  - `--offline/--no-offline` (Default `--offline`): Cache-Miss → Exit 1
    mit klarer Fehlermeldung, kein Live-Bedrock-Call.
  - `--cache-dir <pfad>`: überschreibt Default und Env-Var
    `SPECCIFY_CACHE_DIR`. Default ist der repo-lokale Cache-Pfad
    `tests/fixtures/llm-cache/` (in `cli/src/speccify_cli/commands/_llm_client.py`).
- **Gemeinsamer Helper** `speccify_cli.commands._llm_client`
  (`resolve_cache_dir`, `build_replay_client`) — `pull` und `verify`
  teilen sich Pfad-Resolution und Client-Bau. `inner`-Hook für späteren
  Live-Fallback ist vorgesehen, aber in 5b nicht verdrahtet (Live-
  Aufnahme bleibt `scripts/record_llm_cache.py`).
- **Lockfile schreibt `LlmGeneratorPin`** pro Spec bei `pull`:
  `provider=bedrock`, `model=bedrock/eu.anthropic.claude-opus-4-7`,
  `prompt_version=0.1.0`, `seed=1`,
  `cache_key=sha256:<digest(spec_sha256+target+model+prompt_version+seed)>`.
  Helper-Methode `Lockfile.with_generator(spec_id, generator)` neu in
  `core/src/speccify_core/lockfile.py` (gemeinsam mit
  `with_generated_files` über interne `_replace_entry`-Hilfe).
- **`verify` prüft Pin-Konsistenz**: Modell-/Prompt-Version-/Seed-/
  Cache-Key-Drift zwischen Lockfile-`LlmGeneratorPin` und Re-Render-
  `cache_key` werden als separate Problem-Strings gemeldet (zusätzlich
  zu den bestehenden Spec-Hash- und Disk-Hash-Checks).
- **example-project regeneriert**: alte `*.md`-Stub-Outputs entfernt;
  `out/org/Button.tsx`, `out/org/ContactForm.tsx`,
  `out/org/OnboardingWizard.tsx` neu generiert (alle 3 aus Replay-Cache,
  byte-identisch reproduzierbar). `speccify.lock` enthält nun für jede
  Spec einen LLM-Pin mit `cache_key`. `speccify verify` läuft grün.
- **Tests neu/erweitert** (9 neu):
  - `cli/tests/test_pull.py` (5): TSX-Output + Lockfile-Pin, Determinismus
    (zwei `pull`-Aufrufe → byte-identisch), Fail ohne Lockfile,
    Target-Mismatch, Cache-Miss bei leerem `--cache-dir`.
  - `cli/tests/test_verify.py` (6): Happy-Path, Disk-Drift,
    Fail ohne Lockfile, Fail ohne `pull`, Modell-Drift (manuell editiertes
    Lockfile), Cache-Miss bei leerem `--cache-dir`.
- **Verifikation**: `uv run pytest` → **134 grün**, `uv run ruff check .`
  clean, `uv run ruff format .` clean. `mypy` zeigt Vor-Bestands-Fehler
  in `cli/tests/test_init.py`, `core/tests/test_bedrock_client.py` und
  `core/tests/test_lockfile.py` — **nicht von Step 5b verursacht** (in
  ungetauchten Test-Dateien aus Step 1/5a, bestehender Drift seit Step 5a-
  Status-Doku "mypy clean" behauptete). Wird in Step 5c bzw. separat
  bereinigt.
- **Nächster Schritt** (Step 5c): CI-Workflow um E2E-Smoke
  `init` + `add` + `pull --offline` + `verify --offline` erweitern;
  `record_llm_cache.py` im `README.md` dokumentieren. Danach Step 6
  (Master-Plan-Sync + Tag `v0.2.0-phase-1b`).

## 2026-05-08 (Phase 1b Step 5a — Provider-Switch: Anthropic → AWS Bedrock + Live-Aufnahme)
- **User-Entscheidung**: firmenweit nutzen wir AWS Bedrock statt der direkten
  Anthropic-API (`toshpy`, `himi-ai` als Referenz). Phase 1b stellt komplett
  auf Bedrock um, bevor Step 5b startet.
- **Ersetzt**: `speccify_core.codegen.anthropic_client.AnthropicClient` → neuer
  `speccify_core.codegen.bedrock_client.BedrockClient` (frozen dataclass) mit
  Lazy-Import von `boto3`, Provider-Präfix-Strip (`bedrock/...`) +
  Date-Suffix-Strip, Single-Shot `bedrock-runtime.converse`,
  deterministischer Text-Block-Extraktion aus `output.message.content`. AWS-
  Credentials via Standard-Chain (`AWS_REGION` / `AWS_ACCESS_KEY_ID` /
  `AWS_SECRET_ACCESS_KEY` / `AWS_PROFILE`); `region` optional am Client.
- **Bedrock-Spezifika**:
  - `seed` nicht durchgereicht (kennt `converse` nicht).
  - `temperature` bewusst **weggelassen** — `eu.anthropic.claude-opus-4-7`
    lehnt das Feld als deprecated mit `ValidationException` ab (initialer
    Run hatte `temperature: 0.0` und 6/6 Specs schlugen fehl). Determinismus
    kommt aus dem Replay-Cache.
  - Modell-Pin in `react_llm.py` von `anthropic/claude-sonnet-4.5@2026-03-01`
    auf `bedrock/eu.anthropic.claude-opus-4-7` umgestellt (Standard-Modell
    aus `toshpy/.env`).
- **Optional-Dep**: `anthropic>=0.34` → `boto3>=1.35`; Extras umbenannt von
  `[anthropic]` auf `[bedrock]` (Sub-Paket `core/pyproject.toml` +
  Workspace-Root `pyproject.toml`).
- **Recorder umgestellt** (`scripts/record_llm_cache.py`): Live-Client jetzt
  `BedrockClient`, AWS-Credential-Check (`AWS_ACCESS_KEY_ID` oder
  `AWS_PROFILE`) statt `ANTHROPIC_API_KEY`. Eingebauter minimaler
  `_load_dotenv` (ohne `python-dotenv`-Dep): liest `.env` am Repo-Root,
  setzt Vars nur falls nicht bereits exportiert (Shell wins). `.env` aus
  `toshpy` nach Repo-Root kopiert (`.gitignore` deckte `.env` bereits ab,
  daher keine Versehensgefahr).
- **Tests**: `core/tests/test_anthropic_client.py` (7 Tests) entfernt, neu
  `core/tests/test_bedrock_client.py` mit 10 Tests (Provider/Date-Strip,
  fehlendes `boto3`, Text-Block-Extraktion via Fake-boto3,
  Region-Durchreichung, Default-Chain-Pfad, Schema-Fehler, leere
  Text-Blöcke, Exception-Wrapping).
- **Live-Aufnahme erfolgreich**: `uv sync --extra bedrock` +
  `uv run python scripts/record_llm_cache.py` → 6/6 Cache-Einträge unter
  `tests/fixtures/llm-cache/` (~36 KB total) live via Bedrock `converse`
  rekorded und eingecheckt. Erste Iteration schlug an deprecated
  `temperature` ab, zweite (ohne `temperature`) lief sauber durch.
- **Verifikation**: `uv run pytest` 131 grün (120 alt + 10 neu + 1
  Lockfile-Korrektur unverändert), `ruff check`, `ruff format`,
  `mypy core/src cli/src` alle clean.
- Plan-/AGENTS-Sync: Step 5a in `phase-1b-react-codegen.md` auf Bedrock
  umformuliert + abgehakt (inkl. Live-Aufnahme); Sub-Step 5b nun unblocked.

## 2026-05-07 (Phase 1b Step 5a-Fix — Workspace-Extra `anthropic`)
- **Bugfix für Live-Aufnahme**: `uv sync --extra anthropic` schlug am Repo-Root
  mit `Extra `anthropic` is not defined in the project's `optional-dependencies`
  table` fehl, weil das Extra nur im Sub-Paket `core/pyproject.toml` deklariert
  war, `uv sync` am Workspace-Root aber das Root-`pyproject.toml` konsultiert.
- Fix: `[project.optional-dependencies]` im Root-`pyproject.toml` ergänzt mit
  `anthropic = ["speccify-core[anthropic]"]` — spiegelt das Sub-Paket-Extra auf
  Workspace-Ebene, sodass der im Phasen-Plan/AGENTS-Anleitung dokumentierte
  Aufruf `uv sync --extra anthropic` direkt funktioniert. CI-Default
  (`uv sync` ohne Extra) bleibt unverändert.
- Verifikation: `uv sync --extra anthropic` installiert `anthropic`, `httpx`,
  `pydantic` etc. sauber; `uv run pytest` 127 grün; `ruff`/`mypy` clean.
- **Maintainer kann jetzt aufnehmen**:
  ```
  uv sync --extra anthropic
  ANTHROPIC_API_KEY=sk-... uv run python scripts/record_llm_cache.py
  ```

## 2026-05-07 (Phase 1b Step 5a — Live-`AnthropicClient` + Recorder-Skript)
- **Step 5a abgeschlossen**: neuer Live-Adapter
  `speccify_core.codegen.anthropic_client.AnthropicClient` (frozen
  dataclass) mit Lazy-Import des `anthropic` SDK, Provider-Präfix-Strip
  (`anthropic/...`) + Date-Suffix-Strip (`...@2026-03-01`), Single-Shot
  `messages.create` mit `temperature=0.0`, deterministischer
  Text-Block-Extraktion. `seed` wird bewusst nicht durchgereicht (SDK-fremd) —
  Reproduzierbarkeit kommt aus dem Replay-Cache. Klare Fehler bei leerem
  `api_key` und fehlender SDK-Installation (`AnthropicClientError`).
- `anthropic>=0.34` als **optional-Dep** `speccify-core[anthropic]` in
  `core/pyproject.toml` ergänzt — CI installiert das SDK nicht, da
  `pull --offline` ausschließlich gegen den Replay-Cache läuft.
- Neues Maintainer-Tool `scripts/record_llm_cache.py`: walkt
  `registry-fixtures/<scope>/<name>/<version>/spec.speccify.yaml`
  deterministisch, baut pro Spec einen `CacheKey` via
  `react_llm.make_cache_key`, ruft Live-`AnthropicClient`, normalisiert +
  validiert TSX (Klammer-Heuristik) und schreibt den **rohen** Response in
  den Replay-Cache. Idempotent (skip bei Cache-Hit; `--force` überschreibt).
  Fail-Fast ohne `ANTHROPIC_API_KEY`. Zielverzeichnis:
  `tests/fixtures/llm-cache/`.
- 7 neue Tests in `core/tests/test_anthropic_client.py`: Provider/Date-Strip
  (4 Varianten), `AnthropicClientError` ohne API-Key, klare
  Fehler-Message bei fehlendem SDK (Lazy-Import-Pfad), Text-Block-Extraktion
  via Fake-SDK (Filter auf `type=='text'`, mehrere Blöcke).
- Verifikation: `uv run pytest` 127 grün (120 alt + 7 neu), `ruff check`,
  `ruff format`, `mypy core/src cli/src` alle clean.
- **Offen für Maintainer**: Live-Aufnahme der 6 Phase-0-Cache-Einträge mit
  `ANTHROPIC_API_KEY` und Eincheck unter `tests/fixtures/llm-cache/`.
  Sub-Step 5b (`pull`/`verify` auf Dispatcher umstellen) hängt davon ab.
- Plan-/Status-Sync: Step 5 in `phase-1b-react-codegen.md` in 5a/5b/5c
  zerlegt, 5a ✅; `.agent/status.md` aktualisiert.

## 2026-05-07 (Phase 1b Step 4 — React-LLM-Adapter + Codegen-Dispatcher)
- **Step 4 abgeschlossen**: neuer Adapter `speccify_core.codegen.react_llm`
  mit Pin-Konstanten (`PROVIDER="anthropic"`,
  `MODEL="anthropic/claude-sonnet-4.5@2026-03-01"`, `PROMPT_VERSION="0.1.0"`,
  `DEFAULT_SEED=1`, `TARGET="react"`), `build_prompt`, `normalize_tsx`
  (Markdown-Fence-Strip + CRLF→LF + Trailing-WS + finale Newline; bewusst
  minimal nach User-Entscheidung), `validate_tsx` (Klammer-Heuristik mit
  String-/Kommentar-Awareness — fängt grobe LLM-Fehler ohne Native-Toolchain),
  `make_cache_key`, `render`/`render_to_files` (auto-`bind_key` für
  `ReplayCacheClient`), `CodegenError`, `ReactRenderResult`. Output-Pfad
  `<scope>/<PascalCase(name)>.tsx`.
- Prompt-Template `core/src/speccify_core/codegen/templates/react_llm.prompt.j2`
  (deterministisch, Single-Default-Export, TSX-only-Anweisung); Hatch
  `force-include` für die `.j2`-Datei in `core/pyproject.toml` ergänzt.
- Dispatcher `speccify_core.codegen.render_for_target` + `TargetRender(files,
  cache_key)` + `SUPPORTED_TARGETS=("react",)`. Phase-1a-Stub-Re-Exports
  (`render`, `render_to_files`) bleiben erhalten — `pull`/`verify` werden
  explizit erst in Step 5 auf den Dispatcher umgestellt.
- Re-Exports in `speccify_core.__init__` (`CodegenError`, `SUPPORTED_TARGETS`,
  `TargetRender`, `render_for_target`); `__all__` aktualisiert.
- 20 neue Tests in `core/tests/test_react_llm.py`: `normalize_tsx`
  (Trailing-WS/CRLF, finale Newline, Markdown-Fences), `validate_tsx`
  (balanced/leer/unbalanced/Klammern in Strings+Kommentaren ignoriert/
  unterminated string), `build_prompt` (Spec-Id + Props + Events sichtbar),
  `make_cache_key` (Determinismus + Pin-Felder), `render`/`render_to_files`
  (Cache-Hit, Offline-Miss → `CacheMissError`, PascalCase-Pfad, ungültiges
  TSX → `CodegenError`, Fence-Strip), Dispatcher (React-Pfad, fehlender
  Client → `CodegenError`, unbekanntes Target → `NotImplementedError`,
  `SUPPORTED_TARGETS`-Membership, byte-Identität über zwei Runs).
- Plan-Open-Questions vor Step 4 mit User geklärt und im Plan verankert:
  Anthropic Claude Sonnet 4.5 fix verdrahtet, minimale Normalisierung,
  Klammer-Heuristik in Python, Cache-Fixtures unter `tests/fixtures/llm-cache/`
  (Eincheck-Pfad in Step 5).
- Verifikation: `uv run pytest` 120 grün (100 alt + 20 neu), `ruff check`,
  `ruff format --check`, `mypy core/src cli/src` alle clean.
- Plan-/Status-Sync: Step 4 ✅ in `phase-1b-react-codegen.md`,
  `.agent/status.md` Phase + Nächste-Schritte aktualisiert.

## 2026-05-07 (Phase 1b Step 3 — Replay-Cache + `LlmClient`-Protokoll)
- **Step 3 abgeschlossen**: neues Modul `speccify_core.codegen.replay` mit
  `CacheKey` (frozen dataclass; `digest()` über kanonisches JSON mit
  `sort_keys=True` und kompakten Separators → SHA-256-Hex), `ReplayCache`
  (Disk-Layout `<root>/<digest>.json` mit `{key, response}`; atomares `put`
  via tempfile + `replace`; `get`/`has`/`put`; korruptes Entry → `CacheMissError`),
  und `CacheMissError`.
- `LlmClient`-Protokoll mit Signatur `complete(*, prompt, model, seed) -> str`
  und `ReplayCacheClient`-Wrapper: `offline=True` → Cache-Miss wirft direkt;
  `offline=False` + `inner` → Live-Call mit Cache-Einlagerung; `bind_key(...)`
  setzt Spec-Kontext explizit (kein impliziter Threading-Kanal); Key wird
  nach erfolgreichem Call konsumiert; Mismatch zwischen `bind_key.model/seed`
  und `complete.model/seed` → `CacheMissError`.
- Re-Exports in `speccify_core.codegen.__init__` und `speccify_core.__init__`
  (`CacheKey`, `CacheMissError`, `LlmClient`, `ReplayCache`,
  `ReplayCacheClient`); `__all__` aktualisiert.
- 15 neue Tests in `core/tests/test_replay_cache.py`: Digest-Stabilität +
  Feld-Sensitivität (alle 7 Varianten verschieden), Get/Put/Has/Round-Trip,
  kanonisches JSON-Layout, Overwrite, Corrupt-Entry-Reject, Offline-Miss/-Hit,
  Online-Miss-Fallback (inkl. Cache-Speicherung), Online-Hit (kein
  Inner-Call), `bind_key`-Pflicht, Key-Mismatch, Key-Konsum nach Use,
  Protocol-Strukturalität.
- Verifikation: `uv run pytest` 100 grün (85 alt + 15 neu), `ruff check`,
  `ruff format --check`, `mypy core/src cli/src` alle clean.
- Plan-/Status-Sync: Step 3 ✅ in `phase-1b-react-codegen.md`,
  `.agent/status.md` Phase + Nächste-Schritte aktualisiert.

## 2026-05-07 (Phase 1b Step 2 — Lockfile-Schema `kind: llm`)
- **Step 2 abgeschlossen**: `schema/lockfile.schema.json` `generator` jetzt
  `oneOf` mit `kind: template` (template_set + template_version) und
  `kind: llm` (provider, model, prompt_version, optional `seed` ≥ 0,
  `cache_key` als sha256-Pattern).
- `speccify_core.lockfile`: neuer `LlmGeneratorPin` (frozen dataclass);
  bestehender `GeneratorPin` bleibt als Template-Pin und wird zusätzlich als
  `TemplateGeneratorPin` aliasiert; Type-Alias `AnyGeneratorPin = GeneratorPin
  | LlmGeneratorPin`. `LockEntry.generator: AnyGeneratorPin`. Serialisierung/
  Parsing per `kind` verzweigt; `seed` wird im YAML weggelassen, wenn nicht
  gesetzt.
- Re-Exports in `speccify_core.__init__` ergänzt (`AnyGeneratorPin`,
  `LlmGeneratorPin`, `TemplateGeneratorPin`); `__all__` aktualisiert.
- 4 neue Round-Trip-Tests in `core/tests/test_lockfile.py`: LLM-Pin mit `seed`
  (inkl. Re-Read und `"seed: 42"` im YAML), LLM-Pin ohne `seed` (kein
  `seed:`-Key im Output), gemischtes Lockfile (template + llm in einem
  `specs[]`, Round-Trip-Equality), Schema-Reject bei kombinierten Template-/
  LLM-Feldern (`oneOf`-Verletzung).
- Default-Verhalten unverändert: `build_lockfile` und alle bestehenden Tests/
  Fixtures laufen weiter mit Template-Pin.
- Verifikation: `uv run pytest` 85 grün (81 alt + 4 neu), `ruff check`,
  `ruff format --check`, `mypy core/src cli/src` alle clean.
- Plan-/Status-Sync: Step 2 ✅ in `phase-1b-react-codegen.md`,
  `.agent/status.md` Nächste-Schritte aktualisiert.

## 2026-05-06 (Phase 1b Step 1 — `speccify init`)
- **Step 1 abgeschlossen**: neuer CLI-Command `speccify init <name>
  [--target react]` (`cli/src/speccify_cli/commands/init.py`).
- Output ist bewusst minimal (User-Entscheidung): `speccify.yaml` mit
  `schema_version: 1`, `target` (Default `react`), `dependencies: {}`.
  Kein `registry`-Block, kein `package.json`/Skeleton.
- Verhalten: Verzeichnis wird angelegt, falls nicht existent; existierendes
  leeres Verzeichnis wird befüllt; nicht-leeres Verzeichnis oder ungültiger
  Name (Slash/Backslash) → Exit 1 mit Fehlermeldung, kein Manifest geschrieben.
- 7 neue CLI-Tests (`cli/tests/test_init.py`): Happy-Path, Default-Target,
  Custom-Target, Round-Trip via `ProjectManifest.load`, leeres existierendes
  Verzeichnis, nicht-leeres Verzeichnis (Exit 1), ungültiger Name.
- Verifikation: `uv run pytest` 81 grün (74 alt + 7 neu), `ruff check`,
  `ruff format --check`, `mypy core/src cli/src` alle clean.
- Plan-/Status-Sync: Step 1 ✅ in `phase-1b-react-codegen.md`,
  `.agent/status.md` Nächste-Schritte aktualisiert.

## 2026-05-06 (Phase 1b geplant)
- **Phasen-Plan `phase-1b-react-codegen.md` geschrieben** — reines Plan-Dokument
  als nächster atomarer Commit, bevor Code für Phase 1b angefasst wird
  (Plan-Disziplin Regel #1, `AGENTS.md`).
- Kern-Entscheidungen mit User abgestimmt:
  - **LLM-Codegen** (Variante B aus Master-Plan) statt Templates für React —
    direkt der Zielzustand. CI nutzt einen eingecheckten Replay-Cache statt
    Live-API-Calls (`--offline` Flag), Cache-Key über
    `(spec_sha256, target, model, prompt_version, seed)`.
  - **`speccify init` minimal**: nur `speccify.yaml` mit `target` + leerer
    `dependencies`, kein `package.json`/Skeleton-Projekt.
  - **TSX-Output minimal**: ein File pro Spec mit Props/Types aus Inputs/Events
    + Komponenten-Skeleton mit `// TODO`-Markern. Keine Tests/Stories.
- Plan zerlegt in 6 atomare Steps: (1) `init`, (2) Lockfile-Schema-Erweiterung
  (`generator.oneOf` für `template`/`llm`), (3) Replay-Cache + `LlmClient`-
  Protokoll, (4) React-LLM-Adapter + Codegen-Dispatcher, (5)
  `pull --target react --offline` + CI + Fixtures, (6) Master-Plan-Sync + Tag
  `v0.2.0-phase-1b`.
- Offene Fragen vor Step 4 im Plan dokumentiert: Provider-Default,
  Normalisierungs-Tiefe, TSX-Validitäts-Check, Cache-Fixture-Ort.
- `AGENTS.md` „Aktuelle Phase" und `.agent/status.md` auf „Phase 1b geplant,
  Step 1 als Nächstes" umgestellt.

## 2026-05-06 (Phase 1a abgeschlossen)
- **Phase 1a Step 4 + Step 5 abgeschlossen** — Stub-Codegen, `speccify pull`,
  `speccify verify`, `lint`-Anpassung, CI-Step und Master-Plan-Sync. Damit ist
  der vollständige Resolver/Lockfile/Codegen/Verify-Kreis für Phase 1a zu.
  - Neues Codegen-Modul `speccify_core.codegen` (Re-Exports) + `codegen/stub.py`
    mit Konstanten `TEMPLATE_SET="phase-1a-stub"` / `TEMPLATE_VERSION="0.1.0"`,
    `render(spec, target)` und `render_to_files(spec, target)`. Output-Pfad
    folgt `<scope>/<name>.md`.
  - Jinja2-Template `core/src/speccify_core/codegen/templates/stub.md.j2` mit
    YAML-Frontmatter (`target`, `spec_id`, `spec_version`, `template_set`,
    `template_version`), Markdown-Tabellen für Inputs/Outputs/Events/Acceptance
    und einer `Uses`-Liste. Determinismus: `keep_trailing_newline=True`,
    keine Datums-/Zufallswerte.
  - `jinja2>=3.1` als Runtime-Dependency in `core/pyproject.toml`; Hatch
    `force-include` für die `.j2`-Datei (sonst landet sie nicht im Wheel).
  - Lockfile-Defaults (`DEFAULT_TEMPLATE_SET`/`DEFAULT_TEMPLATE_VERSION`)
    werden jetzt aus `speccify_core.codegen.stub` re-exportiert (single source
    of truth, wie im Plan vorgesehen).
  - Neuer CLI-Command `speccify pull` (`commands/pull.py`): liest Lockfile,
    fordert Specs aus der `LocalRegistry`, ruft Stub-Codegen, schreibt Dateien
    atomar (`tempfile` + `os.replace`), aktualisiert
    `generated_files_sha256` pro Eintrag via `Lockfile.with_generated_files`.
    Klare Fehler bei fehlendem Lockfile oder Target-Mismatch zum Lockfile.
  - Neuer CLI-Command `speccify verify` (`commands/verify.py`): re-resolved das
    Manifest, vergleicht (id, version, sha256, target) mit dem Lockfile,
    re-rendert jede Spec und vergleicht Output-Hashes, prüft schließlich auch
    die tatsächlichen Dateien auf Disk gegen die Lockfile-Hashes
    (Drift-Detection). Sammelt alle Probleme und beendet bei Drift mit Exit 1.
  - `speccify lint` angepasst: Specs ohne Top-Level `kind`-Feld (Projekt-
    Manifeste wie `speccify.yaml`) werden mit Hinweis übersprungen statt
    fälschlich gegen `spec.schema.json` validiert. Manifest-Schema-Validierung
    läuft weiter beim Manifest-Load in `lock`/`add`.
  - 12 neue Tests:
    - `core/tests/test_codegen_stub.py` — Determinismus, Output-Pfad-Konvention,
      Frontmatter, `Uses`-Block für Workflow-Specs.
    - `cli/tests/test_pull.py` — E2E (lock + pull, Hash im Lockfile passt zur
      Disk-Datei), Determinismus über zwei `pull`-Aufrufe, fehlendes Lockfile,
      Target-Mismatch zum Lockfile.
    - `cli/tests/test_verify.py` — Happy-Path, manueller Disk-Drift → Exit 1
      mit „Disk-Drift", fehlendes Lockfile, fehlender `pull` (leere
      `generated_files_sha256`).
  - End-to-End im `example-project/` lokal grün:
    `uv run speccify lock` → 3 Specs (button, login-screen via Diamond,
    onboarding-wizard), `uv run speccify pull --out ./out` → 3 Markdown-Dateien,
    `uv run speccify verify --out ./out` → konsistent.
  - CI-Workflow `.github/workflows/ci.yml` um E2E-Smoke ergänzt
    (`cd example-project && lock && pull && verify`).
  - `.gitignore` ergänzt um `example-project/out/` und
    `example-project/speccify.lock` (werden in CI bei jedem Lauf neu gebaut).
  - Master-Plan `.agent/plans/archive/speccify-plan.md` synchronisiert:
    - Lockfile-Beispiel hat jetzt zwei Varianten: `kind: template` (Phase 1a,
      ohne API-Keys reproduzierbar) und `kind: llm` (Phase 1b+).
    - Phase 1 explizit in Sub-Spikes 1a / 1b / 1c / 1d zerlegt; 1a verlinkt
      auf den abgeschlossenen Phasen-Plan.
    - Erstes Codegen-Target ist React (statt SwiftUI), Begründung dokumentiert;
      Phase 3 zieht SwiftUI/Angular nach.
  - Verifikation lokal grün: `uv run pytest` (74 Tests, +12 neu seit Step 3),
    `uv run ruff check`, `uv run ruff format --check`,
    `uv run mypy core/src cli/src`, `uv run speccify lint specs/*.speccify.yaml`,
    sowie der CI-E2E-Pfad im `example-project/`.
  - Phase-1a-Plan: Steps 4 und 5 sind als ✅ markiert; `status.md` und
    `AGENTS.md` auf „Phase 1a abgeschlossen → Phase 1b" umgestellt.

## 2026-05-06 (noch später²)
- **Phase 1a Step 3 abgeschlossen** — Lockfile-Format + `speccify lock`/`add`:
  - Neues JSON-Schema `schema/lockfile.schema.json` (Draft 2020-12) mit
    `schema_version=1`, `target`, `specs[]` (id, version, sha256, resolved_via,
    target, generator{kind=template, template_set, template_version},
    generated_files_sha256[]).
  - Neues Modul `speccify_core.lockfile` mit `Lockfile`/`LockEntry`/`GeneratorPin`/
    `GeneratedFile`, `LockfileError`, `Lockfile.load`/`write` (deterministischer
    YAML-Dump mit fixer Key-Reihenfolge, alphabetisch nach `id`),
    `Lockfile.with_generated_files` (für Step 4) und Top-Level-Helper
    `build_lockfile(target, resolutions)`.
  - Defaults-Konstanten `DEFAULT_TEMPLATE_SET="phase-1a-stub"` und
    `DEFAULT_TEMPLATE_VERSION="0.1.0"` zentralisiert (Step 4 importiert sie aus
    `speccify_core.codegen.stub`, bis dahin liegen sie hier).
  - Re-Exports in `speccify_core.__init__` ergänzt.
  - CLI-Subcommand-Layer neu: `cli/src/speccify_cli/commands/__init__.py`,
    `_workspace.py` (gemeinsamer `WorkspaceContext` mit Manifest+Registry-Lookup,
    `--registry`-Override), `lock.py` (`speccify lock`) und `add.py`
    (`speccify add @scope/name[@<range>]`, Default-Range `^<major.minor>` aus
    latest-Registry-Version, ruft implizit `lock`).
  - 16 neue Tests:
    - `core/tests/test_lockfile.py` — Round-Trip, alphabetische Sortierung beim
      Schreiben, Schema-Violation, `with_generated_files`-Verhalten,
      `build_lockfile` aus echtem Resolver-Graph.
    - `cli/tests/test_lock.py` — Smoke gegen Fixtures, Determinismus zweier
      Aufrufe, unbekannte Dependency, fehlendes Manifest, `--registry`-Override.
    - `cli/tests/test_add.py` — Default-Range, expliziter Caret, exakte Version,
      unbekannte Spec, ungültige Spec-Referenz.
  - Verifikation lokal grün: `uv run pytest` (62 Tests, +16 neu),
    `uv run ruff check`/`format --check`, `uv run mypy core/src cli/src`.
  - Plan-Status: Phase 1a Step 4 (Stub-Codegen + `speccify pull`) ist als
    Nächstes dran.

## 2026-05-06 (noch später)
- **Phase 1a Step 2 abgeschlossen** — MVS-Resolver:
  - Neues Modul `speccify_core.resolver` mit `Range` (Caret `^X.Y`/`^X.Y.Z` + exakt
    `X.Y.Z`), `Resolution`, `ResolvedGraph`, `Resolver` und `ResolverError`-Hierarchie
    (`VersionNotFoundError`, `RangeConflictError`).
  - MVS-Algorithmus strikt nach Go-Vorbild: Maximum aller geforderten
    Mindestversionen, danach kleinste verfügbare Version, die alle Ranges
    erfüllt. Transitive Auflösung über `uses:` via Worklist.
  - Spec-Hashing: `sha256` der Original-Bytes der Spec-Datei (nicht re-serialisiert)
    → `Resolution.spec_sha256`. Resolutions deterministisch alphabetisch sortiert.
  - Re-Exports in `speccify_core.__init__` ergänzt.
  - 12 neue Tests in `core/tests/test_resolver.py`: Range-Parser (Caret/Exact/Invalid),
    Happy-Path, transitive `uses:`-Auflösung, Diamond mit `button@0.1.1` als
    Resultat (`onboarding-wizard.uses: ^0.1` + `login-screen.uses: ^0.1.1`),
    sortierte Resolutions, fehlende Version, unbekannte Spec, inkompatible Ranges,
    ungültige Range im Manifest.
  - Verifikation lokal grün: `uv run pytest` (46 Tests, +12 neu),
    `uv run ruff check`/`format --check`, `uv run mypy core/src cli/src`.
  - Plan-Status: Phase 1a Step 3 (Lockfile + `speccify add`/`lock`) ist als
    Nächstes dran.

## 2026-05-06 (später)
- **Phase 1a Step 1 abgeschlossen** — Manifest- und Pseudo-Registry-Layer:
  - Neues JSON-Schema `schema/manifest.schema.json` (Draft 2020-12) für
    `speccify.yaml`-Projektmanifest: `schema_version=1`, `target`,
    optional `registry.path`, `dependencies` als Map `@scope/name → range`
    (Phase 1a: nur exakte Versionen oder Caret `^X.Y` / `^X.Y.Z`).
  - `speccify_core.manifest.ProjectManifest` als immutable `@dataclass(frozen=True)`
    mit `load`/`write` (deterministischer YAML-Dump, sortierte Dependency-Keys),
    `resolved_registry_path()` (relativ zum Manifest), `ManifestError`-Hierarchie.
  - `speccify_core.registry`: `Version` (`major.minor.patch`, Pre-Releases in 1a
    bewusst ausgeklammert), `Spec` (mit Original-Bytes für stabile Hashes),
    `LocalRegistry` (Layout `<root>/<scope>/<name>/<version>/spec.speccify.yaml`,
    `list_versions` sortiert, `fetch` mit Available-Versions-Hint im Fehler),
    `RegistryError`.
  - Re-Exports in `core/src/speccify_core/__init__.py` ergänzt.
  - `registry-fixtures/` mit den 5 Phase-0-Specs als `0.1.0` plus
    `org/button/0.1.1/` für den späteren Diamond-Test angelegt; IDs/`uses`
    von `spec://...` auf `@org/...` umgeschrieben. Diamond-Setup so gewählt,
    dass reines Go-MVS deterministisch `button@0.1.1` liefert: `login-screen`
    fordert `@org/button@^0.1.1`, `onboarding-wizard` bleibt `@org/button@^0.1`
    (Mindestversionen `0.1.1` vs. `0.1.0`, Maximum = `0.1.1`).
  - `example-project/speccify.yaml` als Minimal-Manifest (Deps: `@org/button`,
    `@org/onboarding-wizard`).
  - Tests: `core/tests/test_manifest.py` (Round-Trip, Default-Registry-Pfad,
    fehlende/ungültige Felder, unbekannte Top-Level-Felder) und
    `core/tests/test_registry.py` (Version-Parsing/Order, sortierte Liste,
    Fetch-Bytes-Stabilität, Available-Versions-Hint, ID-Format-Check,
    Root-Validierung, alle 5 Specs vorhanden).
  - Verifikation lokal grün: `uv run pytest` (34 Tests, alt: 12, neu: 22),
    `uv run ruff check`/`format --check`, `uv run mypy core/src cli/src`,
    `uv run speccify lint registry-fixtures/.../spec.speccify.yaml` (alle 6
    Fixtures gegen `spec.schema.json` valide).
  - Plan-Status: Phase 1a Step 2 (MVS-Resolver) ist als Nächstes dran.

## 2026-05-06
- **Phase 1a-0 (Rebrand) abgeschlossen**: Repository komplett von `flowcation` auf
  `speccify` umgestellt. Python-Pakete (`flowcation_core/cli/mcp` →
  `speccify_core/cli/mcp`), Distribution-Namen, Workspace-Name, CLI-Binary
  (`flowcation` → `speccify`), Schema-`$id` (`https://speccify.io/schema/spec/v0.json`),
  Spec-ID-URI-Schema (`flow://` → `spec://`), Spec-Datei-Suffix
  (`*.flowcation.yaml` → `*.speccify.yaml`), Manifest-/Lockfile-Konvention
  (`speccify.yaml`/`speccify.lock`), Master-Plan in `speccify-plan.md` umbenannt.
- Doku konsistent: `README.md`, `AGENTS.md`, alle `*/README.md`, `.agent/*.md`,
  `phase-1a-resolver-lockfile.md` umgestellt. CI-Workflow ruft jetzt
  `speccify lint specs/*.speccify.yaml`.
- Verifikation grün: `uv lock` + `uv sync --reinstall` + `uv run pytest`
  (12 Tests) + `ruff check`/`format --check` + `mypy core/src cli/src` +
  `speccify lint specs/*.speccify.yaml` (5 Specs).
- Plan `phase-1a0-rename-to-speccify.md` nach `archive/` verschoben (Status →
  Done). Annotated Tag `v0.0.1-speccify-rebrand` als Marker vor Phase 1a.
- Domain-Status: Owner hat `speccify.io` + `speccify.de` bei df.eu registriert.
  `speccify.dev` ist bei df.eu nicht verfügbar/anbietbar — defensives Halten
  von `.dev` aufgeschoben (optional später via Cloudflare Registrar / Namecheap /
  Squarespace). Status-Update in `phase-1a0-rename-to-speccify.md` (Header +
  Domain-Liste) und `archive/naming-plan.md` (Header-Update-Zeile) ergänzt.
- Naming-Entscheidung final: **`speccify`** (Begründung im archivierten
  `archive/naming-plan.md`: Spec→Verb, Owner-Vorbenutzung, npm/GH-Org/`.io`/`.dev`
  frei).
- Neuer Plan `phase-1a0-rename-to-speccify.md` angelegt (Code-Rebrand:
  Python-Pakete `flowcation_*` → `speccify_*`, CLI-Binary `speccify` → `speccify`,
  Schema-`$id`, Manifest-/Lockfile-Name, Spec-ID-Schema `spec://` → `spec://`,
  Doku-Querverweise; Stages 1–6 mit Verifikation und Tag `v0.0.1-speccify-rebrand`).
- `naming-plan.md` nach `archive/` verschoben (Entscheidung getroffen,
  Recherche-Plan erfüllt). `status.md` umgebogen: Phase 1a-0 als nächster
  Schritt vor Phase 1a.
- Naming-Plan: Abschnitt „Weitere TLDs (`.ch`/`.at`/`.eu`)" ergänzt —
  Empfehlung: **nicht ins Initial-Setup**, da kein dedizierter Marketing-Hub
  und kein akutes Defensiv-Risiko. Tabelle mit Kosten/Nutzen + Nachzieh-Trigger
  (CH/AT-Kunden, EU-Förderprogramme, Squatting). Header-Update-Zeile ergänzt.
- Naming-Plan: Domain-Strategie-Abschnitt für `speccify` ergänzt
  (`.io` international + `.de` DE-Markt als Setup, `.com` aufschiebbar/optional).
  Enthält: Begründung mit Dev-Tool-Präzedenzfällen (`pnpm.io`, `n8n.io`,
  `fly.io`, `sentry.io`, ...), `.com`-Vorteile-Tabelle, Konkretplan
  (Sofort-Sicherung der freien Assets, `.com`-Anfrage mit Limit 500–3k USD),
  Heuristik-Tabelle und bewusste Auslassungen (`.ai`, `.app`).
- Naming-Plan: zwei Owner-Eigenvorschläge (`speccify`, `zouop`) ergänzt + bewertet.
  - `speccify`: npm/GH-Org frei, `.dev`/`.io` frei, `.com` registriert (geparkt seit
    2022, kein Server). Plus: Owner hat OSS-Vorbenutzung
    (`mhennemeyer/speccify`). Inhaltlich stärkster Kandidat (Spec→Verb).
  - `zouop`: `.com` bereits in Owner-Besitz, npm + `.dev`/`.io` frei,
    aber GitHub-User `zOuOp` blockiert Org-Anlage und Wort hat keinen
    semantischen Bezug zum Produkt. Eingeordnet als Backup.
  - Persönlicher Kurzfavorit neu sortiert: 1) `speccify`, 2) `forgepkg`,
    3) `mosaicspec`, 4) `anvilspec`, 5) `zouop`.
- Plan-Hygiene durchgeführt: bestehende Pläne in `.agent/plans/` auf Status geprüft.
- Phase 0 final geclosed:
  - ADR-Light-Tabelle für Q1–Q5 in `phase-0-wrap-up.md` ergänzt
    (Q1 strikte `kind`-Enum ab Phase 1, Q2 Asset-Ref-Whitelist
    `relativ + asset:// + figma:// + https://`, Q3 Resolver in Phase 1a,
    Q4 `$schema`-Pin auf Draft 2020-12 + Validator-Check in Phase 1,
    Q5 Conformance-Runner erst Phase 3).
  - Handover-Sektion auf `phase-1a-resolver-lockfile.md` und Master-Plan-Phase-1
    ergänzt.
  - Status `Done` (2026-05-06) im Plan-Header gesetzt.
- Pläne archiviert (`git mv` nach `.agent/plans/archive/`):
  - `phase-0-wrap-up.md` (Wrap-up abgeschlossen).
  - `phase-0-closeout.md` (überholt durch wrap-up; nicht ausgeführt).
  - `phase-0-wrap-up-decisions.md` (in wrap-up integriert).
- Querverweise umgebogen: `README.md` zeigt auf Archiv-Pfade + Phase-1a-Plan;
  `AGENTS.md` *Aktuelle Phase* auf Phase 1a umgestellt.
- `status.md` aktualisiert: Phase = *Phase 0 abgeschlossen — Phase 1a aktiv*,
  nächster Schritt = Phase-1a-Plan + Naming-Entscheidung.
- Annotated Tag `v0.0.0-phase0` auf den Wrap-up-Commit gesetzt.

## 2026-05-05
- Projekt initialisiert
- Phase-0-Abschluss-Tooling ergänzt:
  - `ruff`, `mypy`, `types-PyYAML` als Dev-Deps in Workspace-`pyproject.toml` gepinnt
    (passt zur Tooling-Aussage in `AGENTS.md`).
  - Repo mit `ruff format` formatiert (2 Dateien angepasst:
    `cli/tests/test_lint.py`, `core/src/speccify_core/validator.py`).
  - GitHub-Actions-Workflow `.github/workflows/ci.yml` um Format-Check + Mypy
    erweitert (vorher nur `ruff check` + Tests + lint).
- Verifiziert lokal: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy core/src cli/src`, `uv run pytest` (12 Tests),
  `uv run speccify lint specs/*.yaml` — alle grün.
- Phase 0 inhaltlich vollständig (Stages 1–8 abgedeckt); offen sind nur die
  im Phase-0-Plan genannten Open Questions sowie der Übergang zu Phase 1.
- Phase-0-Abschluss formalisiert:
  - `phase-0-spec-schema-spike.md` abgehakt (Status `Done`, alle Stages mit ✅
    und Artefakt-Verweis, Validation-Block markiert).
  - Neuer Plan `.agent/plans/phase-0-wrap-up.md` angelegt (Open Questions +
    Phase-1-Übergabe + ADR-artige Entscheidungstabelle).
  - Phase-0-Plan via `git mv` nach `.agent/plans/archive/` verschoben.
  - Querverweise in `AGENTS.md` und `README.md` auf den archivierten Pfad
    bzw. den neuen Wrap-up-Plan umgebogen.
  - `status.md` auf *Phase 0 abgeschlossen — Wrap-up läuft* gesetzt.

## 2026-05-19 — Phase-1d-Plan-Entwurf
- Neuer Phasen-Plan `.agent/plans/phase-1d-browser-playground.md` angelegt
  (Single Source of Truth für Phase 1d).
- Inhalt: Browser-Playground unter `apps/web/` (Next.js 15 + React 19,
  FastAPI-Backend in-process über `speccify-core`), MVP-Endpoints
  `GET /api/v1/specs` + `POST /api/v1/render`, **offline-only über
  Replay-Cache** (kein Live-Bedrock, vom User explizit so entschieden),
  Cross-Consistency CLI ↔ MCP ↔ Web byte-identisch, Tag-Vorschlag
  `v0.4.0-phase-1d`.
- Stack-Entscheidungen (vom User bestätigt): Next.js (statt SvelteKit),
  Replay-Cache-MVP (statt Backend-Proxy zu Bedrock).
- Plan-Doku: 6 Implementation-Steps + 5 Open Questions; noch keine
  Implementierung.
- Nächster Schritt: User-Review des Plans, dann optional Tag
  `v0.3.0-phase-1c` setzen, dann Phase-1d Step 0 starten.

## 2026-05-19 — Phase 1c Tag gesetzt + Phase 1d Step 0
- Tag `v0.3.0-phase-1c` lokal annotated auf Commit `6e4fa86` (Phase-1c-Wrap-up) gesetzt.
- Phase 1d Step 0: `apps/web/backend/` als uv-Workspace-Member `speccify-web-backend` angelegt (FastAPI + uvicorn[standard] + speccify-core). Skeleton mit `create_app()` + `/api/v1/health`, `cli.main` (argparse, lazy uvicorn-Import), `tests/test_health.py` (TestClient-Smoke).
- Top-Level `pyproject.toml` erweitert: workspace member, source-pin `speccify-web-backend`, dev-group + `httpx`, pytest testpaths.
- `uv sync --all-packages` (nach `--reinstall` wegen bekanntem editable-`.pth`-Side-Quest aus Phase 1c Step 0), **175 Tests grün** (174 + 1 neu), ruff/format clean.
- Nächster Schritt: Step 1 — Backend-MVP (`/api/v1/specs`, `/api/v1/render` offline mit `ReplayCacheClient`, Fehler-Mapping, Pytest-Suite).

## 2026-05-19 — Phase 1d Step 1: Backend-MVP `/api/v1/specs` + `/api/v1/render`
- `apps/web/backend/src/speccify_web_backend/`: neue Module `settings.py`, `services/render.py`, `routes/specs.py`, `routes/render.py`; `app.py` erweitert (Router-Wiring + CORS für localhost:3000 + Settings auf `app.state`).
- `settings.Settings.from_env()` resolved `SPECCIFY_PROJECT_ROOT` / `SPECCIFY_REGISTRY_PATH` / `SPECCIFY_CACHE_DIR` mit Repo-Defaults (Registry → `<repo>/registry-fixtures/`, Cache → `<repo>/tests/fixtures/llm-cache/`).
- `services/render.render_spec_from_yaml`: framework-agnostischer Wrapper über `speccify_core.render_for_target`; baut `Spec` direkt aus YAML-Bytes (kein Registry-Roundtrip → editierte YAML funktioniert syntaktisch, endet im Cache-Miss-Pfad). Offline-only via `ReplayCacheClient(offline=True)`.
- `routes/specs.list_specs`: listet Pseudo-Registry-Einträge (`@scope/name@latest` + raw YAML). Plan-Abweichung: nicht `<repo>/specs/*.yaml` (`spec://name`-IDs, keine Cache-Hits) — Begründung im Plan dokumentiert.
- `routes/render.render_spec`: Pydantic-Body `{spec_id, version, spec_yaml, target}`; Fehler-Mapping `cache_miss` 422 (mit Maintainer-Hinweis auf `scripts/record_llm_cache.py`), `spec_invalid` 400 (YAML-Parse + `SpecLoaderError`/`CodegenError`), `unknown_target` 400, `bad_request` 400.
- Tests: `test_specs_route.py` (2) + `test_render_route.py` (5) → **182 Tests grün** (175 → 182); ruff check + ruff format --check clean (nach 1× `--fix` + format-Lauf für die zwei neuen Module).
- Step 1 abgehakt im Plan; Cross-Consistency-Test bewusst in Step 4 verschoben. Nächster Schritt: Step 2 (Frontend-Skeleton) nach User-Commit.

## 2026-05-19 — Phase 1d Steps 2+3 (Frontend-Skeleton + Render-Flow)

- Frontend-Stack: Next.js 15.5.18, React 19.2.6, TypeScript 5.9.3 strict, Monaco
  via `@monaco-editor/react@4.7.0`, zod 3.25.76. Paket-Manager pnpm@10.33.3,
  Node ≥22 LTS (`.nvmrc`, `engines.node`).
- Files unter `apps/web/frontend/`:
  - `package.json`, `tsconfig.json` (`@/*`-Alias), `next.config.ts`
    (rewrites `/api/v1/*` → `http://localhost:8000`, override via
    `SPECCIFY_BACKEND_URL`), `next-env.d.ts`, `.nvmrc`, `.gitignore`.
  - `app/layout.tsx`, `app/page.tsx` (Landing), `app/playground/page.tsx`
    (Client-Component, kein State-Mgmt-Lib, `useEffect`/`useState`/
    `useCallback`/`useMemo`).
  - `components/{SpecPicker,SpecEditor,RenderOutput,ErrorPanel}.tsx`.
    Monaco lazy via `next/dynamic({ ssr:false })`.
  - `lib/api.ts` mit `listSpecs`/`renderSpec` + zod-Schemas + `ApiError`-
    Klasse, die `detail.{error_code,message,hint,details}` aus
    FastAPI-HTTPException extrahiert.
- `apps/web/README.md` ersetzt (altes Placeholder gelöscht): Stack, Quickstart
  (Backend `uv run speccify-web-backend` + Frontend `pnpm dev`), Endpoint-Liste,
  Fehler-Codes, Limitierungen, Master-Plan-Link.
- Verifikation: `pnpm install` (307 Packages, 8.7 s), `pnpm typecheck`
  (tsc --noEmit, 0 Fehler), `pnpm build` (5 statische Routen,
  `/playground` 16.7 kB / 118 kB First-Load). Backend: `uv run pytest`
  **182 grün** nach `uv sync --reinstall` (bekanntes editable-Side-Quest);
  `ruff check` + `ruff format --check` clean.
- Plan-Sync: `phase-1d-browser-playground.md` Steps 2+3 abgehakt; Playwright-
  Smoke explizit auf Step 5 (CI-Job) verschoben mit Begründung. `status.md`
  und Top-Level-README bleiben für Step 4 (Cross-Consistency) offen.
- Kein eigener Commit gemäß `rules.md`; User entscheidet über Commit-Zeitpunkt.
- Nächster Schritt: Step 4 — Cross-Consistency-Test CLI ↔ MCP ↔ Web byte-
  identisch + Top-Level-README-Abschnitt „Browser-Playground".

## 2026-05-21 — Phase 1d Phasen-Plan archiviert
- `phase-1d-browser-playground.md` liegt unter `.agent/plans/archive/`
  (`isActive: false`); Datei-History via `git mv` erhalten.
- `AGENTS.md` „Aktuelle Phase" referenziert nur noch den Archiv-Pfad;
  1d in Archiv-Liste aufgenommen (analog 1a/1b/1c). Tag-Vorschlag
  `v0.4.0-phase-1d` bleibt offen an User (vgl. `rules.md`).
- `.agent/status.md` Meta-Block + „Nächste Schritte" auf Archiv-Zustand
  umgestellt; nächster offener Punkt: Phase-2-Plan-Entwurf nach User-Tag.
- Keine Code-/Test-Änderungen; `uv run pytest` als Sanity erwartet 183 grün.

## 2026-05-22 — Phase-2-Plan-Skelett (Registry-MVP)

- Neuer Phasen-Plan `.agent/plans/phase-2-registry-mvp.md` (`isActive: true`) als
  Skelett analog zu früheren Phasen-Kickoffs angelegt. Scope: Django-Backend
  unter `registry/` (User, Scope, Spec, SpecVersion, Token+TOTP-2FA),
  REST-API `/api/v1/registry/...` (publish/fetch/versions/search/yank/whoami/
  tokens), CLI-Commands `login`/`logout`/`publish`/`search`/`yank`/`whoami`,
  MCP-Tools `search`/`publish`/`yank` (Auth via `SPECCIFY_TOKEN`), Web-UI
  (Tendenz Django-Templates), Lockfile-Bump auf `schema_version: 2` mit
  optionalem `signature`-Feld (sigstore vorbereitet) und `yank_status`,
  zweistufige Registry-Resolution (lokal → Remote) mit registry-gebundenen
  Scopes gegen Dependency Confusion, Workspaces nativ (optional / vertagbar
  nach Phase 3).
- Explizit Out of Scope in Phase 2: volle sigstore-Verifikation, aktive
  Federation, OAuth/WebAuthn, Discovery-Features, Live-LLM-Cloud-Rendering,
  Live-Domain-Deploy.
- 10 Open Questions als Round-1-Klärungspunkte für User (Backend-Framework
  final, Web-UI-Stack, Storage-Backend, 2FA-Methode, Token-Format, Login-UX,
  Scope-Vergabe, Workspaces in 2 vs. 3, Web-UI in `apps/web/` vs. `registry/`,
  Domain-Status `speccify.io`). Stages 0–9 als Skelett; Delivery-Steps folgen
  in Round 2 nach Klärung der Open Questions.
- `.agent/status.md` „Nächste Schritte" um Phase-2-Plan-Kickoff-Eintrag
  ergänzt; Tag-Vorschlag `v0.4.0-phase-1d` bleibt weiterhin offen an User
  (nicht selbst gesetzt, vgl. `rules.md`).
- Keine Code-/Test-Änderungen.

## 2026-07-23 (OSS-Pivot P1 — Aufräumen + Pivot-Plan)
- **Pivot-Plan** [`plans/pivot-open-source-git-composer.md`](./plans/pivot-open-source-git-composer.md)
  erstellt und nach User-Refinement umgestellt: Composer-Fast-Track
  (P1 Aufräumen → P2 API/Mocks/Komposition → P3 visueller Composer →
  P4 Projekt-Builds → P5 Git-Quellen → P6 Launch). Composer baut Apps
  **und** Composite-Komponenten; `composition:` wird gemeinsames
  Schema-Konzept.
- **P1 umgesetzt** auf Branch `feat/oss-pivot` (3 Commits): Registry-
  Rückbau (`registry/`, CLI-Remote-Schreibpfad, MCP `publish`/`yank`,
  CI-Job, dev-up.sh, Docs; Archiv-Branch `archive/pre-oss-pivot-registry`),
  `example-commercial-specs/` gelöscht, 75-Pfad-Sweep als 60-Pfad-Sweep
  (Local/CLI/MCP/Web) nach `apps/web/backend/tests/` portiert,
  CLI-Referenz regeneriert (7 Seiten), OSS-Hygiene (CONTRIBUTING, CoC,
  Issue-Templates), Master-Plan + agent.md + README auf Pivot umgestellt.
- **Verifikation**: 372 Root-Pytest grün (357 + 15 Sweep-Zellen), ruff
  check/format clean, `gen_cli_docs --check` + `sync_docs_to_site --check`
  grün, MCP-stdio-Smoke OK, example-project Offline-E2E OK. Mypy: 11
  vorbestehende Fehler, unverändert zur Baseline (lokale Mypy-Version
  strenger als CI).
- `RemoteRegistry` in `core/` bewusst behalten (MockTransport-Tests
  self-contained); wird in P5 durch `GitRegistry` ersetzt/ergänzt.

## 2026-07-23 (P2-Plan — API-Vertrag, Komposition & Mock-Generator)
- **Aktiver Phasen-Plan** [`plans/archive/phase-p2-api-composition-mocks.md`](./plans/archive/phase-p2-api-composition-mocks.md)
  erstellt. Stage 0 entfällt als Frage-Runde: Entscheidungen D1–D6 per
  User-Delegation („folge deinen Empfehlungen") direkt dokumentiert —
  Logic-Mocks fixture-basiert (D1), keine State-Machine / `behavior:`
  reserviert (D2), explizites Mapping statt Auto-Forwarding in
  Composites (D3), Phase-7-S4 (`screenshots[].tolerance`) reitet im
  Schema-Bump mit (D4), Spec-Schema v1 mit `schema_version`-Feld +
  v0-Loader-Migration (D5), Mocks lockfile-frei (D6).
- Stages 1–6 definiert: Schema v1 → `composition:` + Typprüfung (+ neue
  Specs `@org/text-input`, `@org/search-bar`) → Mock-Codegen React
  (`speccify mock`) → API-Conformance-Backend (TS-Harness, Mock ↔ LLM) →
  MCP-Tool `mock` + `POST /api/v1/mock` + Cross-Consistency → Doku/Wrap-up.
  Ziel-Tag-Vorschlag `v0.12.0-p2-api-mocks`.
- Größtes benanntes Risiko: Spec-Schema-Bump invalidiert den
  `spec_sha256`-gebundenen LLM-Replay-Cache — Mitigation (kanonisierter
  Cache-Key vs. Maintainer-Re-Recording) ist erste Entscheidung in Stage 1.
- Phase-7-Plan nach `archive/` verschoben (D4-Vermerk im Header); Pivot-Plan
  aktualisiert (Fragen 4/5/9/10 → entschieden, „Schema v3" → Spec-Schema v1).
- Nur Plan-/Doku-Änderungen, kein Code.

## 2026-07-24 (P2 Stages 1–3 + 5 — Schema v1, Komposition, Mock-Codegen)
- **User-Refinement**: „Start bei Null" — kein v0-Migrationspfad; Composer
  muss vom Agent selbst bedienbar sein; Composer wird später Tauri-2-App
  (nichts bauen, was dem entgegensteht). In P2-/Pivot-Plan verankert.
- **Stage 1**: `schema/spec.schema.json` hart auf v1 (`schema_version: 1`
  Pflicht, `api:`-Block, `kind`-Enum, `screenshots[].tolerance`).
  Wiring-Key `when:` statt `on:` (YAML-1.1 parst `on` als Boolean!).
  Alle 7 Referenz-Specs v1 (specs/ + registry-fixtures via Transform;
  login-screen-Fixture behält `^0.1.1`-Diamond, button 0.1.1 Bump).
- **Stage 2**: `core/api.py` (ComponentApi, TypeRef, types_compatible,
  literal_assignable mit Enum-Mitgliedschaft) + `core/composition.py`
  (parse + validate gegen Kind-APIs, Fehler mit JSON-Pfaden). Resolver
  zählt `composition.uses` transitiv. 22 neue Tests.
- **Cache-Re-Key**: LLM-Adapter lesen `api:` (PROMPT_VERSION 0.2.0,
  Stub TEMPLATE_VERSION 0.2.0); 18 Cache-Einträge mechanisch auf neue
  Keys umgezogen (Responses byte-identisch — kein Bedrock-Recording).
  example-project Lockfile + out/ regeneriert.
- **Stage 3**: `codegen/mock_react.py` (Pin `p2-mock-react v0.1.0`):
  Leaf-Mocks (typisierte Props, Event-Chips mit Payload-Synthese aus
  gleichnamigen Props, Slots als ReactNode), Composite-Mocks (Kind-Baum,
  wired-State für `set`, Callbacks für `emit`, `map_to`-Forwarding),
  Logic-Mocks aus `api.fixtures` (D1). Closure Button/TextInput/SearchBar
  typecheckt via gepinntem tsc (ReactToolchainDriver, `@conformance`).
- **Stage 5**: CLI `speccify mock` (8. Command, Doku regeneriert),
  MCP-Tool `mock` (7 Tools, Smoke angepasst), Web `POST /api/v1/mock`
  (Composer-Palette-Vorbau); Cross-Consistency CLI == Web byte-identisch.
- **Stage 4 vertagt** hinter P3 (tsc-Basisebene läuft; voller Harness
  nach Composer-Erkenntnissen). Doku: `docs/component-api-and-mocks.md`.
- **Verifikation**: 411 Pytest grün, Mock-tsc-Conformance grün,
  MCP-stdio-Smoke OK, ruff check/format clean, `gen_cli_docs --check` grün.
- **macOS-Venv-Ärger**: Quarantäne versteckt `.pth` re-kurrierend (auch
  frisch geschriebene Dateien!). Session-Workaround: `PYTHONPATH` auf die
  vier `src/`-Verzeichnisse setzen — umgeht `.pth` komplett.

## 2026-07-24 (P3 — Composer-MVP)
- **Backend (P3-API)**: `services/composer.py` + `routes/composer.py` —
  `GET /api/v1/specs/{scope}/{name}` (Detail mit API-Contract-JSON inkl.
  Typ-`kind`/`enumValues` + aufgelöste Kind-Contracts), `POST /api/v1/validate`
  (Schema + Kompositions-Typprüfung; inhaltliche Fehler als Issues, nie 4xx),
  `POST /api/v1/specs` (Save in Registry; Pfad aus id/version; Gespeichertes
  sofort Palette-/Mock-fähig → rekursive Komposition). Core-Refactor:
  `resolve_composition_children`/`parse_child_ref` von mock_react nach
  `composition.py`. CORS: :5173 + tauri://localhost.
- **Frontend**: neuer pnpm-Member `apps/composer/` — Vite-React-SPA
  (`base: "./"`, statischer Export, kein SSR → Tauri-2-fähig; `VITE_API_BASE`
  für spätere Sidecar-Shell). Palette („+ als Kind"/„öffnen"), Canvas mit
  interpretierten Mocks (Contract-JSON statt TSX-Compiler im Browser;
  Semantik identisch zu mock_react inkl. Payload-Synthese), Wiring-Simulation
  (`simulate.ts`: set→State, emit→Event-Log, Quellen payload/props/Literal),
  Inspector (typisierte Prop-Editoren, Verdrahtungs-Formular mit
  contract-getriebenen Dropdowns, eigene Events/Props inkl. map_to, Spec-Meta),
  YAML-Panel mit Round-Trip („übernehmen" lädt editiertes YAML zurück).
- **Agent-Bedienbarkeit bewiesen**: `test_composer_agent_flow.py` baut die
  Composite `@org/filter-bar` komplett headless über die HTTP-API
  (Palette → Contracts → validieren → speichern → Detail → Mock-Closure →
  wieder in der Palette). 9 weitere Composer-Routen-Tests.
- **Integration**: CI-Job `apps/composer build (vite spa)`; `dev-up.sh`
  startet Composer auf :5173; `docs/composer.md` + README-Abschnitt;
  Pivot-Plan P3 als „MVP geliefert" markiert (offene Verfeinerungen notiert).
- **Verifikation**: 420 Pytest grün, `pnpm --filter speccify-composer build`
  grün (tsc + Vite, im ersten Anlauf), ruff check/format clean.
- Tag-Vorschlag an User: `v0.13.0-p3-composer-mvp`.

## 2026-07-24 (P3-Verfeinerung Runde 1 — Slot-Befüllen, Undo/Redo, UI-Smoke)
- **Slot-Befüllen (Canvas)**: `doc.ts`-Tree jetzt rekursiv — `findTreeNode`,
  `findSiblingList`, `detachNode` (prunt leere Slot-Listen), `collectAliases`,
  `nodePlacement`, `moveNodeToSlot` (Zyklen-Guard: eigener Teilbaum = No-Op).
  `addChild(doc, child, target?)` fügt in `tree[].slots[<slot>]` ein;
  `removeChild` entfernt Teilbäume inkl. uses/wiring/map_to aller Nachfahren;
  `moveNode`/`setTreeProp` arbeiten auf der Geschwister-Liste. Canvas rendert
  Slot-Zonen (Klick = Einfüge-Ziel-Toggle, Highlight, rekursive MockNodes);
  Inspector-Knoten-Panel bekam „Platzierung"-Select. simulate.ts nutzt
  findTreeNode (verdrahtete Props funktionieren auch verschachtelt).
- **Undo/Redo (App.tsx)**: Snapshot = `{doc, children}` (Kind-Contracts gehören
  zur Editier-Einheit). past/future-Stacks (Limit 100), Inspector-Edits
  koalesziert (<800 ms Burst = 1 Schritt), Undo/Redo resettet Simulation +
  Einfüge-Ziel und fixt Selektion. ⌘Z/⇧⌘Z global, außer in
  INPUT/TEXTAREA/SELECT (natives Text-Undo). Inspector-Entfernen läuft jetzt
  über `onRemoveNode` in App (vorher 2 setState-Aufrufe = hätte 2
  History-Einträge ergeben).
- **Playwright-UI-Smoke**: `apps/composer/e2e/composer-smoke.spec.ts` (3 Tests)
  + `playwright.config.ts` (2 webServer) + `start-backend.sh` (Wegwerf-Kopie
  der registry-fixtures via SPECCIFY_REGISTRY_PATH, Port 8788; Vite :5199 via
  `COMPOSER_PROXY_TARGET` in vite.config.ts — kollisionsfrei zu dev-up.sh).
  Pin `@playwright/test@1.44.0` (= Visual-Regression-Browser-Build 1117).
  CI-Job `apps/composer ui smoke (playwright)` in ci.yml (uv sync + pnpm +
  Browser-Cache + `--with-deps chromium`). Skripte: `pnpm run composer:e2e`.
- **Side-Quest macOS**: Chromium-1117-Download hing nach vollständigem Zip
  (141 MB, `unzip -t` OK) — manuell nach `~/Library/Caches/ms-playwright/
  chromium-1117` entpackt + `INSTALLATION_COMPLETE`-Marker gesetzt. Ein früher
  abgebrochener Download hatte einen 208K-Stub hinterlassen (Launch-Fehler
  `spawn -88`) — bei dem Symptom Cache-Dir löschen und neu entpacken.
- **Doku**: docs/composer.md (Slot-Zonen, Undo/Redo, UI-Smoke-Abschnitt,
  MVP-Grenzen aktualisiert); Pivot-Plan P3 „Verfeinerung Runde 1" markiert.
- **Verifikation**: 3/3 Playwright grün (6,2 s, erster Lauf), Composer-
  Typecheck + Build grün (269 kB), 420 Pytest grün (Python unverändert).
- Tag-Vorschlag an User: `v0.14.0-p3-composer-verfeinerung-1`.

## 2026-07-24 (Rust-Neustart — Plan-Kickoff, kein Code)
- **Neuer Workstream angelegt** (BO-Richtungsentscheidung vom selben Tag):
  Toolkit + MCPs aus dotagent (`~/Desktop/Work/Articles/dotagent`) werden
  in diesem Repo **neu in Rust geschrieben** statt als Python-Pakete
  migriert; dotagent bleibt Referenzimplementierung (Exec-MCP-Referenz:
  dotagent-Commit `2949d1d`). Kein PyPI, kein App Store/Sandboxing.
- **`.agent/plans/archive/rust-neustart-toolkit-mcps.md`** (`isActive: true`):
  vollständige Einweisung für Sessions ohne dotagent-Vorwissen —
  Hintergrund, Rust/Python-Schnitt (Engine + Composer-Backend bleiben
  Python), Wire-Kontrakt `POST /stream` (iKanbanAi hängt dran),
  Actions-Datenmodell (Vorlage iKanbanAi-`ProjectAction`), Stufen R0–R5,
  Referenz-Tabelle (dotagent-/iKanbanAi-Dateipfade).
- **`status.md`**: Workstream unter „Nächste Schritte" verlinkt; die
  Produkt-Roadmap (P3-Verfeinerung etc.) läuft parallel weiter.
- **Hinweis für später**: `.agent/` ist hier getrackt (inkl. Chats) —
  vor einer Public-Schaltung des Repos gleiches Untracking prüfen wie in
  dotagent (`583ae11`); der neue Plan nennt private Pfade/Projekte.
- Nächster Schritt: **R0** — Cargo-Workspace (`crates/`), Actions-Schema
  mit iKanbanAi abgleichen, Kontrakt-Testsuite gegen den laufenden
  Python-Exec-MCP (Port 8765) spezifizieren.

## 2026-07-24 (Rust-Migration R0 + Desktop-App-Übernahme A0)
- **BO-Umpriorisierung** (nach R0-Lieferung): App-Übernahme + Composer-
  Integration zuerst (neuer aktiver Plan `desktop-app-und-composer.md`,
  Entscheidungen D1–D5 dokumentiert), Rust-Portierung danach (Plan
  `rust-neustart-toolkit-mcps.md` heißt jetzt „Migration nach Rust").
- **R0 geliefert** (Commit 4c166df): Cargo-Workspace (Pin 1.97.1,
  `crates/exec-mcp` + `crates/discovery-mcp` als Skelette, CI-Job `rust
  workspace` mit fmt/clippy -D warnings/build/test);
  `schema/actions.schema.json` (wire-kompatibel zu iKanbanAi-
  ProjectAction: Array, `details`→`description`; Ablage
  `.agent/actions.json` + `~/.speccify/actions.json`, Projekt gewinnt);
  `docs/exec-mcp-contract.md` (kompletter Wire-Vertrag aus dotagent
  2949d1d: JSON-RPC bound/multi, exakte Fehlertexte, Allowlist-Token-
  Präfix + Pending-Dedup, SSE-Framing, 600s/ungekappt/Stop-Semantik,
  23-Tests-Checkliste); `scripts/exec_mcp_contract.py` (28 Szenarien,
  Normalisierung duration/ts/serverInfo/Banner/Pfade, Datei-Effekte;
  **28/28 Parität Referenz-vs-Referenz gegen laufenden dotagent-Server
  verifiziert**). Rust via brew-rustup installiert (stable 1.97.1 war
  als Toolchain schon vorhanden; cargo liegt unter
  ~/.rustup/toolchains/*/bin — PATH entsprechend setzen).
- **A0 geliefert**: dotagent `app/dashboard` (2949d1d) → `apps/desktop`
  kopiert (ohne Artefakte), Rebranding Speccify/`io.speccify.desktop`/
  `speccify-desktop` (+`speccify_desktop_lib`), pnpm- und Cargo-
  Workspace-Einbindung, Root-Skripte `desktop:*`, README neu. CLI-Bridge
  `run_dotagent` bewusst unverändert (D1) — stirbt erst mit der
  Rust-Migration. CI: `desktop-frontend`-Job; `rust`-Job excludet das
  Tauri-Crate (Linux-webkit2gtk). Ein fmt-Diff in lib.rs behoben.
- **Verifikation**: tsc + Vite grün (211 kB), `cargo build/clippy
  -p speccify-desktop` grün, `cargo test --workspace --exclude
  speccify-desktop` grün, `tauri build` Release-Bundle grün (.app unter
  target/release/bundle/). Offen: BO-Check `pnpm run desktop:dev`.
- Nächster Schritt: **A1 Composer-Fenster** (SPA bündeln, Laufzeit-
  API-Base, Supervisor spawnt speccify-web-backend pro Fenster).

## 2026-07-24 (Desktop A1 — Composer-Fenster in der App)
- **Architektur (D4 präzisiert)**: Backend serviert die gebaute
  Composer-SPA selbst unter `/ui` (StaticFiles html=True, Settings-Feld
  `composer_dist` + Env `SPECCIFY_COMPOSER_DIST`; ohne Build kein Mount).
  Composer-Fenster lädt `http://127.0.0.1:<port>/ui/` → API same-origin,
  kein CORS, keine Fenster-Capabilities nötig, kein doppeltes Bundling.
  `window.__SPECCIFY_API__` in api.ts als Laufzeit-Override ergänzt.
- **Rust (`open_composer`)**: ~-Expansion, Vorprüfungen mit klaren
  Fehlermeldungen (venv-Binary fehlt → `uv sync`; dist fehlt →
  `pnpm run composer:build`), freier Port via bind(0), Spawn
  `.venv/bin/speccify-web-backend` (cwd=Repo, PATH-Anreicherung,
  PYTHONPATH-Workaround gegen macOS-Quarantäne), Logs in den Supervisor
  (`composer-backend-<port>`), Port-Wait 20 s (sonst Kill + Fehler),
  WebviewWindow auf /ui/, `WindowEvent::Destroyed` → Kill + proc-exit.
- **UI**: neuer Default-Tab „Composer" (Repo-Pfad-Feld mit localStorage,
  Default `~/Desktop/Work/speccify`, ActionButton + Fehlerbox).
- **Verifikation**: 422 Pytest grün (inkl. 2 neuer
  `test_composer_ui_mount.py`), ruff clean, Composer-Playwright 3/3,
  tsc+Vite (desktop 212 kB, composer 269 kB) grün, cargo build/clippy
  -p speccify-desktop grün, /ui-Livecheck grün, `tauri build` grün.
- Offen: manueller BO-Check (`pnpm run desktop:dev` → Composer-Tab).

## 2026-07-24 (Walkthrough-Doku + FilePicker)
- BO-Feedback nach erstem App-Start („hat geklappt"): (1)
  `docs/composer-tristate-walkthrough.md` — Tri-State-Button als
  Segmented Control aus drei Basis-Buttons (Aliasse aus/teils/an wegen
  YAML-1.1-off/on-Falle; Alias-Rename nur via YAML-Round-Trip; 12
  Wiring-Regeln; Referenz-YAML headless verifiziert: validate/save/mock
  grün, Mock trägt onChanged + Variant-Sets). Erkenntnis dokumentiert:
  echtes Zyklieren (EIN Button, drei Zustände) braucht behavior:/
  bedingte Wiring — Kandidat für die Verfeinerung. (2)
  tauri-plugin-dialog + „Auswählen…"-Button (Verzeichnis-Picker) am
  Repo-Pfad-Feld des Composer-Tabs (Capability dialog:default).
- PATH-Fix beim BO: brew-rustup hat keine ~/.cargo/bin-Shims →
  `/opt/homebrew/opt/rustup/bin` in ~/.zshrc exportiert (desktop:dev
  lief vorher auf „cargo metadata: No such file or directory").

## 2026-07-25 (Plan: Toolkit-Vollausbau)
- BO-Zielvorgabe: vor weiterer Composer-/Spec-Schärfung den Infrastruktur-
  Teil fertigmachen (iKanbanAi wartet). Neuer aktiver Plan
  `toolkit-discovery-terminal.md` (Entwurf zum Refinen, 8 Open Questions):
  Discovery-MCP inkl. client_config, Toolbox = dotagent-TOML 1:1
  (builtin/global/workingdir), MCPs Exec/Parallels(Port)/Playwright
  (extern via npx-Manifest), eigene Tools/MCPs via Scaffold ins Working
  Dir, Settings-Tab (~/.speccify/settings.json, Einweisungs-Dateien per
  Klick), Terminal-Sidebar (xterm.js + portable-pty, zsh/bash, Working
  Dir, Windows zurückgestellt), ask_bo-Chat-Elemente als App-gehosteter
  desktop-ui-MCP (Schema 1:1 iKanbanAi ChatInteraction:
  buttons/multi_select/form — Referenz gelesen: ask_bo-Tool + Answer als
  Tool-Result). Empfohlene Reihenfolge T1 Settings → T2 Toolbox → T3
  Discovery (iKanbanAi-Meilenstein) → T4 Exec-Rust-Port (Harness-Gate)
  → T5 Parallels/Playwright → T6 Terminal → T7 ask_bo → T8 Wrap-up.
- Plan-Hygiene: desktop-app-und-composer.md abgeschlossen (A0/A1 vom BO
  abgenommen, A2 aufgegangen); rust-neustart-toolkit-mcps.md auf
  Kontrakt-Referenz zurückgestuft (R1/R2-Ausführung = T4/T3).

## 2026-07-25 (T0-Entscheidungen + T1 Settings)
- BO-Antworten Runde 1 in den Toolkit-Plan eingepflegt (alle 8: Reihenfolge
  bestätigt, iKanbanAi braucht Aktionen UND mcp_list; 8767 + stdio; TOML
  1:1 inkl. kb; EIN Working Dir; Autostart-Command in Settings; ask_bo
  mit Timeout-Semantik; Parallels asap direkt nach Exec; Einweisungs-Trio
  ok, andere Agents später).
- T1 geliefert: settings.rs (get/save_settings, briefing_status,
  create_briefing_file — nie überschreiben; Templates via include_str!),
  SettingsView (Working-Dir-Picker, Autostart-Command, Einweisungs-
  Status mit Klick-Anlage), 6. Tab „Settings". Templates: CLAUDE.md
  (Speccify-Kurzkontext + MCP-Wegweiser), .mcp.json (discovery/exec/
  playwright), .claude/settings.json (enableAllProjectMcpServers).
- Verifikation: cargo test 2/2 + clippy/fmt clean, tsc+Vite grün.
- Nächster Schritt: T2 Toolbox nativ (Rust-Manifest-Parser, builtin-
  Manifeste, Library-Tab nativ, Scaffold).

## 2026-07-25 (T2 Toolbox nativ)
- `crates/toolbox`: Parser 1:1 nach dotagent-Semantik (Pflichtfelder,
  kind/transport-Validierung, Warnungen statt Abbruch beim Verzeichnis-
  Laden), load_all mit Layer-Vorrang workingdir > global > builtin,
  Scaffold mit Slug-Check + Nie-Überschreiben. 5 builtin-Manifeste
  (exec/parallels übergangsweise auf dotagent-CLI — Kommentar im TOML
  verweist auf T4/T5-Wechsel). App-Commands toolbox_list/toolbox_scaffold;
  LibraryView nativ (source-Labels builtin/global/workingdir, run-Zeile
  sichtbar, Scaffold-Formular). settings::resolve_working_dir pub(crate).
- Verifikation: cargo test 7/7, clippy --workspace -D warnings clean,
  fmt clean, tsc+Vite grün.
- Nächster Schritt: T3 Discovery-MCP (JSON-RPC http+stdio, mcp_list mit
  client_config, tools_list, actions_propose, scaffold) — iKanbanAi-
  Meilenstein.

## 2026-07-25 (T3 Discovery-MCP)
- `crates/mcp-core` eingezogen (Bedarfsfall aus R0 eingetreten: Discovery/
  Exec/Parallels/desktop-ui teilen den Unterbau): Dispatch nach
  docs/exec-mcp-contract.md-Semantik, tiny_http-Transport (Thread pro
  Request, roher Socket-Writer via into_writer als SSE-Grundlage für T4),
  stdio (ndjson). PARSE_ERROR/-32601/202-Verhalten im Unit-Test gepinnt.
- `crates/discovery-mcp`: DiscoveryMcp mit mcp_list/tools_list/
  actions_propose/scaffold (Details im Plan). client_config macht jeden
  Eintrag direkt in .mcp.json einhängbar — iKanbanAi bekommt Aktionen
  UND MCP-Liste (T0.1). Port-Konvention: exec 8765, parallels 8766,
  discovery 8767 (KNOWN_PORTS + --port-Args-Parsing).
- Verifikation: cargo test 8 Suiten grün (mcp-core 1, discovery 6,
  toolbox 5, settings 2 …), clippy --workspace -D warnings clean
  (2 collapsible_if via let-chains gefixt), Live-Smoke: GET-Banner,
  initialize, mcp_list-client_configs für alle 5 builtins,
  actions_propose→Datei mit source=agent/confirmed=false, stdio-initialize.
- T3-Rest notiert: Server-Tab-Umstellung (mit T4), iKanbanAi-Anbindung
  drüben. Nächster Schritt: T4 Rust-Exec-MCP gegen den Kontrakt-Harness.

## 2026-07-25 (T4 Rust-Exec-MCP — Kontrakt-Parität)
- `crates/exec-mcp` als Rust-Port der dotagent-Referenz: allowlist
  (Token-Präfix via shlex, consume Einmal-Freigaben, pending dedup,
  dep-freier civil_from_days-UTC), exec (run_command 20k-Cap +
  wait-timeout; stream via os_pipe fd-Merge stderr→stdout, ungekappt,
  Timeout-/Disconnect-Kill), server (run_command/run_action/list_actions,
  bound/multi, Fehlertexte 1:1). CLI http+stdio+/stream.
- **mcp-core Stream-Transport gefixt**: into_writer ließ die Keep-alive-
  Verbindung offen → Client-Hang. Umgestellt auf tiny_http-Response mit
  ChannelReader (chunked, sauberer 0-Chunk-Abschluss); ChannelWriter
  liefert BrokenPipe wenn der Reader wegfällt → Disconnect-Kill bleibt.
- **Gate grün: exec_mcp_contract.py 28/28 Parität** Rust-Kandidat vs.
  laufende dotagent-Referenz. 10 exec-Tests (inkl. Cap/Timeout/Disconnect-
  Lebensdauer). clippy --workspace -D warnings clean, fmt clean.
- builtin speccify-exec.toml → `speccify-exec-mcp --port 8765`.
- Offen (mit T5): 8765-Umschaltung im Betrieb + Server-Tab-Start/Stop.
  Nächster Schritt: T5 Parallels-Port + Playwright-Manifest.

## 2026-07-25 (T5 Parallels-Port + Playwright)
- Allowlist nach mcp-core gehoben (git mv), konfigurierbare Dateinamen
  (with_files) + seed_if_absent; Exec nutzt sie unverändert, Harness
  weiterhin 28/28. mcp-core bekam shlex-Dep.
- `crates/parallels-mcp`: mac_to_vm_path, build_exec_argv (chcp/pushd/
  dotnet-Vollpfad/list2cmdline-Quoting), run_prlctl mit injizierbarem
  Runner (real = spawn+wait-timeout), 5 VM-Tools, eigene Allowlist
  (parallels-*.json, Default dotnet build/test/run geseedet). CLI
  http+stdio, --project/--vm/--home. 4 Tests. **Live-Smoke gegen echtes
  prlctl: vm_list zeigt reale VM „Windows 11".**
- builtin parallels-dotnet.toml → speccify-parallels-mcp --port 8766.
  Playwright bleibt npx-stdio-Manifest (T2), Discovery liefert client_config.
- Verifikation: cargo test 13 Suiten grün, clippy --workspace -D warnings
  clean, Exec-Harness 28/28, Desktop baut.
- Nächster Schritt: T6 Terminal-Seitenleiste (xterm.js + portable-pty,
  Autostart-Command aus Settings). Offen: 8765/8766-Umschaltung + Server-Tab.

## 2026-07-26 (T6 Terminal-Seitenleiste)
- Rust terminal.rs (portable-pty 0.9): terminal_open spawnt die Login-
  Shell (-l, $SHELL, TERM=xterm-256color) im Working Dir aus den Settings
  und tippt den Autostart-Command vor (tty puffert bis zum ersten Read);
  write/resize/kill-Commands; term-out/term-exit-Events aus dem Reader-
  Thread (lossy UTF-8); Terminals-Drop killt Shells beim App-Quit.
  PTY-Integrationstest ohne Tauri (spawn+pretype+read) grün.
- Frontend TerminalPanel (xterm.js 5.5 + fit): rechte Sidebar 520px,
  Nav-Toggle „⌨ Terminal", Restart-Knopf, Exit-Hinweis, ResizeObserver
  mit Nachfitten beim Einblenden. Mount erst beim ersten Öffnen (kein
  Autostart beim App-Start), danach persistent (Shell überlebt Toggle).
- Verifikation: cargo test 3 (inkl. PTY-Smoke), clippy clean, tsc+Vite
  grün, tauri build grün (Speccify.app + dmg).
- Offen: BO-Check (Settings→Working Dir + Autostart → ⌨ Terminal);
  T7 ask_bo als nächste Stufe; Server-Tab-Umstellung weiter offen.

## 2026-07-27 (T7 ask_bo-Chat-Elemente)
- desktop_ui.rs: App-gehosteter desktop-ui-MCP (:8768, mcp-core):
  ask_bo blockiert via Condvar bis zur Sidebar-Antwort (Timeout 300s →
  answered:false + interaction_id + „nicht erneut stellen"-Hint),
  ask_bo_result holt sie später (T0.6). AskBoRegistry geteilt zwischen
  Server-Thread (setup-Spawn) und Tauri-Command ask_bo_answer; Events
  ask-bo / ask-bo-answered. 3 Unit-Tests (Block/Timeout+Später/Schema).
- Frontend: AskBoPanel über dem Terminal in der (jetzt App-eigenen)
  Sidebar — buttons/multi_select/form nach iKanbanAi-ChatInteraction,
  leere Form-Eingabe ⇒ recommended, beantwortet = eingefroren ✓,
  unbekannte kinds → Hinweis (Vorwärts-Kompat). ask_bo öffnet die
  Sidebar automatisch (startet KEIN Terminal); „?"-Badge am Toggle.
  TerminalPanel auf Innen-Komponente umgebaut (Container in App).
- Templates: .mcp.json + CLAUDE.md um speccify-desktop-ui (:8768).
- Verifikation: cargo test 6 (3 neue ask_bo) + clippy/fmt clean,
  tsc+Vite grün, tauri build grün (Speccify.app + dmg).
- Offen: BO-E2E (Terminal-Agent ruft ask_bo → Sidebar), iKanbanAi-
  Schema-Abgleich drüben. Nächster Schritt: T8 Wrap-up (docs/toolkit.md,
  Server-Tab, Tag-Vorschlag).

## 2026-07-27 (BO-Findings: Terminal-Copy + ask_bo-Robustheit)
- Finding 1 (Kopieren): ⌘C kopiert die xterm-Selektion, ⌘V fügt ein —
  attachCustomKeyEventHandler + Tauri-Clipboard-Plugin (WKWebView-sicher;
  navigator.clipboard ist dort unzuverlässig). Ohne Selektion bleibt ⌘C
  unangetastet, ^C bleibt SIGINT. Capability clipboard-manager read/write.
- Finding 2 (ask_bo-UI kam nicht): Ursache nicht eindeutig reproduzierbar
  (Kandidaten: zweite App-Instanz hielt Port 8768, oder verpasstes Event).
  Strukturell abgesichert statt geflickt: (a) tauri-plugin-single-instance
  (als erstes Plugin registriert) — Doppel-Instanz-Klasse eliminiert;
  (b) Registry speichert Event-Payloads, neuer Command ask_bo_pending —
  die UI holt offene Fragen beim Mount UND alle 5s aktiv ab (Events nur
  noch Beschleuniger, nicht Träger); Event-Handler dedupliziert per id.
  Tests erweitert (pending vor/nach Antwort).
- Verifikation: cargo test 6 grün, clippy/fmt clean, tsc+Vite grün,
  tauri build grün. BO-Re-Test des ask_bo-Flows offen.

## 2026-07-27 (BO-Finding: Tastatur-Bedienung der ask_bo-Karten)
- ask_bo-Flow vom BO als funktionierend bestätigt (nach Single-Instance +
  Pending-Sync). Neues Finding: Listen-Antworten nicht per Pfeiltasten
  bedienbar. Umgesetzt: neueste offene Karte bekommt Auto-Fokus;
  buttons: ←/→ (auch ↑/↓) bewegt Auswahl ab Option 1 (= Empfehlung),
  Enter bestätigt, Ziffern 1–9 wählen direkt; multi_select: ↑/↓ + Space
  toggelt + Enter sendet; form: Enter springt zum nächsten Feld bzw.
  sendet am Ende (leer = Empfehlung). Kurze Tastatur-Hints in den Karten;
  Buttons/Checkboxen tabIndex=-1 (Fokus bleibt auf der Karte).
- Verifikation: tsc+Vite grün, tauri build grün.

## 2026-07-27 (T8 Wrap-up — Toolkit-Plan abgeschlossen)
- Server-Tab nativ: mcp_status (Toolbox-MCPs, Port-Probe, binary_found
  mit PATH-Hinweis, client_config), Start/Stop via Supervisor mit
  Live-Logs (proc-log), Config-Kopieren übers Clipboard-Plugin; stdio-
  Server als „startet der Client"; dotagent-CLI + Spike-Panel entfernt.
  http_port/probe_port/client_config in den toolbox-Crate gehoben,
  Discovery entdoppelt.
- docs/toolkit.md (Server-Tabelle, cargo install --path, Toolbox/
  Aktionen, Cockpit, Agent-Flow) + README-Abschnitt Desktop/Toolkit.
- Plan toolkit-discovery-terminal.md: T8 ✅, isActive false — T0–T8
  komplett. Tag-Vorschlag an BO: v0.16.0-toolkit-discovery-terminal.
- Verifikation: 13 Rust-Suiten + 6 Desktop-Tests grün, clippy clean,
  tsc+Vite grün, tauri build grün.

## 2026-07-27 (Übergabeplan an iKanbanAi)
- `~/Desktop/Work/iKanbanAi/.agent/plans/speccify-toolkit-integration.md`
  angelegt (vollständige Einweisung ohne Speccify-Vorwissen): Server-
  Tabelle mit Ports, Code-Befund drüben (nur Port-Kopplung, kein
  Namens-Match — Umschaltung wire-transparent; ExecMCPConfig 8765/8766),
  Discovery-Tool-Verträge mit Response-Shapes, ask_bo-Schema-Vertrag,
  Stufen K0 (Verifikation) / K1 (Exec-Umschaltung, nur Texte) / K2
  (Discovery-Client: globale Aktionen + mcp_list) / K3 (ask_bo-
  Fixture-Test), 3 Open Questions. Datei drüben bewusst NICHT committet
  (fremdes Repo — macht die iKanbanAi-Session).

## 2026-07-27 (R3 — dotagent komplett abgelöst)
- Zuschnitt: statt separatem Rust-CLI (Name `speccify` gehört der Python-
  Spec-Engine) sind die letzten dotagent-Funktionen native Tauri-Commands:
  system_cmd.rs mit doctor (Check-Liste bereinigt: pipx/dotagent raus,
  Claude Code rein; PATH+Well-Known, Symlink-Dedup, parallele Probes,
  Versions-Regex handgerollt), python_list/python_install (uv, Minors
  3.11–3.14), kb_list (chunks.json + faiss-Größe + books/<kb>/-Pfad-
  Auflösung; Format 1:1).
- run_dotagent/find_dotagent/DOTAGENT_BIN aus lib.rs entfernt;
  lib/dotagent.ts gelöscht → lib/system.ts (invoke); Views umgestellt.
- **Paritätstest** kb_list_matches_dotagent_reference (#[ignore], manuell)
  grün gegen die echten 6 KBs (Name/Books/Chunks/Titel identisch);
  doctor/kb-Shape-Tests laufen in der normalen Suite (9 Desktop-Tests).
- App-README neu (ohne CLI-Bridge), toolkit.md-Kopf: „Speccify ruft
  dotagent nirgends mehr auf". Rust-Plan R3 abgehakt — offen bleibt nur
  R5 (Signing/Notarisierung/Updater), danach dotagent archivieren.
- Verifikation: cargo test 9+1(ignored) grün, clippy/fmt clean, tsc+Vite
  grün, tauri build grün.

## 2026-07-29 (R5.1/R5.2 — App ohne Repo lauffähig)
- Feinplan `.agent/plans/archive/r5-distribution.md` (R5.1–R5.5, D1–D5): Weg von
  „läuft aus meinem Repo" zu „Download, in /Programme ziehen, läuft".
- **R5.1 Sidecars**: scripts/build_sidecars.sh baut exec/discovery/
  parallels-mcp und legt sie als binaries/<name>-<triple> ab;
  bundle.externalBin zieht sie nach Contents/MacOS. sidecar.rs löst
  Kommandos auf (mitgeliefert > PATH > expliziter Pfad); spawn_process
  und mcp_status nutzen das, der Server-Tab zeigt die Quelle.
- **R5.2 Engine-Payload**: build_engine_payload.sh baut die vier eigenen
  Wheels (uv build), exportiert gehashte Pins aus uv.lock und kopiert
  Composer-SPA + registry-fixtures + llm-cache nach src-tauri/resources
  (612 KB, gitignored, payload.json mit Hash). engine.rs: engine_status/
  engine_install (uv venv + uv pip install, Live-Log als proc-log,
  Marker installed.json). open_composer hat jetzt zwei Quellen —
  Repo-Modus (D3) vor gebündelter Engine, die Resources kommen per
  SPECCIFY_COMPOSER_DIST/_REGISTRY_PATH/_CACHE_DIR/_PROJECT_ROOT ins
  Backend. mcp_status bildet `uv run speccify-mcp` auf <venv>/bin ab und
  liefert absolute Pfade in der Client-Config (MCP-Clients haben unseren
  PATH nicht). Umgebungs-Tab: Engine-Karte mit Installation + Log.
- Bewusst offen: `uv` selbst als Sidecar (heute PATH/brew) — steht als
  R5.2.7 im Plan.
- Verifikation: 16 Desktop-Tests (9 + 7 neue) grün, 13 Rust-Suiten grün,
  clippy/fmt clean, tsc+Vite grün, 422 Pytest grün; tauri build → App
  enthält 3 Sidecars + Payload (17 MB, dmg 5,7 MB), startet aus dem
  Bundle (desktop-ui-MCP :8768 antwortet). Bootstrap 1:1 außerhalb des
  Repos durchgespielt: venv aus dem Payload, Backend liefert
  /api/v1/health 200, /ui/ 200, /api/v1/specs aus den Fixtures.

## 2026-07-29 (dev.sh — ein Kommando für die Desktop-App)
- `scripts/dev.sh`: prüft Werkzeuge (uv/pnpm/cargo, mit Install-Hinweis),
  lädt Deps (pnpm install, uv sync --all-packages + venv-Hygiene), baut
  Sidecars und Engine-Payload nur bei Bedarf (mtime-Vergleich gegen die
  Quellverzeichnisse) und startet dann `tauri dev` — mit `--release`
  stattdessen Bundle bauen + Speccify.app öffnen. Flags: --refresh,
  --no-start, --skip-engine, --help.
- Guard: läuft schon eine Instanz (Port 8768, Single-Instance-App), bricht
  das Skript mit Hinweis ab statt eine zweite ins Leere zu starten.
- Nebenbefund: 13 dist-info-Ordner ohne RECORD in `.venv` (Altlast der in
  P1 entfernten Django-Registry, `registry/` ist ungetrackt). uv kann sie
  nicht deinstallieren und meldet sie bei jedem Sync — dev.sh weist jetzt
  darauf hin (Aufräumen nur per frischem venv, bewusst nicht automatisch).
- Verifikation: zweiter Lauf 0,9 s und überspringt alles; `touch` an einer
  Composer-Quelle löst gezielt den Payload-Neubau aus (Hash identisch —
  der Payload-Build ist deterministisch); Guard beendet mit Exit-Code 1;
  422 Pytest weiterhin grün.

## 2026-07-31 (R5.3 vorbereitet — Signing/Notarisierung)
- `tauri.conf.json` → `bundle.macOS`: hardenedRuntime true,
  minimumSystemVersion 10.15 (Tauri-2-Minimum statt Default 10.13).
  Signing-Identity bewusst NICHT in der Config — sie kommt aus
  APPLE_SIGNING_IDENTITY, sonst könnte niemand ohne Zertifikat bauen.
  Keine Entitlements: Developer-ID ohne Sandbox braucht keine, und die
  Engine-venv läuft als eigener Prozess (Hardened Runtime beschränkt nur
  Code im eigenen Adressraum).
- `scripts/release_macos.sh`: Preflight (codesign/xcrun/spctl, Identity
  wirklich im Keychain via find-identity, Notarisierungs-Credentials —
  Abbruch VOR dem Compile), dann Sidecars + Payload + `tauri build`
  (Tauri signiert, notarisiert und stapelt selbst — Env-Namen aus dem
  CLI-Binary 2.11.4 verifiziert), dann Verifikation: codesign --verify
  --deep --strict, Authority/TeamIdentifier, jedes Sidecar einzeln auf
  Signatur + runtime-Flag, spctl, stapler validate für .app und .dmg.
  Flags: --no-notarize, --verify-only.
- `docs/release.md`: Zertifikat + App-Specific Password einrichten,
  Env-Variablen (nichts davon ins Repo), Verifikations-Kommandos,
  Quarantäne-Test auf fremdem Mac, Fehlerbild-Tabelle, notarytool log.
- Verifikation ohne Zertifikat: Preflight listet fehlende Credentials und
  endet mit Exit 1 (nichts gebaut); --verify-only diagnostiziert das
  aktuelle unsignierte Bundle korrekt (kein TeamIdentifier, Sidecars ohne
  Hardened Runtime, Gatekeeper lehnt ab, kein Ticket); tauri build mit
  neuer Config grün, LSMinimumSystemVersion = 10.15. Start-Smoke des
  Bundles ausgelassen — auf :8768 lief die dev-Instanz des BO.
- Offen und nur vom BO lösbar: Developer-ID-Zertifikat + App-Specific
  Password, dann ein echter release_macos.sh-Lauf.

## 2026-07-31 (R5.2.7 — uv als vierter Sidecar, letzte Vorbedingung weg)
- Vorgezogen vor R5.4: der Updater hängt wie R5.3 an BO-Zutaten
  (Signaturschlüssel, Hosting), das mitgelieferte uv dagegen ist heute
  komplett verifizierbar — und es war die letzte externe Vorbedingung
  der verteilten App ("erst brew install uv").
- `scripts/fetch_uv.sh`: lädt die gepinnte Version (0.12.0) samt der von
  astral-sh veröffentlichten .sha256, verifiziert, extrahiert nach
  binaries/uv-<triple>, legt einen Versions-Stempel an (idempotent) und
  kopiert einen Lizenzhinweis nach resources/licenses/ (uv ist MIT bzw.
  Apache-2.0). build_sidecars.sh ruft es auf, externalBin nimmt es mit.
- `search_dirs()` (system_cmd.rs) sucht jetzt das App-Bundle VOR dem
  PATH — sonst gewönne ein altes Homebrew-uv, und der Doctor meldete
  "uv fehlt", obwohl die App eins mitbringt. Damit nutzen Doctor,
  python_list und python_install automatisch das mitgelieferte Binary.
- Verifikation: uv 0.12.0 baut die Engine-venv aus dem Payload und das
  Backend antwortet daraus (health 200, /ui/ 200, specs aus Fixtures) —
  also die Version selbst geprüft, nicht nur den Download; fetch_uv.sh
  zweiter Lauf No-Op; `uv --version` und `uv venv` direkt aus
  Speccify.app/Contents/MacOS lauffähig; 17 Desktop-Tests (neu:
  bundle_dir_is_searched_first), 422 Pytest, clippy/fmt clean, tauri
  build grün. Kosten: App 17 → 55 MB, dmg 5,7 → 22 MB.

## 2026-08-01 (R5.4 — Updater verdrahtet, wartet auf den Public Key)
- BO-Entscheidung: er erzeugt das minisign-Schlüsselpaar selbst, ich baue
  alles andere und lasse den pubkey als einzige Lücke.
- tauri-plugin-updater (Rust + JS) eingebunden; plugins.updater mit
  Endpoint https://speccify.io/releases/latest.json und leerem pubkey,
  Capability updater:default (wird beim Build aufgelöst — im generierten
  ACL-Manifest enthalten).
- Kernpunkt: der Updater wird NUR angehängt, wenn ein pubkey hinterlegt
  ist (pubkey_from_plugin_config), sonst scheiterte der Plugin-Setup und
  die App startete nicht mehr. Kommando updater_status liefert der UI
  configured/current_version/endpoints.
- Umgebungs-Tab: Karte mit App-Version + "Nach Updates suchen"; das
  Plugin wird per dynamischem Import geladen und landet in einem eigenen
  1-KB-Chunk (Haupt-Bundle referenziert plugin:updater nicht). Ohne
  Schlüssel steht dort der Hinweis statt des Knopfes.
- release_macos.sh: schaltet createUpdaterArtifacts per --config ein,
  sobald TAURI_SIGNING_PRIVATE_KEY gesetzt ist, bricht ab wenn dabei der
  pubkey fehlt, und listet .app.tar.gz + .sig.
- docs/release.md: Schlüsselerzeugung, latest.json-Vertrag (Tauri-2-
  Format, signature = Inhalt der .sig, 204 = kein Update), Release-Ablauf.
- Verifikation: 18 Desktop-Tests grün (neu: updater_stays_off_without_a_
  pubkey inkl. Nicht-String-Fall), clippy/fmt clean, tsc grün, 422
  Pytest, tauri build grün (Hauptbinary 13,2 → 16,9 MB durch das Plugin);
  Preflight mit gesetztem Key und leerem pubkey bricht korrekt ab.
  Bundle-Start-Smoke erneut ausgelassen — auf :8768 lief die dev-Instanz
  des BO; die Empty-Key-Logik deckt der Unit-Test ab, das Plugin wird in
  dem Fall gar nicht erst registriert.

## 2026-08-02 (R5.5 — Download-Seite, dotagent-Ablösung dokumentiert)
- `apps/marketing/src/pages/download.astro`: Desktop-App-Seite mit
  Feature-Karten, Hinweis auf den einmaligen Engine-Bootstrap (braucht
  einmal Netz) und der Einschränkung Apple Silicon. Der dmg-Link
  erscheint nur bei gesetztem PUBLIC_DOWNLOAD_URL/_VERSION — sonst steht
  dort die Selbstbau-Anleitung (./scripts/dev.sh --release) statt eines
  toten Links; gleiches Muster wie PUBLIC_PLAYGROUND_URL auf /try-it/.
  Verlinkt aus Header, Footer und Hero; README um die Env-Tabelle ergänzt.
- Verifikation: beide Zustände gegen das gebaute HTML geprüft (ohne Vars
  Fallback-Text und kein .dmg im Markup; mit Vars der erwartete Link
  "Speccify 0.2.0 laden (.dmg)" und kein Fallback); 24 Seiten bauen grün,
  dist danach wieder ohne Release-URL erzeugt; 422 Pytest, ruff clean.
- dotagent: die verbliebenen Erwähnungen in Code/Doku sind
  Herkunftsnachweise und bleiben. docs/toolkit.md und der Kopf von
  scripts/exec_mcp_contract.py sagen jetzt sauber, was gilt — Speccify
  ruft dotagent nicht mehr auf, übrig sind zwei Regressions-Netze
  (Diff-Harness, #[ignore]-Paritätstest für kb_list).
- Das Archivieren des dotagent-Repos habe ich NICHT gemacht: fremdes Repo
  (~/Desktop/Work/Articles/dotagent), gleiche Linie wie beim
  iKanbanAi-Übergabeplan. Fertiger README-Text liegt im Plan (R5.5.3).

## 2026-08-04 (Plan-Ablage aufgeräumt)
- BO-Wunsch: Pläne sollen archiviert oder Entwürfe sein, genau einer aktiv;
  Schema wie in iKanbanAi (`lifecycle` / `status` / `sessionId` im
  Frontmatter, statt des hiesigen `isActive: true|false`).
- Alle 29 Pläne auf das neue Frontmatter umgestellt (Bodies unverändert);
  `isActive` ist raus, `sessionId` bleibt bzw. kommt aus dem Dateinamen.
- Sechs abgeschlossene Pläne nach `plans/archive/` verschoben
  (desktop-app-und-composer, phase-p2-api-composition-mocks,
  r5-distribution, rust-neustart-toolkit-mcps, speccify-plan,
  toolkit-discovery-terminal). Top-Level enthält jetzt nur noch
  `pivot-open-source-git-composer.md` (`lifecycle: active`) — die
  Produkt-Roadmap, an der als Nächstes gearbeitet wird. Leeres `next/`
  entfernt.
- Verweise in 11 Dateien nachgezogen (nur Pfade, keine Prosa). Nebenbei
  eine Altlast behoben: `.agent/agent.md` verlinkte mit repo-root-relativen
  Pfaden (`./.agent/plans/…`), obwohl es selbst in `.agent/` liegt — dadurch
  waren ~20 Links tot. Tote Plan-Links insgesamt: 23 → 6 (Rest sind
  Altlasten in `.junie/` und in den Marketing-Docs, kein Plan-Thema).
- Konvention in `agent.md` festgeschrieben (Abschnitt „Pläne: Ablage &
  Lebenszyklus"), damit künftige Sessions sie einhalten. Bewusst NICHT in
  `rules.md` — die ist ein Symlink auf `~/.agent/rules.md` und würde alle
  Projekte betreffen; das wäre BO-Entscheidung.
- Verifikation: 422 Pytest grün (Doku-Änderung, kein Code berührt);
  Frontmatter-Durchlauf geprüft (1 × active, 28 × done, kein isActive mehr).

## 2026-08-04 (P3-Rest: Mock-Bundle-Rendering + Drag & Drop — P3 abgeschlossen)
- Ausgangspunkt: der Canvas zeichnete den API-Contract nach (eigene
  Prop-Grids, eigene Event-Chips). Zwei Mock-Implementierungen, also
  garantierte Drift zum `speccify mock`-Output. Jetzt rendert der Canvas
  die generierten Dateien selbst.
- Backend: `POST /api/v1/mock/draft` (`services/mock.py::mock_draft_spec_yaml`)
  mockt eine ungespeicherte Spec — Kinder aus der Registry, nur das Dokument
  ist neu. Beide Mock-Responses tragen jetzt `entry` (Modulpfad der Spec in
  der Closure); dafür `mock_output_path` im Core öffentlich gemacht.
- Frontend: `mockRuntime.ts` transpiliert die Closure mit sucrase (TSX → CJS,
  nur Syntax) und führt sie mit einem Mini-`require` aus: relative
  Closure-Importe werden aufgelöst, `"react"` an die Composer-Instanz
  gebunden (sonst brechen Hooks). `useMockBundle.ts` holt die Closure
  debounced (250 ms); scheitert ein Zwischenstand, bleibt die letzte
  lauffähige stehen und der Canvas zeigt „Mock veraltet".
- Der Composer liefert der echten Komponente nur noch Props (camelCase wie
  im Generator), Event-Callbacks (Payload zurück auf snake_case gemappt)
  und Slot-Inhalte — die Slot-Zone landet damit exakt dort, wo der Mock
  `data-speccify-slot` rendert. Fehlergrenze pro Mock; `synthesizePayload`
  ist entfallen.
- Zweiter Canvas-Modus „Vorschau": rendert die Mock-Komponente des Dokuments
  selbst, inklusive der im generierten Code laufenden Verdrahtung. Damit
  gibt es einen laufenden Abgleich zur Composer-Simulation (`simulate.ts`),
  die im Bearbeiten-Modus weiterhin die Props zwischen den Knoten liefert.
- Drag & Drop: Palette-Einträge ziehbar (Drop auf Canvas = Top-Level, auf
  Slot-Zone = in den Slot), Knoten am Griff (⠿) umhängbar samt Teilbaum;
  eigene MIME-Typen in `dnd.ts`, damit `dragover` ohne `getData` entscheiden
  kann. Klick-Einfüge-Ziel und „+ als Kind" bleiben (agent-/tastaturfähig).
  Desktop-Fenster jetzt mit `disable_drag_drop_handler()` — sonst schluckt
  Tauris OS-Datei-Drop-Handler die HTML5-Drag-Events.
- Nebenbei: Playwright startet Vite mit `--host 127.0.0.1`. Vite band hier
  nur auf ::1, die webServer-Wartebedingung fragt IPv4 — der Smoke lief
  120 s ins Timeout, bevor überhaupt ein Test startete.
- Verifikation: 426 Pytest grün (+4: Entwurf==gespeichert byte-identisch,
  ungespeichertes Composite, 404 bei unauflösbarem Kind, 400 ohne id);
  5/5 Playwright grün (+2: Vorschau-Modus, Drag & Drop); Composer-Typecheck
  + Build grün (269 → 484 kB, gzip 136 kB — der Preis für sucrase im
  Bundle); 18 Desktop-Tests grün (+1 ignored), clippy/fmt clean; ruff clean.
  Beide Modi zusätzlich per Screenshot gegengesehen.
- Tag-Vorschlag: `v0.18.0-p3-composer-mock-bundle`.

## 2026-08-04 (P4 — `speccify build`: ganze Projekte aus `kind: app`)
- Schema (P4.1): neuer `app:`-Block (`routes[] {path,node,title?}`,
  `theme.tokens`, `env[]`) und dritte Wiring-Aktion `navigate: /pfad`.
  Kein zweites Baum-Konzept: **Screens sind die Top-Level-Knoten der
  Komposition**, `app.routes` sagt nur, welcher Knoten unter welchem Pfad
  liegt. `core/app.py` parst und validiert (Routen zeigen auf Top-Level,
  Pfade/Env-Namen eindeutig, `navigate` nur in Apps und nur auf deklarierte
  Routen, `app:` nur bei `kind: app`); das Composer-Backend meldet die
  Befunde als eigene Quelle „app".
- Codegen (P4.2): `codegen/app_react.py` erzeugt ein vollständiges
  Vite-React-Projekt. Bewusst ohne `react-router` — ein ~40-zeiliger
  Hash-Router liegt als Datei im Projekt, damit es mit react/react-dom/vite
  läuft und die Route-Semantik lesbar bleibt. `src/App.tsx` hält Wiring-State
  *und* Route und rendert nur den Screen der aktiven Route; die
  Wiring-Semantik ist dieselbe wie im Composite-Mock, plus `navigate`.
  Theme-Tokens werden CSS-Variablen, `app.env` wird typisierter Zugriff auf
  `import.meta.env` mit den Defaults aus der Spec.
- Zwei Füllungen, ein Scaffold: `--mocks` legt die Mock-Closure ab und je
  Screen einen Re-Export `<Name>.tsx → ./<Name>.mock` — der Import-Swap aus
  dem P2-Vertrag als eine sichtbare Zeile. `--no-mocks` schreibt die
  generierten Implementierungen an genau diese Stelle. Die Mock-Bytes sind
  byte-identisch zu `speccify mock`; es gibt weiter genau einen Mock-Pfad.
- Adapter (P4.3): `speccify build`, MCP-Tool `build` (8 Tools jetzt) und
  `POST /api/v1/build` — byte-identisch, per Cross-Consistency-Test gepinnt.
  Der Web-Pfad baut bewusst nur Mocks: das Backend hat weder Cache-Flags
  noch LLM-Zugang im Vertrag.
- Beweis (P4.4): `tests/test_app_build_smoke.py` hinter dem Marker
  `app_build` (wie Conformance/Visual-Regression, eigener CI-Job) baut die
  Demo-App, lässt `tsc --noEmit` und `vite build` darüber laufen, liefert
  `dist/` aus und spielt sie mit Playwright durch: Startroute, Navigation per
  Event, Datenfluss über Screens, unbekannte Route, keine Page-Errors.
  Toolchain per Symlink auf `apps/composer/node_modules` statt `pnpm install`
  im Wegwerf-Projekt; fehlt sie, wird übersprungen statt rot.
- Beim Bauen gelernt: Event-Payloads eines Mocks entstehen aus gleichnamigen
  Props — ein Datenfluss ist im gemockten Build also nur beobachtbar, wenn
  seine Quelle eine statische Prop ist. Deshalb hat die Demo-App einen
  Notiz-Screen (`@org/text-input` mit statischem `value`), dessen Wert im
  Kontaktformular als `initial_name` landet. Steht in `docs/app-builds.md`.
- Verifikation: 470 Pytest grün (+28), `pytest -m app_build` grün (67 s),
  `speccify lint specs/*.yaml` grün, CLI-Doku-Drift grün, ruff clean.
- Tag-Vorschlag: `v0.19.0-p4-app-builds`.

## 2026-08-04 (P5.1 + P5.2 — Git-Repos als Spec-Quelle)
- Entscheidungen (beantworten die offenen Fragen 1–3 des Pivot-Plans):
  **D16** die Repo-URL ist die Identität (`git+https://host/org/repo[#pfad]`)
  — host-qualifiziert, kein Confusion-Problem, und es passt ohne Änderung ins
  bestehende `Registry`-Protocol. **D17** Tags sind die Versionen (`v1.2.0`,
  mit Pfad `<pfad>/v1.2.0`) — ein Monorepo versioniert seine Specs damit
  unabhängig. **D18** Trust über Commit-Pin im Lockfile, sigstore bleibt ein
  späterer additiver Slot. **D19** der Cache ist ein Bare-Clone pro Repo.
- `GitRegistry` (P5.1): `fetch --depth 1` für Tags, `git cat-file blob
  <tag>:<pfad>` für die Spec-Bytes — kein Working Tree, kein Checkout. Nach
  einem Fetch ist alles offline lesbar; `offline=True` verbietet Netz hart und
  sagt im Fehlerfall, wie man den Cache füllt. Tests laufen gegen echte
  `file://`-Repos, CI braucht kein Netz.
- Lockfile v4 (P5.2): Git-Ids erlaubt, neues Feld `source_commit`. v1–v3
  bleiben lesbar (Loader-Migration), v3 liegt jetzt als Legacy-Schema-Datei
  neben v1/v2.
- Resolver: neues optionales `serves`-Prädikat pro Registry. Die lokale
  Registry bedient `@scope/name`, die GitRegistry `git+…`; die Reihenfolge im
  Set ist damit egal, und Registries ohne das Prädikat (Test-Doubles) bleiben
  gültig. Git-Ids sind ihr eigener „Scope" — der Phase-2-Confusion-Schutz
  greift weiter für scoped Ids.
- Stolperstein: der Codegen leitet Dateinamen und Komponenten-Namen aus der
  Spec-Id ab — mit einer Git-Id bricht das (`nicht im Format '@scope/name'`).
  Lösung: `Spec.name_id` liefert die **in der Spec deklarierte** Id; der
  Codegen benennt danach, die Herkunft hält das Lockfile. Für Registry-Specs
  sind beide identisch, also ändert sich kein Byte — belegt durch die
  Cross-Consistency-Tests und den `-m app_build`-Smoke.
- Verifikation: 489 Pytest grün (+19), `pytest -m app_build` grün,
  `speccify lint specs/*.yaml` grün, ruff clean.
- Offen in P5: P5.3 Discovery (Index-Repo + `speccify search`), P5.4 MCP/Web/
  Composer auf Git-Quellen nachziehen.

## 2026-08-05 (P5.3 + P5.4 — Discovery und Git-Quellen in allen Adaptern)
- Discovery ohne zentralen Dienst: ein Index ist ein Git-Repo (oder ein
  lokales Verzeichnis) mit **einer Datei pro Spec-Repo** unter `entries/*.yaml`
  (D21). Ein PR fasst genau eine Datei an, es gibt keine Merge-Konflikte in
  einer wachsenden Sammelliste, und CI validiert jeden Eintrag einzeln.
  Der Index nennt bewusst **keine Versionen** — Tags sind die Wahrheit, ein
  Index kann damit gar nicht veralten.
- `speccify search` (Ranking Id > Titel > Keyword > Summary, `--json`,
  `--offline`), MCP-Tool `search` (jetzt 9 Tools) und `GET /api/v1/index`.
  Quellen-Reihenfolge überall gleich: explizit > `SPECCIFY_INDEX` > `./index`.
  Trennzeichen ist das Komma, nicht `os.pathsep` — ein Doppelpunkt steckt in
  jeder Git-URL.
- `index/` im Repo mit README (Format, Beitrags-Ablauf) als Vorlage; Einträge
  bleiben leer, bis zum Launch gesät wird. Platzhalter-URLs wären tote Links.
- Git-Plumbing als `GitRepoCache` herausgelöst — Spec-Quellen und Index-Repos
  teilen sich denselben Bare-Clone-Cache.
- Der eigentliche Hebel für P5.4 war eine kleine Fassade: `MultiRegistry`.
  Der Resolver nimmt von sich aus eine Liste, aber Kompositions-Auflösung,
  Mock- und App-Codegen erwarten genau *eine* Registry. Statt jede
  Aufrufstelle auf Listen umzubauen, verteilt die Fassade pro Id an die erste
  Registry, die sie bedient (`serves`). Damit können Web-Backend und MCP ohne
  Sonderfälle mit Git-Kindern arbeiten.
- Nebenbei zwei Kanten geglättet: `parse_child_ref` kennt jetzt Git-Refs mit
  Range (`composition.uses`), und eine unerreichbare Git-Quelle ist im
  Composer ein Validierungs-Befund statt eines 404-Absturzes.
- Verifikation: 521 Pytest grün, 5/5 Playwright, `-m app_build` grün,
  CLI-Doku-Drift grün, ruff clean.
- Offen: die Composer-**Palette** listet weiter nur die lokale Registry —
  Index-Suche in der Oberfläche ist der nächste sinnvolle Schritt.
- Tag-Vorschlag: `v0.20.0-p5-git-quellen`.

## 2026-08-05 (P5.5 — Index-Suche in der Composer-Palette)
- Letzter Schritt, der Git-Quellen auch visuell nutzbar macht: die Palette
  hat einen Abschnitt „Index (Discovery)" mit Suchfeld; Treffer lassen sich
  wie lokale Specs einfügen oder in den Canvas ziehen.
- Dafür musste die Detail-Antwort zwei Dinge trennen, die vorher dasselbe
  waren: `id` ist der **deklarierte** Name der Spec (danach heißen
  generierte Dateien und der Knoten-Alias), `source` der Ref, über den sie
  geholt wurde und der in `composition.uses` gehört. Bei Git-Quellen sind
  das zwei verschiedene Strings. Neuer Endpoint `GET /api/v1/spec?source=`
  löst beliebige Quellen auf — der bestehende `/specs/{scope}/{name}` kann
  keine URLs im Pfad tragen.
- Index-Schema erlaubt jetzt auch `git+file://` (lokale Indizes und Tests);
  geteilte Indizes bleiben bei https.
- Der UI-Smoke legt sich seine Fixture selbst an: `start-backend.sh` baut ein
  echtes Git-Repo mit der Button-Spec (Tag v0.1.0) plus einen Index, der
  darauf zeigt, und setzt SPECCIFY_INDEX/SPECCIFY_GIT_CACHE. Der neue Test
  geht den ganzen Weg: suchen → Git-Quelle als Kind → deren generierter Mock
  steht im Canvas → Validierung löst die Git-Quelle auf.
- Verifikation: 523 Pytest grün, 6/6 Playwright grün, Composer-Typecheck +
  Build grün (486 kB), ruff clean. Palette zusätzlich per Screenshot geprüft.
- Damit ist P5 komplett; als Nächstes P6 (Doku-Site, Saatgut-Repos, Launch).

## 2026-08-05 (P6.1 — Doku-Site auf den heutigen Stand, Launch vorbereitet)
- Die Site beschrieb noch die Welt vor dem Pivot: ein Sidebar-Abschnitt
  „Registry" (das zurückgebaute Django-Backend), Stub-Seiten aus Stage 1
  („Inhalt folgt in einer späteren Stage") und ein Hero, der Speccify „npm
  für Spezifikationen" nannte — während Specs längst wie Go-Module über Git
  geteilt werden.
- Sync-Mapping um die vier Seiten erweitert, die den heutigen Workflow
  erklären (API-Vertrag & Mocks, Composer, Projekt-Builds, Git-Quellen &
  Discovery); Sidebar umgebaut; `registry/` gelöscht.
- Stub-Seiten mit echtem Inhalt: Installation (die drei Wege CLI/MCP/Web),
  Deine erste Spec (Spec → Mock → Composer → Build → über Git teilen),
  Spec-Format, MCP-Referenz (alle 9 Tools; `mcp/README.md` hatte `mock`,
  `build` und `search` noch nicht), Targets.
- Gefundener Nebenfehler: der „AUTOGENERIERT"-Hinweis war ein
  MDX-Kommentar (`{/* … */}`) in `.md`-Dateien — Starlight rendert das als
  sichtbaren Text. Beide Generatoren schreiben jetzt HTML-Kommentare.
- `docs/launch.md` als Vorbereitung: Vor-dem-Launch-Checkliste (alle
  Verifikations-Kommandos), Plan fürs Saatgut im bewusst leeren Index (drei
  Repos aus den Referenz-Specs, inkl. Befehlen), HN- und X-Entwürfe plus die
  absehbaren Rückfragen. **Nichts davon ausgeführt** — Repo anlegen, pushen,
  deployen und posten bleibt BO-Entscheidung.
- Verifikation: 523 Pytest grün, Doku-Sync und CLI-Doku ohne Drift, Site
  baut 29 Seiten (vorher 24), ruff clean; Landing und Doku-Seiten per
  Screenshot gegengesehen.

## 2026-08-06 (Neuausrichtung: Specs werden Workflow-Playbooks — Plan)
- BO-Ansage: Der ursprüngliche Zweck ist vom Fortschritt bei Coding-Agents
  überholt. Feingranulare Komponenten-Specs, aus denen man Größeres
  zusammensetzt, bringen kaum noch Mehrwert — Agents sind auf dem Level
  schon gut. Neue Idee: eine Spec beschreibt einen **komplexen,
  wiederkehrenden Workflow** samt Quellen und Assets (Beispiel: „IAP mit
  7 Tage Trial in macOS/iOS integrieren" — zweimal gemacht, jedes Mal
  stundenlang recherchiert). Composer wird **Viewer + kontextsensitiver
  Chat** ohne manuellen Edit-Modus; Child-Nodes (Wiederverwendung) bleiben;
  MCPs/Server bleiben und werden ausgebaut.
- Alten Plan `pivot-open-source-git-composer.md` auf `done` gesetzt und nach
  `plans/archive/` verschoben, Verweise in 9 Dateien nachgezogen (Konvention:
  genau ein aktiver Plan).
- Neuer aktiver Plan `neuausrichtung-workflow-playbooks.md`: Vision, Delta
  (was bleibt / was zurückgebaut wird), Schema-v2-Entwurf am IAP-Beispiel,
  Specs als Bundles (Assets erzwingen Verzeichnisse + Bundle-Hash),
  Viewer/Chat über MCP statt eigenem LLM-Client, `speccify check` als
  Nachfolger von Conformance (Link-Rot + Quellen-Alter), fünf Phasen
  W1–W5, fünf Entscheidungsvorschläge D1–D5 und vier Fragen an den BO.
- Kernabwägung im Plan: der Codegen-Zweig (Mocks, App-Builds, LLM-Targets,
  Replay-Cache, Conformance, Visual-Regression, Composer-Editor) trägt in
  der neuen Welt nichts — ~2.700 Zeilen plus Tests und drei CI-Jobs.
  Empfehlung: Archiv-Branch `archive/pre-playbook-pivot` + Löschung, wie
  beim Registry-Rückbau in P1. Noch nicht ausgeführt: der Plan wartet auf
  das Refinement.
- Keine Code-Änderungen in dieser Session — nur Plan-Hygiene, wie bei
  früheren Phasen-Kickoffs.

## 2026-08-06 (W1 — Schnitt und Fundament für Playbooks)
- Refinement mit dem BO: kein Schema v2, sondern **kompletter Neustart** (es
  hat nie jemand außer ihm eine Spec benutzt); **alles auf Englisch**;
  Vokabular „Playbook"; Granularität als D8 vorgeschlagen (Prüfstein: „hätte
  ich beim zweiten Mal wieder nachschlagen müssen?").
- Rückbau in einem Rutsch, Archiv-Branch `archive/pre-playbook-pivot`: Mocks,
  `speccify build`, drei LLM-Targets, Replay-Cache, Conformance,
  Visual-Regression, Composer-Editor, Workspaces, `specs/`,
  `registry-fixtures/`, `example-project/`, die alten Schemata, drei CI-Jobs.
- Neues Fundament: `schema/playbook.schema.json` + `core/playbook.py`. Die
  interessanten Regeln stehen nicht im JSON-Schema, sondern daneben: ein
  Schritt hat `detail` ODER `uses` (nie beides — sonst weiß ein Agent nicht,
  welchem er folgen soll), Quellen müssen von einem Schritt referenziert sein,
  Assets müssen im Bundle liegen.
- Playbooks sind **Bundles**: Verzeichnis mit `playbook.yaml` + `assets/`.
  Das erzwang neue Registry-Semantik (Verzeichnis statt Datei, auch über
  `ls-tree`/`cat-file` im Git-Pfad) und einen Bundle-Hash über sortierte
  Pfade + Inhalte — mit Längenpräfixen, damit `a/b`+`c` nicht mit `a`+`b/c`
  kollidiert. Lockfile v1 pinnt diesen Hash plus den Commit.
- Stolperstein: PyYAML macht aus `retrieved: 2026-08-06` ein `date`-Objekt,
  das JSON-Schema will einen String. Autoren sollen keine Quotes tippen
  müssen → Normalisierung vor der Validierung.
- Zwei echte Referenz-Playbooks statt Fixtures aus dem Nichts: die
  macOS-Signierung/Notarisierung einer Tauri-App (aus `docs/release.md`, also
  selbst erarbeitetes Wissen) und das Developer-ID-Zertifikat als
  wiederverwendetes Child. Damit ist die Wiederverwendung nicht Deko,
  sondern im Referenzmaterial belegt.
- Der Composer musste mit: nach dem Rückbau der Editor-Teile wäre er kaputt
  gewesen. Er ist jetzt ein lesender Viewer mit Selection-State — der
  Vorgriff auf W3, der W4 (Kontext-Chat) direkt anschlussfähig macht.
- Verifikation: 115 Pytest grün, 1/1 Playwright (Viewer-Smoke inkl. Selection,
  Asset-Anzeige, Sprung ins Child), MCP-stdio-Smoke grün, Viewer-Build,
  Doku-Site 32 Seiten, ruff clean; CLI-Flow zusätzlich von Hand durchgespielt.
- Offen: `speccify check` (W2), Schritt-Diagramm und Markdown im Viewer (W3),
  Kontext-Chat (W4), README/Landing/Launch-Texte (W5).

## 2026-08-06 (W2 — `speccify check` und der Agent-Vertrag)
- Kernfrage von W2: Playbooks veralten anders als Code. Kein Compiler meckert,
  wenn Apple eine Doku-Seite verschiebt oder ein Schritt seit einem Release
  nicht mehr stimmt. `speccify check` trennt deshalb sauber von `lint`:
  `lint` = wohlgeformt, `check` = stimmt noch.
- Drei Ebenen: Struktur (wie lint), **Alter** aus dem `retrieved`-Datum jeder
  Quelle, und optional **Erreichbarkeit** (`--links`, hinter dem Pytest-Marker
  `links`, weil Netz). 404 ist Fehler, 5xx Warnung, Redirect ok; Server, die
  HEAD ablehnen, bekommen einen zweiten Versuch mit GET.
- Entscheidung beim Bauen: Strukturfehler verdecken Alters-Warnungen. Bei
  einem kaputten Playbook ist eine Liste alter Quellen nur Rauschen — erst
  reparieren, dann über Aktualität reden.
- MCP: `playbook_asset` (Skripte/Configs, die mit dem Playbook reisen — Text
  direkt, Binäres base64, Fehlermeldung nennt die vorhandenen Assets) und
  `playbook_check`. Damit 9 Tools.
- Der Agent-Vertrag ist jetzt als Test gepinnt statt nur behauptet:
  `playbook_list` → `playbook_get` → dem delegierten Schritt ins
  Child-Playbook folgen → `playbook_step` → `playbook_asset`, ausschließlich
  über Tools. Beim Schreiben aufgefallen: „notarization" als Auswahl-Keyword
  war mehrdeutig (beide Referenz-Playbooks führen es) — der Test wählt jetzt
  über „tauri".
- Nebenbei bestätigt: `--links` läuft gegen die echten Apple-/Tauri-Quellen
  der Referenz-Playbooks durch, alle vier lösen auf.
- Verifikation: 130 Pytest grün (+15), `pytest -m links` grün, ruff clean,
  Doku-Sync und CLI-Doku ohne Drift.

## 2026-08-06 (W3 — Viewer-Ausbau)
- Workflow-Diagramm neben den Schritten: ein Knoten pro Schritt, delegierte
  gestrichelt, Marker für Assets/verify, Klick wählt aus und scrollt hin.
  Bewusst handgezeichnetes SVG statt Diagramm-Bibliothek — das Layout ist eine
  einzige Spalte, und ein abhängigkeitsfreier Viewer wiegt mehr als generische
  Graph-Fähigkeiten.
- Markdown im `detail` über `react-markdown`. Wichtig dabei: die Bibliothek
  rendert per Default **kein rohes HTML** — Playbooks kommen aus fremden
  Git-Repos, ein `dangerouslySetInnerHTML`-Pfad wäre hier fahrlässig.
- Beim Screenshot-Gegenlesen aufgefallen: Prerequisites, Pitfalls und
  verify-Kriterien zeigten Backticks als Text, während der Schritt-Body sie
  renderte. Das sieht aus wie ein Bug, also Inline-Markdown-Komponente
  nachgezogen (ohne `<p>`-Wrapper).
- Quellen-Alter: „retrieved today" / „4 months old", ab 180 Tagen bernstein.
  Die Schwelle spiegelt `STALE_SOURCE_DAYS` aus dem Core — Viewer und
  `speccify check` dürfen sich nicht widersprechen.
- Ein Filterfeld für zwei Zwecke: es engt die Bibliothek ein und ist zugleich
  die Query für den Discovery-Index. Statt einer zweiten Such-Oberfläche gibt
  es einen Knopf „Search the index for …" — der natürliche Fluss ist ja
  „lokal nichts gefunden, schau weiter".
- Stolperstein beim Testen: nach der Index-Suche steht der Filter noch, also
  ist die Bibliotheksliste leer — der E2E musste das berücksichtigen. Das ist
  korrektes Verhalten, aber es zeigt, dass ein geteiltes Feld erklärt werden
  muss (steht jetzt in `docs/viewer.md`).
- Verifikation: 130 Pytest, 1/1 Playwright (Smoke deckt jetzt Filter,
  Diagramm-Klick, gerendertes Markdown, Quellen-Alter und Index-Suche ab),
  Viewer-Build 323 kB, ruff clean, Doku-Sync ohne Drift, Screenshot geprüft.
- BO hat die Referenz-Projekte fürs IAP-Playbook genannt:
  zwei eigene, nicht öffentliche Apps (Pfade im BO-Gedächtnis) — im Plan
  notiert (nur lesen, fremde Repos).

## 2026-08-06 (IAP-Referenz-Playbook aus zwei echten Projekten)
- Beide BO-Projekte gelesen — dort nichts geschrieben.
  Sie lösen dasselbe Problem und kommen zur selben Architektur: freie App +
  NonConsumable-Freischaltung + **selbstgebaute** 7-Tage-Frist.
- Die Erkenntnis, die den Rechercheaufwand ausmacht und jetzt als erster
  Schritt im Playbook steht: **Apple hat für Einmalkäufe keinen
  Testzeitraum.** Free Trials sind Introductory Offers, die es nur für Abos
  gibt. Wer „testen, dann besitzen" will, baut die Uhr selbst.
- Die zweite Erkenntnis: Die Uhr ist trivial, die **Persistenz** nicht.
  UserDefaults überlebt Backups, aber nicht das Löschen; die Keychain
  überlebt das Löschen, aber nicht das neue Gerät; iCloud KVS spannt über
  Geräte, braucht aber ein Konto. Die eine App nutzt Keychain + UserDefaults,
  die andere iCloud + UserDefaults — im Playbook stehen alle drei mit ihren
  Überlebenseigenschaften und der Merge-Regel „frühester Start gewinnt".
- Weitere Fallstricke aus dem echten Code: High-Water-Mark gegen
  zurückgestellte Uhren (bewusst ohne Bestrafung), `Transaction.updates` vor
  der Entitlement-Prüfung abonnieren, `.pending` ist kein Fehler, ein Kauf
  muss eine abgelaufene Frist schlagen, `originalAppVersion` ist auf iOS die
  Build-Nummer und meldet in der Sandbox „1.0", Produkt-IDs vertragen keine
  Bindestriche.
- Assets sind **neu geschriebene Vorlagen** (StoreKit-Konfiguration,
  TrialState.swift, StoreService.swift), kein kopierter Projektcode.
- `speccify check --links` hat sich sofort bezahlt gemacht: eine Apple-URL,
  die ich für richtig hielt, war ein 404. Genau der Fall, für den W2 gebaut
  wurde — gefunden, bevor jemand der Anleitung folgt.
- Nebenbei zwei Testannahmen korrigiert, die an „genau zwei Playbooks"
  hingen; die Bibliothek wächst ja.
- Verifikation: 130 Pytest, `check --links` grün (13 Quellen), 1/1 Playwright,
  ruff clean.

## 2026-08-06 (IAP-Playbook korrigiert — Rückfragen deckten echte Lücken auf)
- Der BO fragte zurück: „Was ist die Build-Nummer-Grenze?" und „Was ist
  Drei-Speicher-Kombination?". Beides waren Lücken **im Playbook**, nicht nur
  in meiner Zusammenfassung — ein Leser hätte an denselben Stellen gestockt.
- Beim Nachschlagen der App Review Guidelines (für seine Antwort zu 2)
  stellte sich meine Kernaussage als zu grob heraus: **Guideline 3.1.1
  erlaubt ausdrücklich einen zeitbasierten Trial für Nicht-Abo-Apps** — als
  Non-Consumable auf Preisstufe 0 mit der Namenskonvention „XX-day Trial".
  Richtig bleibt, dass StoreKit die Tage nicht zählt (das tun nur
  Introductory Offers, abo-only); das Tier-0-Produkt macht den Trial im Store
  sichtbar. Schritt 1 und 2 korrigiert.
- 3.1.1 verlangt zusätzlich, vor Trial-Beginn Dauer, Folgen und Preis zu
  nennen; 2.2 hält Demos/Trial-Versionen vom Store fern. Damit hat
  „read-only statt Sperre" jetzt eine Quelle statt eines Bauchgefühls.
- 3.1.1 nennt selbst **DeviceCheck** fürs Verwalten der Trial-Dauer — als
  vierte Ablage ergänzt (zwei Bits bei Apple, überlebt Werksreset, braucht
  Server).
- Grandfathering: die Schwelle ist keine Ableitung, sondern ein
  Nachschlagewert aus der Versionshistorie in App Store Connect. Steht jetzt
  samt Beispiel-Code im Schritt.
- Speicher-Empfehlung geschärft: zwei benannte Kombinationen statt „nimm
  alle drei" — drei Ablagen sind kein Verdienstorden, sondern drei Dinge zum
  Abgleichen.
- Die Validierung hat beim Umbau eine verwaiste Quelle gefunden
  (`asc_iap_types` hing an keinem Schritt mehr) — genau ihr Zweck.
- Verifikation: lint + `check --links` grün (15 Quellen), 130 Pytest, ruff.

## 2026-08-06 (W4 — Kontext-Brücke zwischen Viewer und Agent)
- Kern der Neuausrichtung, jetzt fertig: Der Viewer meldet jeden Klick ans
  Backend, `viewer_selection` gibt ihn **aufgelöst** zurück — Playbook,
  Schritt samt `detail`/`verify`/Quellen, oder der Asset-Inhalt. Ein Agent
  muss nicht dreimal nachfragen, um zu wissen, worüber geredet wird.
- Gegenrichtung: `playbook_propose` nimmt den kompletten neuen YAML-Text.
  Das Backend validiert **sofort** — ein ungültiger Vorschlag erreicht die
  Oberfläche gar nicht erst, sonst stünde dort ein Diff, den man nicht
  anwenden kann. Der Viewer zeigt Diff + Apply/Discard; auf die Platte kommt
  nichts ohne Klick.
- Zwei Leitplanken, beide bewusst: Playbooks aus **Git-Quellen** lassen sich
  nicht schreiben (Änderungen gehören ins Quell-Repo als Commit und neuer
  Tag), und der Sitzungszustand liegt **im Speicher** — eine Auswahl, die die
  Sitzung überlebt, wäre eine Lüge über das, was der Nutzer gerade ansieht.
- Diff selbst gebaut (LCS über Zeilen + Kontext-Verdichtung, ~60 Zeilen).
  Für ein einzelnes Panel lohnt keine Abhängigkeit, die man dauerhaft pflegt.
- Der MCP-Test läuft gegen ein **echtes Backend** auf freiem Port statt gegen
  ein Fake: Die Tools sprechen HTTP, ein Mock hätte genau den Teil
  wegabstrahiert, der schiefgehen kann.
- Screenshot-Gegenlesen hat wieder etwas gefunden: der Apply-Knopf war
  unsichtbar — `.row button` und `button.primary` haben gleiche Spezifität,
  die generische Regel stand später, also weißer Text auf weißem Grund.
  Behoben und im Smoke festgenagelt (prüft jetzt die Hintergrundfarbe).
- Verifikation: 144 Pytest (+14), 1/1 Playwright (klicken → Auswahl über die
  API prüfen → Vorschlag → Diff → anwenden → Änderung im Playbook), ruff,
  Doku-Sync.
- Damit ist von der Neuausrichtung nur noch W5 offen: README, Landing-Page
  und `docs/launch.md` tragen die alte Komponenten-Geschichte.

## 2026-08-06 (W5 — Außendarstellung auf Playbooks; Neuausrichtung abgeschlossen)
- **W5 geliefert**, damit sind W1–W5 komplett und der Plan ist archiviert
  (`plans/archive/neuausrichtung-workflow-playbooks.md`).
- README, Landing-Page und alle Doku-Seiten auf Playbooks und (D6) auf
  Englisch. Die Prüffrage steht jetzt vorn: „Hätte ich beim zweiten Mal wieder
  nachschlagen müssen?" Der Pivot selbst steht im README — er ist die
  interessante Hälfte der Geschichte, nicht etwas zum Verstecken.
- `/try-it/` gelöscht statt umgeschrieben: die Seite bewarb einen Playground,
  den es seit W1 nicht mehr gibt. Ein Hosted-Ersatz wäre erfunden gewesen.
- **Der Desktop-Build war kaputt und niemandem aufgefallen.**
  `build_engine_payload.sh` kopiert `registry-fixtures/` und
  `tests/fixtures/llm-cache/` in die App-Resources — beide beim Rückbau
  entfernt, mit `set -e` bricht das Skript ab. Selbst repariert hätte die App
  eine leere Bibliothek gezeigt: `lib.rs` setzte `SPECCIFY_REGISTRY_PATH`, das
  Backend liest `SPECCIFY_LIBRARY_PATH`. Beides zieht jetzt auf `playbooks/`.
  Das ist der Preis dafür, dass der Rückbau die Rust-Seite nicht mitgeprüft
  hat — die Python-Suite war grün, der Build war es nicht.
- Weitere Leichen entfernt: `apps/web/frontend` (Next.js-Playground gegen
  `/api/v1/specs` und `/api/v1/render`, beide weg; hing nicht im
  pnpm-Workspace, wurde aber von CI gebaut und von `dev-up.sh` gestartet),
  `record-llm-cache.sh` (exec't eine nicht existierende Python-Datei), das
  `bedrock`-Extra (boto3 zog 6 Pakete ins Lock), `Settings.cache_dir`.
- `gen_cli_docs.py --check` hat verwaiste Seiten nicht bemerkt: `build`,
  `mock` und `conformance` standen weiter auf der Doku-Site. Der Check meldet
  sie jetzt, der Lauf löscht sie. Ohne das passiert es beim nächsten Umbau
  wieder.
- Die MCP-Referenz nannte Tools, die es nicht gibt, und Input-Namen, die nie
  gestimmt haben. Gegen `server.py` geprüft: es heißt `reference`, nicht
  `source`, und `playbook_list` nimmt kein `query`.
- Verifikation: 144 Pytest (1 deselected), 1/1 Playwright, 18/19 Desktop-Tests
  (1 ignored), ruff clean, MCP-stdio-Smoke, Doku-Sync + CLI-Doku ohne Drift,
  Marketing-Build 21 Seiten (vorher 25: −1 Playground, −3 Geister-Befehle),
  keine toten internen Links im gebauten Site-Output,
  `build_engine_payload.sh` läuft wieder durch, `speccify check playbooks/`
  0 Fehler.
- Offen sind nur noch BO-Aktionen aus `docs/launch.md`.

## 2026-08-07 (Veröffentlichung: Repo, Website, Release-Pipeline)
- **Repo öffentlich**: `mhennemeyer/speccify`, `main` als Default. Das Repo
  enthielt ein **anderes** Projekt von 2009 („A minimal RSpec clone", 3 Stars,
  zwei davon fremd) — `master` bleibt unangetastet, damit nichts verloren geht
  und alte Links weiter funktionieren.
- **Hygiene vor dem Push**: keine Secrets (geprüft). `.agent/chats/` (rohe
  Sitzungstranskripte) und `.junie/` entfernt, Namen zweier privater Projekte
  neutralisiert — ein öffentliches Git-Log bekommt man nicht zurück.
  Urheberangabe korrigiert (LICENSE + 5 pyproject sagten „Marc"), Commit-Mail
  auf die private Adresse umgestellt.
- **Website live** über `pages.yml`; Deploy prüft vorher erneut, dass Doku-Site
  und Repo übereinstimmen.
- **Release-Pipeline** steht, ist aber **ungetestet** — sie braucht einen Tag,
  und Tags setzt der BO.
- **Der erste CI-Lauf überhaupt** war die eigentliche Arbeit: Es gab nie ein
  Remote, also lief nichts davon je. Sechs echte Fehler, alle behoben (Details
  in `.agent/status.md`).
- **Lehre**: Ein Werkzeug, das nie lief, ist kein grünes Werkzeug. Playwright,
  mypy, lychee und markdownlint haben zusammen sechs Fehler gemeldet, die
  lokal alle „grün" waren — mypy sogar deshalb, weil es gar nicht startete.
- **Lehre 2**: Das Repo liegt in einem iCloud-synchronisierten Ordner. 70
  Konfliktkopien im Arbeitsverzeichnis, eine davon eine fremde Binary in der
  venv. Das ist kein Repo-Problem, sondern ein Ablageort-Problem.
