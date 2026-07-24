# Speccify Desktop (Tauri 2)

Desktop-App über der `dotagent`-CLI — übernommen aus dotagent
`app/dashboard` (Commit `2949d1d`) per BO-Entscheidung 2026-07-24;
Plan: [`.agent/plans/desktop-app-und-composer.md`](../../.agent/plans/desktop-app-und-composer.md).
Die CLI-Bridge zeigt bis zur Rust-Migration
([`rust-neustart-toolkit-mcps.md`](../../.agent/plans/rust-neustart-toolkit-mcps.md))
weiter auf die installierte dotagent-CLI.

## Architektur

*   **CLI-Bridge:** Alle Daten kommen über den Tauri-Command `run_dotagent(args)`,
    der `dotagent … --json` als Subprocess aufruft (`src-tauri/src/lib.rs`).
    CLI-Discovery: `DOTAGENT_BIN`-Env-Var → angereicherter `PATH`
    (Homebrew, `~/.local/bin`, `~/.cargo/bin`).
*   **Prozess-Supervisor:** `spawn_process`/`kill_process` starten Prozesse
    Rust-seitig, streamen stdout/stderr zeilenweise als `proc-log`-Events in
    die UI und killen alle Kinder beim App-Quit (Drop des Supervisor-State).
    Wird in Stufe A1 auch die `speccify-web-backend`-Instanzen der
    Composer-Fenster verwalten.
*   **Views:** Bibliothek (`registry list --json` mit Tag-Filter), Umgebung
    (`doctor --json` + Python-Verwaltung), Server (`mcp list/start/stop/logs`
    + Supervisor-Panel), Knowledgebases (`kb kbs --json`).

## Entwicklung

```bash
pnpm install                      # im Repo-Root (Workspace)
pnpm run desktop:dev              # tauri dev (Frontend :1420)

# Mit einer bestimmten dotagent-CLI statt der aus dem PATH:
DOTAGENT_BIN=~/Desktop/Work/Articles/dotagent/.venv/bin/dotagent pnpm run desktop:dev
```

Rust-Seite: `apps/desktop/src-tauri` ist Member des Root-Cargo-Workspace
(`cargo build -p speccify-desktop`); der CI-`rust`-Job schließt das Crate
aus (Linux bräuchte webkit2gtk), gebaut wird nativ auf macOS.

## Build

```bash
pnpm run desktop:build     # .app/.dmg unter target/release/bundle/
```
