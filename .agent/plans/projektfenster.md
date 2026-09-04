---
lifecycle: active
status: Bauen — P1–P3 geliefert und auf macOS/Windows verifiziert. D25 geliefert 2026-08-29: gemeinsamer Agent-Host-Vertrag, Claude- und Codex-Skill-Links, native MCP-Dateien, Terminal-Presets und Repository-Dogfooding. P4-Kern geliefert 2026-09-01 (Skill-Browser D24, Projekt-Quellen D21, Agents-Editor D23). Neu 2026-09-01: **P6 Website + integrierte Hilfe** — P6a (inkl. Screenshots, Download-Seite macOS+Windows, DE-Landing — 85 Seiten) + P6b geliefert; **P6c Signierung vorbereitet** (Windows-Job signiert secrets-getrieben via Azure Trusted Signing, BO-Aktionsliste in docs/release.md, PUBLIC_RELEASE_SIGNED erreicht jetzt den Pages-Build). 2026-09-02: **P6c macOS ✅** — v0.3.0 signiert+notarisiert als Draft (spctl: Notarized Developer ID), Website live mit neuer Download-Seite; offen: BO published den Draft, Azure-Setup für Windows-Signing. 2026-09-03: **D30 Playbooks geliefert** (`.agent/playbooks/` + Tab mit Editor). Offen: Tutorial-Stubs. Zuvor 2026-08-31: **P5 Agent-/Workflow-Parität** (BO stellt iKanbanAI zurück; alles außer Git/IDE kommt nach Speccify — D26–D29, W1–W7, P5 zieht vor den P4-Rest). **W1–W6 geliefert 2026-08-31, auf macOS UND Windows verifiziert** (VM: 38/38 Rust-Tests; Setup per Banner-Klick legt Junctions über den mklink-Fallback an, Policy-Block v1 sitzt, Board rendert). Committet (eaf2188 D25, 3bbceda P5, 3b80919 Windows-Pfadfix). Offen: W7-Feinschliff nach Gebrauch, Push/CI-Erstlauf. Offen: CI-Erstlauf beim nächsten Push, x86-Referenz. Läuft parallel zu `skills-und-tools.md` (BO-Ausnahme von der Ein-Plan-Regel).
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
  * MCPs: `.mcp.json` für Claude und `.codex/config.toml` für Codex.
  * Agent-Config: `CLAUDE.md`, `AGENTS.md`, ggf. `.agent/agent.md`.
* **iKanban AI als Vorbild, nicht als Abhängigkeit**: Der dortige Schnitt
  (Skills-Tab, Tools-Tab, MCP-Tab, Agent-Terminal, Board) ist die validierte
  UX — aber iKanban ist Swift/macOS. Das Projektfenster übernimmt den
  Schnitt in der Tauri-App, die auf Windows baut.
* **Wissen des Agenten**: kommt aus dem Projekt selbst. `.agent/agent.md`
  und `.agent/skills/` sind kanonisch; `CLAUDE.md`/`.claude/skills` und
  `AGENTS.md`/`.agents/skills` sind Host-Adapter. Das Terminal muss nur im
  richtigen cwd starten.

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
* **MCPs**: Server aus `.mcp.json` (Claude) und `.codex/config.toml`
  (Codex), dazu die Claude-Permission-Allowlist aus
  `.claude/settings.json`. Globale MCPs verwaltet weiterhin das Dashboard.
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
* **D17 — `speccify link` kennt Windows.** `.claude/skills` und
  `.agents/skills` zeigen auf `.agent/skills`
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
* **D25 — Agent-Host-Vertrag statt Claude-Sonderfall** (2026-08-29):
  `.agent/agent.md` und `.agent/skills/` sind die einzigen Wahrheiten.
  `speccify init/link` richtet Claude (`.claude/skills`) und Codex
  (`.agents/skills`) ein, auf Windows jeweils per Junction-Fallback.
  Einweisungen erzeugen Pointer für `CLAUDE.md` und `AGENTS.md`; MCPs bleiben
  im nativen Host-Format (`.mcp.json` bzw. `.codex/config.toml`). Der
  Projekt-MCP-Tab zeigt beide, das Terminal bietet Host-Presets, ein freies
  Kommando bleibt möglich. Weitere Hosts ergänzen nur die Adaptertabelle.

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
.agent/agent.md + Agent-Kommando; Windows-Default `claude.cmd`),
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

### P4 — Skill-Quellen, Projekt-Settings, Agent-Config (✅ Kern 2026-09-01)

