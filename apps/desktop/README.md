# Speccify Desktop (Tauri 2)

Desktop-Cockpit für Speccify: Composer-Fenster, Toolbox, MCP-Server,
Agent-Terminal, ask_bo. Ursprünglich aus dotagent `app/dashboard`
übernommen (Commit `2949d1d`) — **seit R3 komplett ohne dotagent**:
alle Daten kommen aus nativen Rust-Commands bzw. den Speccify-MCPs.
Pläne: [`desktop-app-und-composer.md`](../../.agent/plans/desktop-app-und-composer.md),
[`toolkit-discovery-terminal.md`](../../.agent/plans/toolkit-discovery-terminal.md);
Überblick: [`docs/toolkit.md`](../../docs/toolkit.md).

## Architektur

*   **Native Commands** (`src-tauri/src/`): `toolbox_cmd` (Manifeste,
    Scaffold, MCP-Status), `system_cmd` (Doctor, Python via uv,
    Knowledgebases), `settings` (Working Dir, Einweisungs-Dateien),
    `terminal` (PTY), `desktop_ui` (ask_bo-MCP :8768).
*   **Prozess-Supervisor:** `spawn_process`/`kill_process` starten Prozesse
    Rust-seitig (MCP-Server im Server-Tab, `speccify-web-backend` je
    Composer-Fenster), streamen Logs als `proc-log`-Events und killen alle
    Kinder beim App-Quit.
*   **Views:** Composer (Fenster öffnen), Bibliothek (Toolbox), Server
    (MCPs Start/Stop + Client-Config), Umgebung (Doctor + Python),
    Knowledgebases, Settings; rechte Sidebar: ask_bo-Fragen + Terminal.

## Entwicklung

```bash
pnpm install                      # im Repo-Root (Workspace)
pnpm run desktop:dev              # tauri dev (Frontend :1420)
```

Rust-Seite: `apps/desktop/src-tauri` ist Member des Root-Cargo-Workspace
(`cargo build -p speccify-desktop`); der CI-`rust`-Job schließt das Crate
aus (Linux bräuchte webkit2gtk), gebaut wird nativ auf macOS.

## Build

```bash
pnpm run desktop:build     # .app/.dmg unter target/release/bundle/
```
