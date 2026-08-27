---
lifecycle: active
status: Bauen — P1 geliefert 2026-08-26; P2-Kern geliefert 2026-08-27 (App läuft in der Parallels-VM auf Windows 11 ARM64: Projektfenster, Tabs, ConPTY-Terminal — E2E über den parallels-MCP + WebView2-CDP verifiziert). Offen aus P2: CI-Job (x64), D17 Junction, Claude-Code-Installation in der VM. Nächster Schritt P3. Läuft parallel zu `skills-und-tools.md` (BO-Ausnahme von der Ein-Plan-Regel).
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

### P2 — Windows-Durchstich (Kern ✅ 2026-08-27)

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
**Gelernt:** `cargo test`-Binaries brauchen VC-Redist (STATUS_ENTRYPOINT_
NOT_FOUND war eine früher fehlende `vcruntime140.dll` — Redist zuerst
prüfen); `prlctl exec` läuft als SYSTEM — interaktive Prozesse gehen über
`schtasks /ru <user> /it`; laufende Exe sperrt den Rebuild (`taskkill`
zuerst); in cmd niemals `%ERRORLEVEL%` in derselben Zeile prüfen.
**Offen aus P2:** CI-Job `windows-latest` (x64), D17 (Junction in
`speccify link`), `claude` in der VM installieren (dann der Skill-Test aus
„Fertig heißt"), x86-Referenz wenn das Notebook da ist.

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

### P3 — Tabs vervollständigen

**Fertig heißt:** Tools-, MCPs- und Agent-Tab zeigen ihre Bestände; der
Tools-Tab macht Plattform-Lücken sichtbar.

1. Tools-Tab: TOOL.md-Ansicht, Status je Plattform aus `expansions.yaml`,
   „fehlt auf dieser Plattform" prominent (die Brücke zum Terminal:
   der Agent implementiert, `tool check` verifiziert).
2. MCPs-Tab: `.mcp.json` **und** `permissions.allow` aus
   `.claude/settings.json` (F2) — zunächst lesend, Bearbeiten nach Bedarf.
3. Agent-Tab: `CLAUDE.md`/`AGENTS.md` anzeigen; Agent-Kommando-Wahl
   (`claude`/`codex`/frei) pro Projekt, falls nicht schon in P1 nötig.
4. **Composer-Rückbau (D18):** `apps/composer`, `open_composer`/
   Fenster-Code, `/ui`-Mount im Web-Backend, Payload-/CI-Anteile,
   Doku-Verweise.
5. Feinschliff aus dem P1/P2-Gebrauch (was der eigene Gebrauch verlangt,
   gewinnt gegen diese Liste).

### P4 — Nach Bedarf (bewusst offen)

Kandidaten, erst nach Gebrauchsevidenz aus P1–P3: Aktionen in der UI
(expand anstoßen = Prompt ins Terminal tippen statt eigener Code-Pfad),
Plan-Board statt Liste (iKanban-Anleihe), ask_bo im Projektfenster,
Windows-Distribution (Installer, Signierung).

## Offene Fragen

Keine. F1–F4 vom BO beantwortet (2026-08-26):

* **F1** — Der Composer wird **nicht mehr gebraucht** → D18 (Rückbau in P3).
* **F2** — MCPs-Tab umfasst auch die **Allowlist** (`permissions.allow`);
  global bleiben MCPs Sache des Dashboards (Server-Tab).
* **F3** — Default `claude`, aber **`codex` muss wählbar sein** → das
  Agent-Kommando ist pro Projekt konfigurierbar, nichts fest verdrahtet.
* **F4** — Windows zuerst über **Parallels** (= Windows-ARM, siehe P2);
  ein x86-Notebook wird besorgt und ist dann die Referenz.