**Geliefert:** D21 — Dashboard-Setting `skill_library` (Default-Quelle)
+ Projekt-Quellen in `.agent/settings.json` → `speccify.sources`
(Settings-Store aus W1). D24 — **Skill-Browser** im Skills-Tab
(„Quellen durchsuchen"): Quelle wählbar (Default + Projekt-Quellen,
+ Quelle über den Verzeichnis-Dialog, entfernen), rekursive Suche nach
`SKILL.md` (Rauschen wie node_modules/.git übersprungen), **Ordner-
struktur = Kategorien** (klappbar), Vorschau; **Import = Kommando ins
Agent-Terminal getippt** (`speccify add @scope/name --library … &&
speccify expand …`, Id aus `metadata.speccify.scope`; ohne scope klare
Meldung) — D14-Haltung: die App liest, der Agent handelt. D23 —
Dashboard-Bereich **Agents**: Whitelist-Editor für
`~/.claude/settings.json`, globale `~/.claude/CLAUDE.md`,
`~/.codex/config.toml`, `~/.codex/AGENTS.md` (read/write nur über Ids,
fehlende Dateien entstehen beim Speichern). E2E: Browser mit
Kategorien/Vorschau/Import-Notice belegt; der Terminal-Type-Kanal
(CustomEvent → terminal_write) ist implementiert, der visuelle
Terminal-Beweis steht aus (im Test lief dort gerade claudes
Trust-Prompt). Offen aus D24 (drüben in skills-und-tools): Quell-Pfad
in die Herkunft (`expansions.yaml`) beim Expand.

*Ursprünglicher Zuschnitt:*

> **Reihenfolge (2026-08-31):** P5 (Workflow-Parität) zieht vor den
> P4-Rest — der BO stellt iKanbanAI zurück und arbeitet täglich in
> Speccify; das tägliche Werkzeug braucht zuerst den Workflow. D21
> (Projekt-Settings) wandert nach P5-W1, weil `.agent/settings.json`
> dort ohnehin gebraucht wird.

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


### P5 — Agent- und Workflow-Parität (BO-Auftrag 2026-08-31)

> **Auslöser (BO):** „Wir wollen iKanbanAI vorerst zurückstellen und die
> Agent- und Workflow-Features hier mit einbauen. Speccify soll alles
> können, was iKanbanAI kann — außer Git- und IDE-Features."

**Kernbefund der Quelltext-Analyse (2026-08-31):** iKanbanAI ist selbst
längst agent-native. Der frühere Orchestrator (PO-/Developer-Agenten,
Team-Chat, In-Process-LLM) wurde dort entfernt; heute gilt: **die Policy
ist Text** (`.agent/AGENT.md`, versioniert, v13), der Agent arbeitet im
Terminal, die App **beobachtet nur Dateien** und schreibt selbst History
für eigene Aktionen. Die einzige „Ausführung" läuft über den lokalen
Exec-MCP — eine Krücke der App-Store-Sandbox. Speccify (Tauri) darf
direkt spawnen. Parität heißt also überwiegend: **Dateiformate + Watcher
+ UI**, nicht „einen Orchestrator bauen".

#### Entscheide (Fortsetzung)

