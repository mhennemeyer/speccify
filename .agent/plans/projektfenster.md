---
lifecycle: active
status: Bauen — P1 geliefert 2026-08-26; P2 geliefert 2026-08-27, „Fertig heißt" bestanden 2026-08-28 (claude läuft eingeloggt im Projektfenster-Terminal auf Windows und listet alle elf Projekt-Skills hinter der Junction). P3-Kern geliefert 2026-08-28: Board-Tab (D19, iKanbanAI-Format, Verschieben byte-stabil), Plan-Editor (D20), Tools-/MCPs-/Agent-Tab, Composer-Rückbau (D18) — auf macOS E2E und auf Windows in der VM verifiziert. BO-Findings 2026-08-28 eingearbeitet (D21–D24, P4 = Skill-Quellen/Projekt-Settings/Agent-Config; iKanbanAI-Referenzen aus dem Produkt entfernt — Speccify definiert, Clients folgen; Terminal rechts/unten umgesetzt). Offen: CI-Erstlauf beim nächsten Push, x86-Referenz. Läuft parallel zu `skills-und-tools.md` (BO-Ausnahme von der Ein-Plan-Regel).
sessionId: projektfenster
---
# Plan: Projektfenster — Pläne, Skills, Tools im Projekt verwalten (auch auf Windows)

> **Auslöser (BO, 2026-08-26):** Projekte mit der Speccify-App öffnen
> (hatten wir schon einmal mit dem Composer) und dann — ähnlich wie in
> iKanban AI — Pläne, Skills, Tools und ggf. mehr verwalten. **Hauptziel:
> Speccify auf Windows nutzen, wo es kein iKanban AI gibt.** Das jetzige
> Fenster bleibt als globales Dashboard erhalten.
>
> **Verhältnis zu [`skills-und-tools.md`](./skills-und-tools.md):** parallel.
> Dieser Plan baut die *Sicht* auf das, was der andere Plan als *Substanz*
> geschaffen hat (`.agent/` als Zuhause, Expand/Execute/Evaluate,
> `expansions.yaml`). M2 (Testlauf) bleibt drüben das nächste Ziel — und
> profitiert: Läuft das Projektfenster auf Windows, kann ein Testlauf
> dort stattfinden, wo iKanban AI nie hinkommt.

---

## Das Ziel in einem Satz

Die Speccify-Desktop-App öffnet ein **Projektverzeichnis in einem eigenen
Fenster** — links die Bestände (Pläne, Skills, Tools, MCPs, Agent-Config),
rechts ein **Agent-Terminal im Projektkontext**, in der Mitte der Inhalt des
gewählten Tabs — und dieses Fenster läuft **auch auf Windows**.

## Ausgangslage

Was schon da ist und was der Plan nur verbinden muss:

* **Fenster-Mechanik**: `open_composer` (`lib.rs`) öffnet heute pro Repo ein
  eigenes `WebviewWindow` mit Supervisor-gestütztem Backend-Prozess. Das
  Muster (Fenster je Projekt, Prozess stirbt mit dem Fenster) ist erprobt.
* **Terminal**: `terminal.rs` — echtes PTY über `portable-pty` 0.9, cwd aus
  den Settings, Autostart-Command, xterm.js. Kommentar dort: „Windows ist
  bewusst zurückgestellt" — `portable-pty` kann aber ConPTY; es fehlt nur
  die Shell-Wahl (`login_shell()` liest `$SHELL`, Fallback `/bin/zsh`).
* **Die Bestände sind Dateien.** Alles, was die linke Seitenleiste zeigen
  soll, liegt lesbar im Projekt:
  * Pläne: `.agent/plans/*.md` (Frontmatter `lifecycle`/`status`/`sessionId`).
  * Skills: `.agent/skills/<name>/SKILL.md` — **normale** Skills (D8),
    expandiert und committet; Herkunft in `.agent/speccify/expansions.yaml`.
  * Tools: `.agent/tools/<name>/TOOL.md` + `<platform>.<ext>`; Status je
    Plattform (`implemented`/`verified`) in `expansions.yaml`.
  * MCPs: `.mcp.json` (dieselbe Wahrheit wie im iKanban-MCP-Tab).
  * Agent-Config: `CLAUDE.md`, `AGENTS.md`, ggf. `.agent/AGENT.md`.
