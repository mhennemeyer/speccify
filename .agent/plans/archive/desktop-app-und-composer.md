---
lifecycle: done
status: A0+A1 abgenommen 2026-07-25 (Desktop-App-Übernahme + Composer-Fenster); offen nur der BO-Walkthrough docs/composer-tristate-walkthrough.md
sessionId: desktop-app-und-composer
---
# Plan: Desktop-App-Übernahme (dotagent) & Composer-Integration

> **Abgeschlossen 2026-07-25:** A0 + A1 geliefert und vom BO abgenommen
> („sieht soweit ok aus"). Der Feinschliff (ehem. A2) geht im
> Nachfolge-Plan [`toolkit-discovery-terminal.md`](./toolkit-discovery-terminal.md)
> auf (Settings, Terminal-Seitenleiste, ask_bo-Chat-Elemente).

**Angelegt 2026-07-24 nach BO-Umpriorisierung** („Erst die dotagent-App
übernehmen, den Composer mit in diese App, App umbenennen; Migration nach
Rust als neuer eigener Plan"). Ersetzt die Stufen R3/R4 des ursprünglichen
Rust-Neustart-Plans — der heißt jetzt [`rust-neustart-toolkit-mcps.md`
(„Migration nach Rust")](./rust-neustart-toolkit-mcps.md) und folgt NACH
diesem Plan.

## Ausgangslage

Die dotagent-Dashboard-App (`~/Desktop/Work/Articles/dotagent/app/dashboard`,
Commit `2949d1d`) ist eine kompakte Tauri-2-App (~1 150 LOC TS + 155 LOC
Rust): 4 Tabs (Library/Umgebung/Server/Knowledgebases), Rust-Supervisor
(`spawn_process`/`kill_process` + `proc-log`/`proc-exit`-Events,
PATH-Anreicherung für GUI-Apps) und genau EINE CLI-Bridge `run_dotagent`
(führt `dotagent … --json` aus, `DOTAGENT_BIN`-Override).

## Entscheidungen (D, 2026-07-24, per BO-Delegation)

- **D1 — CLI-Bridge bleibt vorerst:** Die App zieht mit funktionierender
  `dotagent`-CLI-Bridge um (die CLI ist auf dem BO-System installiert).
  Ersetzt wird sie erst durch die Rust-Migration (Exec-/Discovery-MCP,
  System-CLI) — nicht in diesem Plan. Kein Feature-Umbau beim Umzug.
- **D2 — Rebranding:** Produktname **„Speccify"**, Bundle-ID
  **`io.speccify.desktop`**, pnpm-Paket `speccify-desktop`, Rust-Crate
  `speccify-desktop` (lib `speccify_desktop_lib`). Tauri-Default-Icons
  bleiben bis zur Distributions-Phase (eigenes Icon dort).
- **D3 — Ein Repo, beide Workspaces:** `apps/desktop` wird pnpm-Member;
  `apps/desktop/src-tauri` wird Member des Root-Cargo-Workspace
  (gemeinsames `target/`, ein `Cargo.lock`). CI: Der schnelle `rust`-Job
  schließt das Tauri-Crate aus (Linux bräuchte webkit2gtk-Systemdeps);
  ein eigener Desktop-Job prüft Frontend-Typecheck + Vite-Build. Der
  native Tauri-Build wird lokal auf macOS verifiziert (Zielplattform).
- **D4 — Composer-Integration** (präzisiert in A1): Das Backend serviert
  die **gebaute Composer-SPA selbst unter `/ui`** (StaticFiles-Mount,
  `SPECCIFY_COMPOSER_DIST`-Override) — das Composer-Fenster lädt
  `http://127.0.0.1:<port>/ui/` und spricht die API **same-origin**
  (kein CORS, keine zweite Origin, minimale Fenster-Capabilities, kein
  doppeltes Bundling in die App). Die App wählt einen freien Port,
  spawnt `speccify-web-backend` über den Supervisor (PYTHONPATH-
  Workaround inklusive), wartet auf den Port; Fenster zu → Prozess
  stirbt. `window.__SPECCIFY_API__` existiert in der SPA zusätzlich als
  Laufzeit-Override (Zukunft: echtes Bundling/Sidecar).
- **D5 — dotagent-Referenz unangetastet:** Übernahme per Kopie (keine
  Historie/Subtree); dotagent bleibt Referenz für die Rust-Migration und
  wird erst nach deren Abschluss archiviert.

## Stufen

### A0 — App-Übernahme & Rebranding ✅ (2026-07-24)
1. [x] `app/dashboard` → `apps/desktop` kopiert (ohne node_modules/target/
   dist/gen/package-lock/`.agent`-Laufzeitreste; deren `.gitignore`s
   decken gen/schemas + `.agent/` ab).
2. [x] Rebranding (D2): tauri.conf.json (productName „Speccify",
   `io.speccify.desktop`, Fenster-Titel, beforeDev/Build auf pnpm),
   Cargo.toml (`speccify-desktop`/`speccify_desktop_lib`), package.json
   (`speccify-desktop`, +`typecheck`-Skript), App.tsx-Brand, index.html,
   README neu.
3. [x] Workspaces: pnpm-Member `apps/desktop`; `apps/desktop/src-tauri`
   im Root-Cargo-Workspace; Root-Skripte `desktop:dev/build/typecheck`.
4. [x] Verifikation: tsc + Vite-Build grün (211 kB), `cargo build
   -p speccify-desktop` grün, `cargo fmt` + `clippy -p speccify-desktop`
   clean, `tauri build` (Release-Bundle) grün. **Offen: manueller
   BO-Check `pnpm run desktop:dev`.**
5. [x] CI: Job `apps/desktop frontend (typecheck + build)`; `rust`-Job
   mit `--exclude speccify-desktop` (Linux-webkit2gtk vermeiden).

### A1 — Composer-Fenster (D4) ✅ (2026-07-24)
1. [x] Backend serviert die Composer-SPA unter `/ui` (Settings-Feld
   `composer_dist` + `SPECCIFY_COMPOSER_DIST`, StaticFiles `html=True`,
   fehlt der Build → kein Mount, API unverändert). 2 neue Tests
   (`test_composer_ui_mount.py`). SPA: `window.__SPECCIFY_API__`-
   Laufzeit-Override in `api.ts` (same-origin bleibt der Default).
2. [x] Rust-Command `open_composer(repo)`: `~`-Expansion, Vorprüfungen
   (venv-Binary + gebautes dist mit klaren Fehlermeldungen), freier
   Port, Spawn `.venv/bin/speccify-web-backend` (cwd=Repo, PATH-
   Anreicherung, PYTHONPATH-Workaround), Logs via Supervisor
   (`proc-log`, id `composer-backend-<port>`), Port-Wait (20 s, sonst
   Kill + Fehler), Fenster `composer-<port>` auf `…/ui/`;
   `WindowEvent::Destroyed` → Kill + `proc-exit`.
3. [x] „Composer"-Tab (Default-Tab) mit Repo-Pfad-Feld (localStorage,
   Default `~/Desktop/Work/speccify`) und „Composer-Fenster öffnen".
4. [x] Capability-Scope: Composer-Fenster lädt Remote-URL — kein
   IPC-/Supervisor-Zugriff aus dem WebView (Tauri-Default für External).
5. [x] Verifikation: 422 Pytest grün (inkl. 2 neuer /ui-Mount-Tests),
   ruff clean, Composer-Playwright 3/3 grün (api.ts-Änderung), tsc+Vite
   beide Apps grün, `cargo build/clippy -p speccify-desktop` grün,
   `/ui`-Livecheck (curl 200 + health) grün, `tauri build` grün
   (Speccify.app + .dmg). **Offen: manueller BO-Check des Fensters
   (`pnpm run desktop:dev` → Tab Composer).**

### A2 — Feinschliff nach BO-Rumprobieren
Kandidaten (erst nach Feedback schneiden): Projekt-Liste im
Composer-Einstieg aus `~/.speccify/projects.json` vs. Datei-Dialog;
Server-Tab um speccify-web-backend-Instanzen erweitern; Menü/Shortcuts.

## Verifikations-/Umschalt-Regeln

- Kein Umbau der dotagent-Wire-Kontrakte in diesem Plan; die
  Kontrakt-Testsuite (`scripts/exec_mcp_contract.py`) gehört zur
  Rust-Migration.
- `.agent/`-Laufzeitdateien der App (exec-pending etc.) niemals
  einchecken.