* **D26 — Agent-native, Policy als Text.** Kein Orchestrator-Code in P5.
  Speccify erzeugt und versioniert den Workflow-Policy-Text im Projekt
  (Board-Regeln: aus dem aktiven Plan Tickets schneiden, oberstes
  Backlog-Ticket nach `order`, **WIP = 1** in Doing, zu Großes splitten,
  Q&A-Protokoll, „History schreibst du selbst"). Die frühere
  Orchestrator-Blaupause (decide(snapshot): `needs_human` **vor**
  `ready` prüfen; WIP>1 ⇒ eskalieren; Ping-Pong ≥ 3 aus der History;
  Idle-Watchdog 120 s) ist dokumentiert und kommt erst nach
  Gebrauchsevidenz als Code (P6-Kandidat).
* **D27 — Die Formate werden Speccify-Formate.** Wir übernehmen die
  Dateiformate 1:1 und kanonisieren sie bei uns (Speccify definiert,
  iKanbanAI bleibt kompatibler Client — Rollen wie in D19):
  - History: `.agent/board/history/<ticket-id>/index.jsonl`, append-only,
    Events `ticket_created|ticket_edited|station_changed|agent_run`,
    `actor: user|system|agent:<name>`; nur `agent_run` trägt
    `tokens_in/out/cache_read/cache_write`, `duration_ms`. Effektiver
    Input = in + cache_read + cache_write (sonst „mehr out als in").
  - Q&A: `## Questions` im Ticket-Body, `### Q<n> · open · <ts>` /
    `### A<n> · bo · <ts>`, Frontmatter `open_question: Q<n>` (immer die
    älteste offene); tolerant lesen, kanonisch schreiben; `needs_human`
    bleibt getrennt (Antwort darf die Abnahme-Markierung nicht löschen).
  - Aktionen: `.agent/actions.json` (name, command = Id, description,
    source agent|bo, confirmed, toolbar, shortcut, inputs mit kinds
    text/number/file/folder/choice/color, target local|parallels;
    `{name}`-Platzhalter; argv ohne Shell; `toolui:<kind> <paramsJSON>`).
  - Freigaben: `.agent/exec-allowlist.json` + `.agent/exec-pending.json`
    (wire-kompatibel — unser exec-mcp nutzt sie heute schon).
  - Projekt-Settings: `.agent/settings.json` (Punkt-Notation, unbekannte
    Schlüssel überleben, keine Secrets) — erfüllt zugleich D21.
* **D28 — Ausführung nativ.** Aktionen startet die App als eigenen
  Prozess (Supervisor/portable-pty vorhanden); Live-Output gestreamt,
  Stop = Prozess killen, Puffer „Ende behalten" (~200k, Render 40k),
  Fortschrittsmarker `[3/20]` in den letzten Zeilen. Der exec-MCP bleibt
  für gesandboxte Clients — die eigene App braucht ihn nicht (dieselbe
  Haltung wie D14).
* **D29 — Ausgeschlossen:** Git (InProcessGit/GitUI), IDE/Editor
  (Tree, Editor-Tabs, Symbol-Index, Emacs-Keymap), On-Device-Summaries
  (Apple Foundation Models, macOS-26-only — auf Windows nicht
  verfügbar; Plan-Zusammenfassungen macht bei uns der Agent),
  `.agent/chats/` (Altlast der entfernten Laufzeit, kein Code liest sie).
* **D30 — Playbooks (BO, 2026-09-03). ✅ geliefert 2026-09-03:**
  stehende Anleitungen unter `.agent/playbooks/<name>.md` — im
  Gegensatz zu Plänen ohne Lifecycle: ein Plan wird wie ein Projekt
  abgearbeitet und ist dann fertig, ein Playbook (Release, Deploy,
  Onboarding) bleibt und wird wiederverwendet. Format: optionales
  flaches Frontmatter (`description:`) + Markdown; Titel = erste
  `# `-Überschrift. Geliefert: `playbook_cmd.rs` (list/create/delete,
  Slug mit Umlaut-Transliteration, Traversal-Guard; Inhalt über
  `project_read_file`/`project_write_file`), Watcher-Bereich
  `playbooks`, Tab „Playbooks" mit Liste/Ansicht/Editor
  (description+Body, byte-stabil via assemblePlan), „+ Playbook",
  Löschen mit Rückfrage, „Als Prompt kopieren" für den Agenten;
  `.agent/agent.md`-Strukturliste + `docs/app-bedienen.md` (→ Hilfe-Tab)
  ergänzt. 45/45 Desktop-Tests, Typecheck grün. Nicht das alte
  Produkt-„Playbook" (das hieß nur so und wurde zu Skills) — hier sind
  es Projekt-Runbooks.

#### Meilensteine

**W1 — Policy, Setup, Projekt-Settings. ✅ 2026-08-31**
Geliefert: `workflow_setup.rs` — versionierter Policy-Block (v1,
`<!-- speccify:workflow:begin/end -->`-Marker-Merge, fremder Inhalt bleibt
Byte für Byte), `project_workflow_status/install` (Zustände
missing/outdated/current + pending-Liste; Host-Dateien ohne Verweis werden
nur gemeldet, nie angefasst; angepasste Skills bleiben unberührt),
Ticket-Skills `/ticket-next`+`/ticket-ask`, Scaffold, Skill-Links für
beide Hosts (Windows: symlink→mklink-/J-Fallback), Settings-Store
`project_settings_get/set` (Punkt-Notation, unbekannte Schlüssel
überleben, null löscht, leere Datei verschwindet) und der
Workflow-Banner im Projektfenster. **„Fertig heißt" bestanden:** im
Fixture per Banner-Klick eingerichtet; `claude -p` hat daraufhin den
aktiven Plan in zwei Backlog-Tickets geschnitten (order, plan:,
ticket_created-History) und genau eines protokollgerecht abgearbeitet
(Doing→Done, station_changed + agent_run mit Token-Feldern,
Fortschrittsnotiz, Werk-Datei angelegt) — ohne dass die App steuert.
Verifikation: 31 Rust-Tests, Typecheck/Build, clippy, E2E.

*Ursprünglicher Zuschnitt:* Versionierter Workflow-
Abschnitt in `.agent/agent.md` (Marker-Merge `speccify:begin/end`,
fremder Inhalt bleibt; Zustände missing/outdated/current mit Banner —
bewusst Knopf, nicht automatisch), Host-Pointer wie gehabt (D25),
Skills `/ticket-next` und `/ticket-ask` als mitgelieferte Griffe,
`.agent/settings.json`-Store (D21/D27). Scaffold `ensure` für
`.agent/{board,plans}`.
**Fertig heißt:** Ein frisches Projekt bekommt per Klick die komplette
Einweisung; claude schneidet daraufhin aus dem aktiven Plan Tickets und
arbeitet das oberste ab — ohne dass die App etwas steuert.

**W2 — Watcher-Basisdienst + Live-Board. ✅ 2026-08-31**
Geliefert: `project_watch.rs` — ein Thread je Projektfenster, alle 2 s
Fingerprint (Pfad+mtime+Größe) je Bereich (board/plans/skills/tools/
actions/settings/agent/mcps), Änderung ⇒ `project-changed`-Event mit
Bereichsliste; erster Lauf primt still, Thread stirbt mit dem Fenster.
**Bewusst Poll-only statt notify-Events**: In-place-Schreiben erzeugt
ohnehin keine Verzeichnis-Events, der Poll ist der notwendige
Mechanismus — Events wären nur Latenz-Optimierung und kämen bei Bedarf
dazu. Frontend: alle Tabs + Workflow-Banner laden bei ihrem Bereich
nach (Plan-Editor ist geschützt: kein Reload mitten ins Editieren).
E2E: Ticket von außen angelegt + station geändert ⇒ Board zeigt beides
binnen ~4 s ohne jeden Klick.

*Ursprünglicher Zuschnitt:* Ein Dienst je Projektfenster:
Verzeichnis-Events (notify) **plus 2-s-Fingerprint-Poll** (Name+mtime+
Größe — Agenten schreiben in place, das erzeugt kein Event). Board,
Pläne, Aktionen laden live statt per „Aktualisieren"-Knopf.
KPI-/Parse-Arbeit off-main mit mtime-Cache.

**W3 — Ticket-Lifecycle voll + History + KPIs. ✅ 2026-08-31**
Geliefert: `board_cmd.rs` — `project_ticket_create` (Id = Titel-Slug +
Hex-Suffix, atomar), `project_ticket_save` (Editor-Sheet in einem Rutsch;
byte-stabiles Frontmatter-Update: bekannte Zeilen ersetzt/ergänzt/
entfernt, unbekannte bleiben in Reihenfolge), `project_ticket_delete`
(Guard auf .agent/board), `project_ticket_history` (tolerant, korrupte
Zeilen übersprungen, neueste zuerst), `project_board_kpis` (nur
agent_run; effektiver Input = in + cache_read + cache_write); App-
Aktionen (create/save/move) loggen History mit `actor: user`. UI:
„+ Ticket" + Editor-Sheet (Titel/Station/order/ready/braucht BO/plan/
Body, Löschen mit Rückfrage), Drag&Drop zwischen Spalten, Done-Spalte
nach `plan` gruppiert (klappbar), KPI-Chip mit aufklappbarer
Läufe-Liste, History im Ticket-Detail (gedeckelt 100). E2E: KPI-Chip
zeigt claudes echten Lauf aus W1 („1 Lauf · ↑30.0k ↓1.5k · 2m");
Edit-Sheet über die UI gespeichert ⇒ `ready: true` byte-stabil in der
Datei + `ticket_edited`-History. (AX-Tippen in Modal-Felder ist als
Testwerkzeug unzuverlässig — die Commands sind Rust-getestet, DnD
probiert der BO mit echter Maus.)

*Ursprünglicher Zuschnitt:* Anlegen/Editieren/
Löschen (Editor-Sheet), `ready`/`needs_human`/`order`/`plan`/`model`,
Body-Append ohne Frontmatter-Anfassen, Id = Titel-Slug + 4-Zeichen-
Suffix, atomar schreiben; App-Aktionen loggen History (`actor: user`).
Drag&Drop zwischen Spalten, Done-Gruppierung nach `plan` (klappbar).
KPI-Kopfzeile („n Läufe · ↑… ↓…", effektiver Input!) + Aktivitätsliste
aus `agent_run`-Events; History im Ticket-Detail (gedeckelt, ~200).

**W4 — Q&A + „braucht mich" + Notifications. ✅ 2026-08-31**
Geliefert: Q&A-Protokoll in Rust (`parse_questions` tolerant — Trenner
·/-/|, Marker optional, mehrzeilige Texte; `project_ticket_answer`
schreibt kanonisch `### A<n> · bo · <ts>`, verweigert Doppelantworten,
rückt `open_question` auf die nächste älteste offene Frage oder
entfernt die Zeile — Frontmatter byte-stabil, `needs_human` bleibt
unberührt), `open_question` im Board-Eintrag, Fragen-Sektion im
Ticket-Detail ganz oben (orange, Antwortfeld, „Answered (n)" klappbar;
Questions aus der Body-Anzeige gefiltert), Karten-Badge „?",
Board-Filter „braucht mich" (`open_question` ∨ `needs_human`, bewusst
nicht persistiert). Watcher meldet **neue** offene Fragen als
System-Notification (tauri-plugin-notification; erster Lauf primt
still, Dedupe `<ticket>|Q<n>`, unabhängig vom aktiven Tab) + Event
`open-question`. E2E: Frage von außen ins Doing-Ticket ⇒ Badge live,
Antwort über die UI ⇒ kanonischer A-Block + `open_question` entfernt +
History „Frage Q1 beantwortet". Offen: die sichtbare Zustellung der
macOS-Notification (Dev-App + Berechtigungsprompt) im Gebrauch prüfen.

*Ursprünglicher Zuschnitt:* Fragen-Sektion im
Ticket-Detail ganz oben (Antwortfeld, „Answered (n)" klappbar),
Board-Filter „braucht mich" (`open_question` ∨ `needs_human`),
OpenQuestionWatch-Semantik (erster Durchlauf primt still; nur die
älteste Frage je Ticket; Dedupe `<ticket>|Q<n>`), System-Notification
über das Tauri-Notification-Plugin, projektweit unabhängig vom Tab.

**W5 — Aktionen. ✅ 2026-08-31**
Geliefert: `actions_cmd.rs` — `.agent/actions.json` lesen/anlegen/ändern/
löschen (command = Id; tolerant: unbekannte Input-Kinds bleiben erhalten),
`project_action_confirm` = **ein** Klick macht aus einem Vorschlag oder
Pending-Eintrag eine bestätigte Aktion **plus** permanenten Allowlist-
Eintrag (wire-kompatibel zum exec-MCP) und räumt exec-pending auf.
Ausführung nativ (D28): argv ohne Shell (shell-words), Spawn im
Projekt-cwd mit angereichertem PATH, stdout+stderr zeilenweise als
`action-output`-Events, `action-exit` mit Code/Dauer, Stop killt,
Registry räumt beim App-Ende. UI: Aktionen-Tab (Bestätigte/Vorschläge/
Neu), Input-Formulare (text/number/choice/file/folder via Dialog/color;
`{name}`-Substitution), Live-Output-Panel (Autoscroll, Kappung 2000
Zeilen, Fortschritt `[3/20]` aus den letzten Zeilen), **Chart-Renderer**
(`{"kind":"chart",…}`-Zeile → SVG live, line + bar, Legende; Pflicht
strikt, Optionales tolerant, Rückfall auf Text). `toolui:`- und
Parallels-Aktionen erscheinen mit „folgt"-Badge (Panel-Registry und
vm_exec nach Bedarf, W7). E2E: Pending „ls -la notes" per Klick
bestätigt (Aktion + Allowlist permanent + pending-Datei weg); Demo-Lauf
mit Fortschritt, Chart (2 Serien) und exit 0 im Live-Panel.

*Ursprünglicher Zuschnitt:* Aktionen-Tab (bestätigte/Vorschläge/manuell,
Reset), Ausführung nativ (D28) mit Live-Output-Fenster, Stop,
Fortschrittsring, Chart-Renderer (`{"kind":"chart",…}`-Zeile → Diagramm,
live; Pflichtfelder streng, Optionales tolerant, nie Output verlieren),
Pending-Import (abgelehnter Agent-Befehl → unbestätigte Aktion;
Bestätigen = confirmed + permanente Allowlist), Shortcuts/Toolbar.
`toolui:`-Panels als Registry (chart zuerst; sqlite nach Bedarf).

**W6 — Plan-Lifecycle + Komfort. ✅ 2026-08-31**
Geliefert: `plan_cmd.rs` — `project_plan_activate` mit der Invariante
**höchstens ein aktiver Plan** (bisheriger active → onHold, nur
Frontmatter, Archiv unangetastet; Achtung: im Speccify-Repo selbst gilt
die BO-Ausnahme zweier aktiver Pläne — dort einfach nicht klicken),
`escalation:`-Frontmatter (einzeilig oder Block, `reason` zählt) im
Plan-Eintrag + rotes Banner mit „Auflösen" (`clear_escalation` entfernt
nur diese Zeilen), Lifecycle-Badges (active/onHold/done/draft/research).
**Kern-Geste:** Das Board zeigt den aktiven Plan aufklappbar über den
Spalten (live über den Watcher) — Plan und Board gleichzeitig sichtbar.
„Als Prompt kopieren" auf Plan und Ticket (Pfad-Referenz + Markdown-
Zaun, Zaunlänge gegen Backticks im Inhalt). E2E: Aktivieren parkte den
bisherigen Plan nachweislich (Dateien), Banner erschien und „Auflösen"
entfernte die Zeile, die Zwischenablage trug den fertigen Prompt.