* **iKanban AI als Vorbild, nicht als Abhängigkeit**: Der dortige Schnitt
  (Skills-Tab, Tools-Tab, MCP-Tab, Agent-Terminal, Board) ist die validierte
  UX — aber iKanban ist Swift/macOS. Das Projektfenster übernimmt den
  Schnitt in der Tauri-App, die auf Windows baut.
* **Wissen des Agenten**: kommt aus dem Projekt selbst (`CLAUDE.md`,
  `.claude/skills → .agent/skills`), nicht aus der App. Das Terminal muss
  nur im richtigen cwd starten — den Rest erledigt die bestehende
  Skills-Mechanik.

## Das Fenster

```text
┌────────────┬──────────────────────────────┬──────────────────────┐
│ Pläne      │                              │  Agent-Terminal      │
│ Skills     │   Inhaltsbereich             │  (PTY, cwd=Projekt,  │
│ Tools      │   je nach gewähltem Tab      │   Autostart z. B.    │
│ MCPs       │                              │   `claude`)          │
│ Agent      │                              │                      │
└────────────┴──────────────────────────────┴──────────────────────┘
```

* **Pläne**: Liste aus `.agent/plans/` (aktiv/archiv, `lifecycle`/`status`
  aus dem Frontmatter), Markdown-Ansicht. Erst lesen; Bearbeiten macht der
  Agent.
* **Skills**: Liste aus `.agent/skills/` mit Herkunft aus `expansions.yaml`
  (expandiert von wo, welche Version, Upstream-Drift wie in `verify`);
  SKILL.md-Ansicht (der Viewer aus T1 als Vorlage).
* **Tools**: Liste aus `.agent/tools/` — je Tool der Spec (TOOL.md) und der
  Status **je Plattform**: fehlt / `implemented` / `verified` (+ Datum).
  Genau hier zeigt sich der Windows-Wert: „`macos.sh` verified,
  `windows.ps1` fehlt" ist die Aufgabenliste für den Agenten rechts.
* **MCPs**: Server aus `.mcp.json` **und** die Permission-Allowlist aus
  `.claude/settings.json` (`permissions.allow`) — beides projektbezogen
  (F2, BO 2026-08-26). Globale MCPs verwaltet weiterhin das Dashboard
  (Server-Tab); der Tab hier zeigt nur, was *dieses Projekt* betrifft.
* **Agent** (ggf.): `CLAUDE.md`/`AGENTS.md` anzeigen; mehr erst nach Bedarf.
* **Rechts**: die bestehende Terminal-Seitenleiste, aber **pro Fenster** mit
  cwd = Projektwurzel und projektbezogenem **Agent-Kommando**: Default
  `claude`, pro Projekt umstellbar auf `codex` oder ein freies Kommando
  (F3, BO 2026-08-26 — nichts Claude-Spezifisches fest verdrahten).
  ask_bo bleibt vorerst im Dashboard.
* **Dashboard**: Das heutige Fenster bleibt; der Composer-Tab wird durch
  einen Tab **„Projekte"** ersetzt („Projekt öffnen" + zuletzt geöffnete) —
  der Composer entfällt (D18).

## Entscheidungen (Vorschläge, Nummerierung setzt D13 fort)

