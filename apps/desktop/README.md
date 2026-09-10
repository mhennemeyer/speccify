# Speccify Desktop (Tauri 2)

Desktop-Cockpit für Speccify: Projektfenster, Skill-/Tool-Bestände,
dateibasiertes Board, MCP-Server, Agent-Terminal und ask_bo. Ursprünglich aus dotagent `app/dashboard`
übernommen (Commit `2949d1d`) — **seit R3 komplett ohne dotagent**:
alle Daten kommen aus nativen Rust-Commands bzw. den Speccify-MCPs.
Pläne: [`desktop-app-und-composer.md`](../../.agent/plans/archive/desktop-app-und-composer.md),
[`toolkit-discovery-terminal.md`](../../.agent/plans/archive/toolkit-discovery-terminal.md);
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
*   **Views:** Projekte (jeweils Board/Pläne/Skills/Tools/MCPs/Agent),
    Bibliothek (Toolbox), Server (MCPs Start/Stop + Client-Config), Umgebung
    (Doctor + Python), Knowledgebases und Settings; Terminal für Claude,
    Codex oder ein freies Kommando.

## Entwicklung

Ein Kommando für alles (idempotent — fertige Schritte werden übersprungen):

```bash
./scripts/dev.sh                  # Deps + Sidecars + Engine-Payload, dann tauri dev
./scripts/dev.sh --release        # stattdessen .app/.dmg bauen und öffnen
./scripts/dev.sh --no-start       # nur vorbereiten
./scripts/dev.sh --check          # Voraussetzungen prüfen, nichts installieren
./scripts/dev.sh --help           # alle Optionen
```

### App während der Entwicklung benutzen (macOS)

Für laufende Nutzung und Abnahme ist eine gebündelte lokale App sinnvoll:
Sie enthält das Frontend und läuft ohne Vite und ohne Rust-Watcher.

```bash
./scripts/dev.sh --status                         # nur Listener/Build anzeigen
./scripts/dev.sh --app --ui-port=18768             # vorbereiten, lokal bauen, öffnen
./scripts/dev.sh --app --prepared --ui-port=18768  # bekannte vorbereitete Umgebung nutzen
./scripts/dev.sh --open --ui-port=18768            # vorhandenen Build öffnen/aktivieren
```

`--prepared` prüft nur das Vorhandensein, nicht die Aktualität der Deps,
Sidecars und Engine. Nach Änderungen daran zunächst `--no-start` ohne
`--prepared` ausführen. Der lokale Build liegt in
`target/debug/bundle/macos/Speccify.app`, ist nicht für Weitergabe signiert
und ersetzt keine installierte Release-App. Keine Veröffentlichung wird ausgelöst.

Die App offen lassen, während Quellen geändert und Tests ausgeführt werden.
Zum Übernehmen eines neuen Standes bewusst Arbeit sichern, mit ⌘Q beenden,
`--app --prepared` erneut ausführen und abnehmen. Ein Neubau der bereits
laufenden lokalen Bundle-Datei wird verweigert. Es gibt weiterhin nur eine
App-Instanz dieser Identität: Alltags-App und Dev-Watcher nicht parallel verwenden.

Am 2026-09-10 hält Lima eine Weiterleitung auf Port 8768. Ein belegter Port
beweist keine laufende native App; das Script zeigt den Listener und beendet
keinen Prozess. Port 18768 ist hier die ausdrückliche lokale Alternative.
Unter **Umgebung → Fragen-MCP dieser App** steht der konfigurierte Endpoint.
Bei Start durch Finder ohne Argument bleibt der Standard 8768; deshalb hier
den dokumentierten `--open --ui-port=18768`-Weg verwenden.

Neue Einweisungsdateien enthalten den gewählten Port; bestehende `.mcp.json`
und `.codex/config.toml` werden nicht automatisch verändert. Nur den Eintrag
`speccify-desktop-ui` bei Bedarf auf den angezeigten Endpoint umstellen.
Andere MCP-Ports und die Lima-VM bleiben unberührt. `--open` aktiviert eine
laufende App ohne ihren Port oder ihre Sitzung zu ändern.

Einzelschritte von Hand:

```bash
pnpm install --frozen-lockfile     # im Repo-Root (Workspace)
pnpm run desktop:dev              # tauri dev (Frontend :1420)
```

Rust-Seite: `apps/desktop/src-tauri` ist Member des Root-Cargo-Workspace
(`cargo build -p speccify-desktop`); der CI-`rust`-Job schließt das Crate
aus (Linux bräuchte webkit2gtk), gebaut wird nativ auf macOS.

Versionen werden im Repository festgelegt: Node mindestens `engines.node`
aus `package.json` (CI verwendet `.nvmrc`), pnpm exakt aus `packageManager`,
Python aus `.python-version` und Rust aus `rust-toolchain.toml`. `uv` muss
installiert sein; es richtet die benötigte Python-Version bei Bedarf ein.
Auf macOS sind außerdem die Xcode Command Line Tools erforderlich.
`dev.sh` prüft diese Voraussetzungen und verwendet beide Lockfiles unverändert.