*Ursprünglicher Zuschnitt:* Lifecycle `draft|active|onHold|done|
research` mit Invariante **genau ein active** (activate ⇒ bisheriger
auf onHold), `escalation:`-Frontmatter + rotes Banner + „Auflösen";
Plan und Board **gleichzeitig sichtbar** (Split in der Mitte — die
Kern-Geste); „Als Prompt kopieren" für Ticket/Plan-Ausschnitt
(Markdown mit `Pfad:Zeile`-Referenz); Plan-Tabs nach Bedarf.

**W7 — Feinschliff nach Gebrauch.** Kandidaten: projektweite Auswahl
(Board ↔ Inspector), Onboarding-Seiten, Aktivitäts-Center in der
Titelleiste (in-memory, cap 500), Orchestrator-Code (D26-Blaupause),
Detached-Fenster für Pläne/Aktionen.

**W7a ✅ 2026-09-04 — Xcode-/iKanban-Layout (BO-Auftrag).** Frage war,
ob das Muster Navigator | Inhalt | Inspektor mit Terminal wahlweise
rechts oder unten unter Tauri Probleme macht. Befund: keine — das
Fenster ist ein einziges WebView, Splitter und Seitenleisten sind
reines DOM; die einzige echte Falle ist der PTY: das Terminal muss beim
Umdocken dasselbe React-Element bleiben, sonst stirbt die Shell. Lösung
ist ein CSS-Grid in `ProjectShell.tsx`, in dem das Terminal nur seine
Grid-Zelle wechselt (verifiziert: gleicher DOM-Knoten nach rechts →
unten → rechts). Geliefert: `lib/layout.ts` (Layout-State, Limits,
localStorage pro Projekt, Migration des alten `terminalPosition`),
`components/SplitHandle.tsx` (Pointer-Capture, hält auch über dem
xterm-Canvas; Doppelklick = Reset), `lib/inspector.tsx` (ein DOM-Slot
pro Tab in der rechten Seitenleiste, Tabs portalen ihr Detail hinein
und behalten ihren State; ohne Seitenleiste Fallback inline), Toolbar
mit drei Xcode-Schaltern, rechte Seitenleiste mit Tabs Inspektor |
Terminal. Erste Nutzung: das Ticket-Detail des Boards wohnt jetzt im
Inspektor, eine neue Auswahl holt den Inspektor-Tab nach vorn. Gefunden
und gefixt beim Prüfen: inline Ref-Callbacks für die Slots lösten eine
Render-Endlosschleife aus → stabile Callbacks je Tab. Verifikation:
Typecheck grün; Layout im Browser per Playwright gegen eine
Tauri-Attrappe (`apps/desktop/dev/mock.html` am Vite-Dev-Server)
durchgespielt — Griffe, Umdocken, Ein-/Ausblenden, Reload aus
localStorage. **BO-Entscheid 2026-09-04: Terminal-Default unten** — der
Inspektor-Fokus bei neuer Auswahl legt das nahe; rechts bleibt als
Option (Default rightWidth 400, Migration nur noch für alte
„rechts"-Wahl). **Offen (W7b):** Pläne/Playbooks/Skills nutzen den
Inspektor noch nicht (ihre Listen könnten in den Navigator, die
Metadaten in den Inspektor wandern); Tastaturkürzel für die Schalter;
Prüfung in der echten App auf macOS und Windows durch den BO.

**Nicht in P5:** alles aus D29; Discovery-/Speccify-MCP-Anbindung der
iKanbanAI-Seite (wird obsolet — Speccify ist das Produkt selbst).


### P6 — Website-Neuaufbau + integrierte Hilfe (BO-Auftrag 2026-09-01)

> **BO:** Website überarbeiten, Inhalte von AgentFundamentals übernehmen
> und ausbauen (agent-fundamentals wird zurückgestellt); dazu eine
> integrierte Hilfe/Anleitung wie in Toyota/tec-e2e.

**Erhebung (2026-09-01, Quelltexte gelesen):**

*AgentFundamentals* (`~/Desktop/Work/AgentFundamentals`) ist eine
fertige, live deployte Astro-7/Starlight-Site — **derselbe Stack wie
`apps/marketing`** —, zweisprachig EN/DE (je Seite beide Sprachen),
~20 200 Wörter in 50 Dateien, redigiert und aus echten Projekten belegt.
Vier Sektionen: `tutorial/` (11 Seiten, 4Notice-Durchlauf; 1 Stub
„submission", 1 „in progress" fastlane), `fundamentals/` (.agent-Ordner,
Skills, Tools, MCPs — der konzeptionelle Unterbau), `speccify/`
(5 Seiten: overview/expand/execute/evaluate/walkthrough — direkt unsere
Produkt-Doku), `ikanban-ai/` (5 Seiten — beim Übernehmen auf das
Speccify-Projektfenster umschreiben; passt zur Rollen-Umkehr aus D19).
Screenshots fehlen durchgängig (Platzhalter-Notes).

*tec-e2e-Hilfe* (`~/Desktop/Work/Toyota/tec-e2e`): ein **Hilfe-Tab, der
die Markdown-Dateien des Repos direkt rendert** — kein Doku-Build, keine
zweite Kopie. Bausteine: Rust-Registry (`docs.rs`: feste Slug-Liste mit
Titel/Beschreibung/Pfad; `list_docs` filtert auf existierende Dateien,
`read_doc` nur über Slugs), `HilfeView` (Master-Detail, react-markdown +
remark-gfm, Quellpfad über dem Text, erstes Dokument auto-geöffnet),
drei Redaktions-Tests (Slugs eindeutig, keine Pfad-Ausbrüche,
Beschreibungen > 20 Zeichen). Kernstück ist eine eigens geschriebene
Anleitung (`docs/app-bedienen.md`).

**P6a-Kern ✅ 2026-09-01:** Alle vier AgentFundamentals-Sektionen
übernommen (EN+DE, `ikanban-ai/` → `app/` und komplett auf die
Speccify-App umgeschrieben — Projektfenster-Tabs, Workflow-Banner,
native Aktionen, Quellen-Browser; null verbleibende iKanban-Treffer),
Tutorial auf das Duo App+CLI umgestellt, Sidebar/Locales (EN/DE) in
`astro.config`, Landing neu („Share the contract, not the
implementation" — Tool-Contract-Ausschnitt, Expand/Execute/Evaluate/
Board, App-Sektion), README neu auf die aktuelle Geschichte,
Playbook-/Viewer-Altseiten samt Sync-Mappings entfernt (Quell-Dokus
als docs/archive-*.md). Build: **83 Seiten** (vorher 21), keine toten
internen Verweise auf gelöschte Sektionen.

**P6a-Rest ✅ 2026-09-01 (42c975c):** 5 App-Screenshots aus der
laufenden App am W1-Fixture (Fixture mit offener Frage, exec-pending
und Herkunft präpariert), alle 12 Platzhalter EN+DE ersetzt;
Download-Seite auf macOS+Windows (SmartScreen-Box, dev.ps1-Selbstbau);
deutsche Landing unter `/de/`. Build 85 Seiten. **`app/plans`-Seite ✅
2026-09-03** („Plans & playbooks", EN+DE, Build 88 Seiten): Lifecycle
mit Ein-Aktiver-Invariante, Aktivieren/Archivieren, Eskalations-Block,
„Als Prompt kopieren", Playbooks (D30) und die Abgrenzung
Skill/Playbook/Plan; Overview-Seiten und integrierte Hilfe auf die
echte Tab-Reihenfolge (Playbooks vor Plänen) gezogen. **Offen in
P6a:** Tutorial-Stubs (`submission`, `fastlane-and-asc` — brauchen
BO-Material), Feinschliff nach BO-Lektüre.

**P6c Signierung (vorbereitet 2026-09-01):** beide Release-Jobs sind
rein secrets-getrieben scharf zu schalten — macOS war fertig
(APPLE_*-Secrets), **Windows jetzt auch**: `release-windows` prüft auf
sechs `AZURE_*`-Secrets und signiert dann Exe, Sidecars und Installer
über Azure Trusted Signing (`trusted-signing-cli` als `signCommand`);
ohne Secrets weiter unsigniert. `pages.yml` reicht
`PUBLIC_RELEASE_SIGNED` jetzt wirklich in den Site-Build (war
verdrahtet, kam aber nie an). Die komplette BO-Aktionsliste — welche
Secrets, wie erzeugen, `gh secret set`-Kommandos, Empfehlung Azure
Trusted Signing über OV-Zertifikat — steht in `docs/release.md`
(„Signierung scharf schalten"). Secrets/Schlüssel erzeugt der BO
selbst; danach `PUBLIC_RELEASE_SIGNED=true` und der Release-Body-Text.

**P6c macOS ✅ 2026-09-02:** Erster signierter+notarisierter Release
(v0.3.0, Draft) — verifiziert am per Browser-Quarantäne simulierten
Download: `spctl accepted, source=Notarized Developer ID`, Ticket
gestapelt, alle 5 Binaries (App + 4 Sidecars inkl. re-signiertem uv)
einzeln geprüft. Stolpersteine dokumentiert für die Nachwelt:
GNU-base64 im PATH kennt `-i` nicht; Passwort muss zur *richtigen*
p12 gehören (Developer ID, nicht Apple Development); Zertifikat lag im
System-, der Schlüssel im Anmelde-Schlüsselbund (Zertifikat per
`security import` in die Anmeldung kopiert, dann Export möglich).
Windows-Job grün nach shasum→sha256sum-Fix (e98c855) und
Tag-Umsetzen; Draft trägt dmg + setup.exe + msi + app.tar.gz.
**Offen:** BO published den Draft; `PUBLIC_RELEASE_SIGNED` bleibt
false, bis auch Windows signiert (das Flag schaltet beide Warnboxen);
Azure-Setup (BO oder Teammitglied — Publisher-Name bedenken).

**Zuschnitt (Vorschlag):**
1. **P6a Website:** `speccify/`- und `fundamentals/`-Sektionen nach
   `apps/marketing` übernehmen (EN+DE), Landing auf die neue Geschichte
   ziehen, `ikanban-ai/`-Seiten als Projektfenster-Guide umschreiben,
   Tutorial als eigene Sektion mitnehmen und die zwei Lücken schließen;
   Screenshots aus der echten App nachschießen. Die alte
   Playbook-Erzählung (bekanntes offenes Ende) fällt dabei mit weg.
2. **P6b Integrierte Hilfe: ✅ 2026-09-01.** `help_docs.rs` — feste
   Slug-Registry, Inhalte **einkompiliert** (die verteilte App hat kein
   Repo neben sich; der angezeigte Quellpfad sagt trotzdem, welche Datei
   man ändert), Redaktions-Test nach tec-e2e-Vorbild (Slugs eindeutig,
   Beschreibungen > 20 Zeichen, Pfade bleiben im Repo). Fünf Dokumente:
   neue Anleitung `docs/app-bedienen.md` (der schnelle Weg, die Tabs,
   Fragen, Troubleshooting), Workflow-Policy, README, git-sources,
   toolkit. `HelpView` (Master-Detail, erstes Dokument auto-offen) als
   Dashboard-Sektion „Hilfe" UND Projektfenster-Tab „Hilfe".

   *Ursprünglicher Zuschnitt:* Hilfe-Tab nach tec-e2e-Muster in Dashboard
   **und** Projektfenster (Rust-Slug-Registry über unsere Repo-Doku +
   eine neue `docs/app-bedienen.md`-artige Anleitung; Markdown.tsx
   existiert). Redaktions-Tests wie im Vorbild.

**Fertig heißt:** speccify.io erzählt die Skill-/Tool-/Workflow-
Geschichte (statt Playbooks) mit den AgentFundamentals-Inhalten, und in
der App beantwortet ein Hilfe-Tab „wie bediene ich das?" ohne externe
Doku.

## Offene Fragen

Keine. F1–F4 vom BO beantwortet (2026-08-26):

* **F1** — Der Composer wird **nicht mehr gebraucht** → D18 (Rückbau in P3).
* **F2** — MCPs-Tab umfasst auch die **Allowlist** (`permissions.allow`);
  global bleiben MCPs Sache des Dashboards (Server-Tab).
* **F3** — Default `claude`, aber **`codex` muss wählbar sein** → das
  Agent-Kommando ist pro Projekt konfigurierbar, nichts fest verdrahtet.
* **F4** — Windows zuerst über **Parallels** (= Windows-ARM, siehe P2);
  ein x86-Notebook wird besorgt und ist dann die Referenz.