* **D14 — Nativ lesen, per Agent handeln.** Die linke Seitenleiste liest
  die Projektdateien **direkt in Rust** (Markdown-Frontmatter, YAML, JSON —
  alles trivial parsebar). Keine Python-Engine, kein Backend-Prozess, kein
  MCP nötig, nur um anzuzeigen. *Aktionen* (expand, tool check, Plan
  fortschreiben) laufen über das Agent-Terminal rechts — konsistent mit
  D11 („Der Dreischritt ist Skill, nicht Code") und D13 (kein Exec-MCP).
  Folge: Das Projektfenster funktioniert auf Windows **ohne** die
  Engine-Payload-Geschichte. Der MCP-HTTP-Modus aus T4 bleibt der Weg für
  *fremde*, gesandboxte Apps (iKanban) — die eigene App braucht ihn nicht.
* **D15 — Fenster wie beim Composer, Inhalt aus der eigenen SPA.** Pro
  Projekt ein `WebviewWindow` (Label `project-<hash>`), das die
  **Desktop-SPA selbst** mit `?project=<pfad>` lädt — kein zweites Frontend,
  kein Backend-Spawn (anders als beim Composer-Fenster, das eine fremde SPA
  vom Backend zieht). Ein Projekt doppelt öffnen fokussiert das vorhandene
  Fenster.
* **D16 — Terminal windowsfähig machen statt neu bauen.** `portable-pty`
  bleibt; `login_shell()` bekommt eine Windows-Variante (PowerShell 7
  `pwsh` wenn vorhanden, sonst `powershell.exe`; `COMSPEC` als letzter
  Fallback). Terminals werden pro Fenster-Id geführt (die `HashMap` in
  `Terminals` kann das schon).
* **D17 — `speccify link` kennt Windows.** `.claude/skills → .agent/skills`
  wird auf Windows eine **Directory Junction** (braucht keine Adminrechte);
  schlägt das fehl: Kopie + `verify`-Abgleich (der Fallback war in T2
  ohnehin vorgesehen). Das ist ein kleiner CLI-Beitrag dieses Plans zum
  anderen — die App selbst verlinkt nichts.
* **D18 — Der Composer entfällt** (BO, 2026-08-26: „Composer brauchen wir
  nicht mehr"). Das Projektfenster übernimmt die Rolle „Projekt öffnen";
  der Composer-Tab im Dashboard weicht dem Projekte-Tab (P1). Der
  **Rückbau** des Restes (`apps/composer`, `open_composer`, `/ui`-Mount im
  Web-Backend, Payload-/CI-Anteile) ist eigener Aufräumschritt in P3 —
  nicht nebenbei, damit P1/P2 klein bleiben. Damit fällt auch die alte
  Rahmenbedingung „Composer muss agent-bedienbar bleiben" weg.
* **D19 — Board-Tab (Speccify-Board-Format)** (BO, 2026-08-28: „Wir
  wollen auch das Board hier abbilden"). Das Format lebt **im Projekt**
  und wird von **Speccify definiert** — Client-Apps (u. a. iKanbanAI)
  lesen und schreiben dasselbe Verzeichnis (Rollen-Klarstellung, BO-
  Finding 2026-08-28: keine iKanbanAI-Referenzen im Produkt):
  `.agent/board/<id>.md`, flaches Frontmatter (`key: value`, kein
  verschachteltes YAML) mit `id`/`title`/`station`/`assignee`/`created`
  (ISO8601 UTC); Zusatzfelder (`order`, `ready`, `needs_human`, …)
  bleiben **byte-stabil** erhalten. Stationen fix: `Backlog`, `Doing`
  (Anzeige „In Progress"), `Done`. Sortierung: Backlog `order` (fehlend
  = ans Ende) → `created` → `id`; Doing/Done nach `created`. Speccify
  liest nativ in Rust (D14) und schreibt beim Verschieben **nur die
  `station:`-Zeile** um (byte-stabiler Rest) — Clients, die das
  Verzeichnis beobachten, ziehen live nach; alle zeigen dasselbe Board.
* **D20 — Pläne editierbar: strukturiert + Body** (BO, 2026-08-28
  „Ist gewünscht!", Form-Entscheid): Frontmatter-Felder (lifecycle,
  status, …) als Formular, darunter der Markdown-Body als Editor;
  Speichern über einen neuen Command `project_write_file` mit demselben
  Traversal-Guard wie `project_read_file` (nur unterhalb der
  Projektwurzel, kein `..`/absolut/`has_root`).
* **D21 — Work-Repo pro Projekt überschreibbar** (BO-Finding
  2026-08-28): Das Repo, in dem eigene Skills/Tools definiert werden
  (die Skill-Quelle fürs Expandieren), hat als Default das Dashboard-
  Setting; **Projekt-Settings** können ein anderes Dir/Repo wählen —
  Kundenprojekte bringen ihr eigenes Skill-Repo mit. Ablage der
  Projekt-Settings: klein anfangen (app-seitig je Projektpfad, wie
  Agent-Kommando), committbare Variante (`.agent/speccify/…`) erst,
  wenn der Gebrauch sie verlangt.
* **D22 — Terminal-Position wählbar** (BO-Finding 2026-08-28): das
  Agent-Terminal rechts **oder** unten, pro Projekt gemerkt. ✅ umgesetzt
  2026-08-28 (Toggle im Terminal-Kopf, localStorage, kein Remount — der
  ResizeObserver im TerminalPanel fittet nach).
* **D23 — Agent-Config im Dashboard editierbar** (BO-Finding
  2026-08-28): die globale Konfiguration des Agenten im Dashboard
  anzeigen/bearbeiten. claude: `~/.claude/settings.json` + globale
  `~/.claude/CLAUDE.md`. codex (geprüft 2026-08-28): global
  `~/.codex/config.toml`, projektseitig `.codex/config.toml`,
  Instruktionen `AGENTS.md` — passt ins selbe Editor-Muster
  (Datei-Liste je Agent + Editor mit Guard auf die erwarteten Pfade).
* **D24 — Skill-Quellen pro Projekt + Skill-Browser** (BO-Findings
  2026-08-28): pro Projekt **eine oder mehrere Skill-Quellen** (Repos,
  in denen Skills definiert werden), durchsuchbar, Import = `expand`.
  Liegen Skills **verschachtelt in Ordnern**, ist die Ordnerstruktur
  die Organisation im Browser **und** wandert als Quelle-Angabe in den
  expandierten Skill (Herkunft in `expansions.yaml`). Baut auf dem
  MCP-Source-Kanal (`source_list`/`add`, T4 im Plan skills-und-tools)
  und `speccify add/expand --library` auf; D21 ist der Spezialfall
  „eine Default-Quelle". → Kern von P4.

## Meilensteine

Reihenfolge nach Risiko: Erst das Gerüst auf macOS (billig, validiert die
UX gegen iKanban), dann **sofort** der Windows-Durchstich — er ist das
Hauptziel und das einzige echte Risiko; die Tabs auszubauen ist danach
planbare Arbeit auf beiden Plattformen zugleich.

### P1 — Projektfenster-Gerüst (macOS) ✅ (2026-08-26)

**Geliefert:** `project_cmd.rs` (Fenster-Registry Label→Wurzel,
`project_open`/`project_current`/`project_recent`/`project_plans`/
`project_skills`/`project_read_file`; Frontmatter/`expansions.yaml` via
`serde_yaml`; Traversal-Guard), `terminal_open` mit optionalem
`cwd`/`autostart` (Dashboard unverändert), Capability `project-*`,
`ProjectShell` (`main.tsx` erkennt den Fenstertyp am Label — synchron,
kein Flackern), Pläne-/Skills-Tab (Master-Detail, react-markdown,
Herkunfts-Banner), Projekte-Tab statt Composer-Tab, Recent-Liste in
eigener Datei `~/.speccify/recent-projects.json` (bewusst NICHT in
AppSettings — die SettingsView schreibt das ganze Objekt zurück und
hätte das Feld bei jedem Save geleert), Agent-Kommando pro Projekt in
localStorage (F3). E2E am eigenen Repo per AX-Scripting verifiziert:
Fenster öffnet, 2 aktive Pläne + Archiv (31), elf Skills mit Herkunft,
Terminal startet in der Projektwurzel und tippt den Autostart vor.
**Gelernt:** AX-`click` fokussiert WKWebView-Inputs nicht (`set focused`
schon); `keystroke` erzeugt echte Events, die React sieht — AX-`set value`
wäre an React vorbeigegangen.

**Fertig heißt:** „Projekt öffnen" im Dashboard öffnet ein Fenster mit
Drei-Bereiche-Layout; Pläne- und Skills-Tab zeigen echte Daten (lesend);
das Terminal rechts startet in der Projektwurzel.

1. Rust: `project_cmd.rs` — `project_open` (Dialog/Pfad → Fenster),
   `project_plans`, `project_skills` (Frontmatter-Parsing), zuletzt
   geöffnete Projekte in den Settings. Dashboard: Composer-Tab →
   Projekte-Tab (nur die Oberfläche; Rückbau des Composers erst P3, D18).
2. Frontend: `?project=`-Modus in der SPA; `ProjectShell` mit linker
   Tab-Leiste, Inhaltsbereich, rechter Terminal-Leiste (TerminalPanel
   wiederverwendet, cwd + Autostart pro Fenster).
3. Pläne-Tab (Liste + Markdown-Ansicht), Skills-Tab (Liste + SKILL.md-
   Ansicht, Herkunft aus `expansions.yaml`, falls vorhanden).
4. Dogfooding: **dieses Repo** als Projekt öffnen — es hat Pläne, elf
   Skills, drei Tool-Specs.

### P2 — Windows-Durchstich (✅ 2026-08-27 — Rest: claude-Login durch den BO, x86-Referenz)

**Geliefert (in der Parallels-VM, Windows 11 ARM64, komplett ferngesteuert
über den parallels-MCP vom Mac aus):** Toolchain in der VM (VS Build Tools
VCTools+ARM64+SDK nach `C:\BuildTools`, LLVM/clang für `ring`, pnpm 10,
VC-Redist; Git/Node/Rust waren da), Repo-Klon vom Home-Share nach
`C:\work\speccify` (safe.directory-Ausnahme für den UNC-Pfad nötig),
tsc+Vite grün, `cargo build -p speccify-desktop` grün (Sidecars + `uv.exe`
nach `binaries/`, `resources/`-Platzhalter — Engine-Payload bewusst nicht),
`cargo test` grün. App läuft; Projektfenster öffnet, Pläne-/Skills-Tab
zeigen echte Daten, **Terminal = PowerShell über ConPTY, cwd =
`C:\work\speccify`, Autostart vorgetippt** (D16 verifiziert per `whoami`).
**Drei Windows-Fixes daraus** (Commits `66fb7e6`, `25d000a`, `ae0b75e`):
`login_shell()` für Windows + `-l` nur auf Unix; `home_dir()` mit
USERPROFILE-Fallback; **`project_open` async** — ein synchroner Command
blockiert auf Windows beim Fenster-Bau den Main-Thread (wry#583), das
Fenster blieb auf about:blank; Verbatim-Präfix `\\?\` von `canonicalize`
abstreifen. Diagnose lief über WebView2-CDP (`:9222`), Sichtnachweis über
`prlctl capture`.
**Gelernt:** `prlctl exec` läuft als SYSTEM — interaktive Prozesse gehen
über `schtasks /ru <user> /it`; laufende Exe sperrt den Rebuild (`taskkill`
zuerst); in cmd niemals `%ERRORLEVEL%` in derselben Zeile prüfen.

**Nachtrag 2026-08-27 (P2-Restpunkte):**
* **STATUS_ENTRYPOINT_NOT_FOUND geklärt** — es war nie VC-Redist: Tauri
  importiert `TaskDialogIndirect`, das nur comctl32 **v6** exportiert; v6
  lädt der Loader nur mit Common-Controls-Manifest. tauri-build hängt das
  Manifest per `rustc-link-arg-bins` nur an die App-Exe — Test-Exen
  starteten deshalb gar nicht. Fix: `/DELAYLOAD:comctl32.dll` in build.rs
  (`50c0272`, erst `07e296f`); ein Manifest per `rustc-link-arg-tests`
  scheiterte, weil das nur Integrationstests abdeckt, nicht Lib-Unittests.
* **D17 ✅** — `speccify link` ersetzt Gits Symlink-Hülse (Textdatei aus
  Checkout ohne Symlink-Recht) und fällt ohne Symlink-Privileg auf eine
  **Junction** zurück (`9b0b71f`). In der VM als normaler Benutzer
  verifiziert: `<JUNCTION> skills → C:\work\speccify\.agent\skills`, alle
  elf Skills dahinter sichtbar.
* **CI-Job `desktop-windows`** (windows-latest, x64): pnpm-Build, Sidecars
  + resources-Platzhalter selbst herstellen (beides gitignored, sonst
  scheitert schon `cargo check` an tauri_build), `cargo test` (`90336b3`).
  Läuft beim nächsten Push.
* **Drei weitere Windows-Bugs** aus dem ersten echten Testlauf (`50c0272`):
  PATH-Auflösung fand `git.exe`/`claude.cmd` nicht (PATHEXT-Suche in
  `sidecar::find_in_dir`, auch für den Doctor); Backslash-Pfade galten
  nicht als explizit; Traversal-Guard ließ `/etc/passwd` durch (auf
  Windows laufwerkslos ⇒ nicht `is_absolute`, jetzt `has_root`).
  VM-Testlauf danach: **grün bis auf den PTY-Test** — ConPTY liefert im
  cargo-test-Harness nichts (als SYSTEM wie als interaktiver Benutzer
  reproduziert), obwohl dasselbe Muster im App-Terminal nachweislich
  läuft; der Test ist auf Windows `ignore` mit Begründung (`2b46458`),
  D16 bleibt über den E2E-Nachweis abgedeckt.
* **Claude Code 2.1.247 in der VM installiert** und im Projektfenster-
  Terminal gestartet (per CDP getippt): Onboarding läuft, steht am
  **Login-Prompt** — den Login kann nur der BO machen. Stolperstein
  fürs Produkt: PowerShell blockt das npm-Shim `claude.ps1`
  (ExecutionPolicy); `claude.cmd` startet ohne Policy-Änderung → der
  Terminal-Autostart sollte auf Windows `claude.cmd` bevorzugen (P3).

**„Fertig heißt" erfüllt (2026-08-28):** BO hat claude in der VM
eingeloggt (Claude Max, Opus 5); auf die Frage nach den Projekt-Skills
listet claude im Projektfenster-Terminal **alle elf Skills hinter der
Junction** (apple-developer-id-cert … storekit2-subscription-paywall,
inkl. speccify) — der komplette Satz aus „App startet, Projekt öffnet,
Tabs zeigen Daten, im Terminal läuft claude und findet die Skills" ist
damit wörtlich eingelöst.

**Offen aus P2:** CI-Lauf beim nächsten Push beobachten; x86-Referenz
wenn das Notebook da ist.

**Fertig heißt:** Das P1-Fenster läuft unter Windows — App startet, Projekt
öffnet, Tabs zeigen Daten, im Terminal läuft `claude` und findet die Skills
des Projekts.

**Umgebung (F4, BO 2026-08-26):** zuerst **Parallels** auf dem Mac; ein
x86-Windows-Notebook ist bestellt. Achtung: Parallels auf Apple Silicon =
**Windows 11 ARM** — gebaut wird dort nativ `aarch64-pc-windows-msvc`
(x64 liefe nur emuliert). Der CI-Job baut zusätzlich x64; das Notebook wird
später der x86-Referenz-Check. Beides sind Tier-1-Targets, der Code ist
derselbe — nur nichts aus dem Parallels-Erfolg über x64-Installer schließen.

1. Build: `cargo build -p speccify-desktop` + `tauri dev`/`build` auf
   Windows (WebView2, NSIS-Bundle); CI-Job `windows-latest` (x64) für
   Typecheck + Vite + `cargo check` des Desktop-Crates.
2. D16: Shell-Wahl unter Windows; PTY-Probe (ConPTY) mit xterm.js.
3. D17: Junction/Kopie in `speccify link` + `verify`; Probe: findet
   Claude Code auf Windows die Skills hinter `.claude/skills`?
4. Pfade: keine Annahmen über `/`; `dev.sh`-Äquivalent dokumentieren
   (die pnpm-Skripte reichen vermutlich — prüfen).
5. Bewusst **nicht** in P2: Engine-Payload, Sidecars, Composer, Signierung
   — das Dashboard darf auf Windows vorerst nackt sein; nur das
   Projektfenster muss stehen.

### P3 — Tabs vervollständigen (Kern ✅ 2026-08-28)

**Geliefert:** Board-Tab (D19: `.agent/board/*.md` nativ gelesen, eigener
Flat-Parser, Verschieben ersetzt nur die `station:`-Zeile — auf macOS E2E
belegt, Datei diff-gleich bis auf die Zeile), Plan-Editor (D20:
lifecycle/status als Formular + Body-Editor, `project_write_file` mit
geteiltem Traversal-Guard, unbekannte Frontmatter-Zeilen bleiben
wörtlich), Tools-Tab (Status je Plattform, „Fehlt auf dieser Plattform
(windows)“ in der VM gezeigt), MCPs-Tab (Server + Allowlist aus
settings.json und settings.local.json), Agent-Tab (CLAUDE.md/AGENTS.md/
.agent/AGENT.md + Agent-Kommando; Windows-Default `claude.cmd`),
**Composer-Rückbau komplett** (apps/composer, open_composer samt
Backend-Spawn-Helfern, /ui-Mount + composer_dist, CI-Jobs composer/
composer-e2e, Payload- und Skript-Anteile, Doku). Verifikation: 228
Pytest, 25 Rust-Desktop-Tests (7 project_cmd auch in der VM), Frontend-
Build, E2E-Fixture-Projekt auf macOS, Tab-Check per CDP auf Windows.

**Fertig heißt:** Tools-, MCPs- und Agent-Tab zeigen ihre Bestände; der
Tools-Tab macht Plattform-Lücken sichtbar; das **Board** (D19) zeigt die
iKanbanAI-Tickets und kann sie verschieben; Pläne sind **editierbar**
(D20) und die Änderung landet auf der Platte.

1. **Board-Tab (D19, BO-Erweiterung):** `.agent/board/*.md` nativ lesen,
   drei Spalten mit iKanban-Sortierung, Ticket-Detail (Body als
   Markdown), Verschieben zwischen Stationen (nur `station:`-Zeile
   umschreiben). `ready`/`needs_human` als Badges.
2. **Plan-Editor (D20, BO-Erweiterung):** im Pläne-Tab bearbeiten —
   Frontmatter-Felder als Formular + Body-Editor, Speichern via
   `project_write_file` (Guard wie read).
3. Tools-Tab: TOOL.md-Ansicht, Status je Plattform aus `expansions.yaml`,
   „fehlt auf dieser Plattform" prominent (die Brücke zum Terminal:
   der Agent implementiert, `tool check` verifiziert).
4. MCPs-Tab: `.mcp.json` **und** `permissions.allow` aus
   `.claude/settings.json` (F2) — zunächst lesend, Bearbeiten nach Bedarf.
5. Agent-Tab: `CLAUDE.md`/`AGENTS.md` anzeigen; Agent-Kommando-Wahl
   (`claude`/`codex`/frei) pro Projekt, falls nicht schon in P1 nötig.
   Windows-Merker: Autostart `claude` → `claude.cmd` bevorzugen
   (ExecutionPolicy blockt das ps1-Shim, P2-Befund).
6. **Composer-Rückbau (D18):** `apps/composer`, `open_composer`/
   Fenster-Code, `/ui`-Mount im Web-Backend, Payload-/CI-Anteile,
   Doku-Verweise.
7. Feinschliff aus dem P1/P2-Gebrauch (was der eigene Gebrauch verlangt,
   gewinnt gegen diese Liste).

### P4 — Skill-Quellen, Projekt-Settings, Agent-Config (BO-Findings 2026-08-28)

**Fertig heißt:** Ein Projekt kann seine Skill-Quellen wählen (Default =
Dashboard-Setting, D21), sie im **Skill-Browser** durchsuchen (Ordner =
Organisation, D24) und Skills von dort importieren (expand, Herkunft
inkl. Quell-Pfad in `expansions.yaml`); die Agent-Config ist im
Dashboard editierbar (D23, claude + codex).

1. Projekt-Settings mit Library-/Work-Repo-Override (D21).
2. Skill-Quellen-Verwaltung pro Projekt + Skill-Browser mit
   Ordner-Organisation + Import über expand (D24) — CLI/Core-Anteil
   (Quell-Pfad in der Herkunft) gehört zu skills-und-tools.md.
3. Agent-Config-Editor im Dashboard (D23).
4. Weiter nach Gebrauch: Ticket-Anlegen/-Editieren im Board,
   Board-Live-Watcher, Aktionen in der UI (expand anstoßen = Prompt ins
   Terminal), ask_bo im Projektfenster, Windows-Distribution
   (Installer, Signierung — **auf echtem Windows ohne Parallels**,
   BO-Finding 2026-08-28: Parallels war nur unsere Fernsteuer-Umgebung,
   Zielbild ist der native Windows-Rechner).

## Offene Fragen

Keine. F1–F4 vom BO beantwortet (2026-08-26):

* **F1** — Der Composer wird **nicht mehr gebraucht** → D18 (Rückbau in P3).
* **F2** — MCPs-Tab umfasst auch die **Allowlist** (`permissions.allow`);
  global bleiben MCPs Sache des Dashboards (Server-Tab).
* **F3** — Default `claude`, aber **`codex` muss wählbar sein** → das
  Agent-Kommando ist pro Projekt konfigurierbar, nichts fest verdrahtet.
* **F4** — Windows zuerst über **Parallels** (= Windows-ARM, siehe P2);
  ein x86-Notebook wird besorgt und ist dann die Referenz.