Die Installationsskripte von `esbuild` und `sharp` sind in
`pnpm-workspace.yaml` ausdrücklich freigegeben. Weitere Pakete mit
Installationsskripten führen zu einer Meldung und müssen einzeln geprüft
werden; eine pauschale Freigabe ist nicht nötig. Das entspricht den
[pnpm-Einstellungen für Buildfreigaben](https://pnpm.io/10.x/settings#onlybuiltdependencies).

## Startumgebung des Agent-Terminals

Im Agent-Tab und vor dem Terminalstart zeigt **Startumgebung prüfen** die
Login-Shell, das aufgelöste Agent-Binary mit Versionsausgabe sowie die verwendete
Speccify-CLI. Beim Start wird dieselbe Prüfung erneut durchgeführt. Eine
fehlende oder nicht startbare bekannte Agent-CLI verhindert den Autostart
mit einer konkreten Fehlermeldung. Login und erfolgreiche Wiederaufnahme
einer Unterhaltung sind damit noch nicht geprüft.

Die Reihenfolge für Speccify ist: `.venv` des geöffneten Projekts, sofern sie
Speccify enthält; anschließend die zum App-Payload passende installierte
Engine; zuletzt die Installation im Shell-PATH. Die gewählte Runtime wird
nach den Shell-Profilen vor den PATH gesetzt. Im geöffneten Terminal lassen
sich die tatsächlich beim Start verwendeten Werte unter **Startumgebung**
nachlesen. Änderungen an Profilen nach dem Start erfordern eine neue Prüfung.
Die CLI-Hilfe muss `expand`, `export`, `link` und `tool` enthalten; fehlende
Befehle erscheinen als Hinweis und verhindern gewöhnliche Codearbeit nicht.

Die Diagnose unterstützt zsh, bash, sh und PowerShell. Freie Shell-Kommandos
werden bei der Diagnose nicht ausgeführt und beim Start unverändert übernommen.
Der Modus **Nur Shell** bleibt auch bei einer fehlgeschlagenen Diagnose
verfügbar. Es werden keine globalen Profile, Anmeldungen oder MCP-Dateien
geändert. MCP-Verfügbarkeit wird nicht aus einem CLI-Pfad abgeleitet.

Für signierte, notarisierte Releases: [`docs/release.md`](../../docs/release.md)
(`./scripts/release_macos.sh`).

## Build

```bash
pnpm run desktop:build     # .app/.dmg unter target/release/bundle/
```

Für eine App, die **ohne Repo** funktioniert, vorher einmal den
Engine-Payload bauen (Wheels + gepinnte Requirements + Composer-SPA +
Fixtures → `src-tauri/resources/`, ebenfalls gitignored):

```bash
./scripts/build_engine_payload.sh
```

Beim ersten Start baut die App daraus per `uv` eine venv unter
`~/Library/Application Support/io.speccify.desktop/engine/venv`
(Umgebungs-Tab → „Engine installieren"; braucht einmal Netz). Der Composer
läuft dann gegen diese Engine; ein im Composer-Tab angegebenes Repo mit
`.venv` gewinnt weiterhin.

Beide Build-Kommandos rufen vorher `scripts/build_sidecars.sh` auf: die drei
MCP-Binaries (`speccify-exec-mcp`, `speccify-discovery-mcp`,
`speccify-parallels-mcp`) und das per `scripts/fetch_uv.sh` geladene `uv`
werden nach
`src-tauri/binaries/<name>-<target-triple>` gelegt und von Tauri als
`externalBin` ins Bundle übernommen (macOS: `Contents/MacOS/`). Zur
Laufzeit gilt **mitgeliefert > PATH** (`src-tauri/src/sidecar.rs`); im
`tauri dev`-Betrieb liegen keine Sidecars neben dem Debug-Binary, dort
greift der PATH-Fallback. `binaries/` ist gitignored.

## Windows

Einmalig die Toolchain installieren (jeweils `winget install …`):
`Rustlang.Rustup`, `OpenJS.NodeJS.LTS`, `LLVM.LLVM` (clang ist Pflicht für
`ring`), `astral-sh.uv`, `Microsoft.VisualStudio.2022.BuildTools` **mit** der
C++-Workload — die nackte winget-Installation lässt `link.exe` weg:

```powershell
winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```
 — dann
`corepack enable` für pnpm. Danach reicht:

```powershell
git clone https://github.com/mhennemeyer/speccify && cd speccify
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

Das Skript prüft die Werkzeuge, baut die MCP-Sidecars mit Triple-Suffix,
füllt `resources/` mit den Referenz-Skills und startet `tauri dev`.
