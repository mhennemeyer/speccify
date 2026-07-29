---
isActive: true
---

# Plan: R5 — Distribution ohne Store (Speccify.app zum Herunterladen)

**Angelegt 2026-07-29.** Feinplan zur letzten offenen Stufe von
[`rust-neustart-toolkit-mcps.md`](./rust-neustart-toolkit-mcps.md) (R5).
R0–R3 sind geliefert, der Toolkit-Plan T0–T8 ist abgeschlossen — was fehlt,
ist der Weg von „läuft auf meinem Rechner aus dem Repo" zu „jemand lädt
Speccify.app herunter, zieht sie in /Programme und sie funktioniert".

## Ausgangslage (Stand `731ef85`)

Die App ist heute **repo-gebunden**:

| Abhängigkeit | Heute | Problem für die Distribution |
|---|---|---|
| Rust-MCPs (exec/discovery/parallels) | `cargo install --path crates/…` → `~/.cargo/bin`, gefunden über den angereicherten PATH (`lib.rs:augmented_path`) | Nutzer hat keine Rust-Toolchain |
| Composer-Backend | `<repo>/.venv/bin/speccify-web-backend` + `PYTHONPATH` auf vier `src/`-Verzeichnisse (`lib.rs:open_composer`) | Nutzer hat kein Repo, kein `uv sync` |
| Composer-SPA | `<repo>/apps/composer/dist/index.html` | dito |
| speccify-mcp (Python, stdio) | Toolbox-Manifest startet `uv run speccify-mcp` im Repo | dito |
| Signatur | ad-hoc (unsigniert) | Gatekeeper blockt den Download |
| Update | keins | jede Version manuell |

Der desktop-ui-MCP (:8768) läuft im App-Prozess und ist damit schon
distributions-fertig.

## Entscheidungen

*   **D1 — Rust-MCPs als Tauri-Sidecars.** Die drei Binaries werden als
    `bundle.externalBin` ins `.app` gelegt (macOS: `Contents/MacOS/`) und
    **vor** dem PATH aufgelöst: gebündelt > PATH > nicht gefunden. Damit
    verschwindet `cargo install` aus dem Nutzer-Setup; Entwickler-Betrieb
    (`tauri dev`) fällt weiter auf den PATH zurück.
*   **D2 — Python-Engine per uv-Bootstrap statt Repo.** Gebündelt werden
    `uv` (Sidecar), die eigenen Wheels (`speccify-core/-cli/-mcp/-web-backend`)
    und ein gepinntes `requirements.lock`; beim ersten Start entsteht daraus
    eine verwaltete venv unter
    `~/Library/Application Support/io.speccify.desktop/engine/`.
    Erstinstallation braucht **einmal Netz** (CPython + Third-Party-Wheels
    von PyPI), danach läuft alles offline. *Verworfen:* PyInstaller-Onefile
    (eigene Build-Toolchain, Signatur/Notarisierung jedes eingebetteten
    Binaries, schlechte Fehlerdiagnose) und „Repo bleibt Pflicht"
    (widerspricht dem Ziel).
*   **D3 — Repo-Modus bleibt erhalten.** Ist im Settings-Tab ein Working
    Dir mit Repo gesetzt, gewinnt weiterhin das Repo (Dogfooding: BO
    arbeitet am Quellstand). Die gebündelte Engine ist der Fallback.
*   **D4 — Signing/Notarisierung/Updater werden vorbereitet, nicht
    ausgeführt.** Konfiguration, Skripte und Doku entstehen hier; der
    tatsächliche Lauf braucht BO-Credentials (Apple Developer ID,
    App-Specific Password/API-Key, Updater-Keypair) und wird als
    BO-Aktionsliste dokumentiert. Keine Secrets ins Repo.
*   **D5 — Kein App Store, kein Sandboxing** (BO-Entscheidung aus dem
    Rust-Plan, Punkt 6): Exec-MCP + Prozess-Supervisor brauchen
    unsandboxed Zugriff.

## Stufen

### R5.1 — Rust-MCPs als Sidecars ✅ (2026-07-29)
1.  [x] `scripts/build_sidecars.sh`: baut die drei Crates in `--release`
    und legt sie als `apps/desktop/src-tauri/binaries/<name>-<triple>` ab
    (Triple aus `rustc -vV`); `binaries/` ist gitignored.
2.  [x] `tauri.conf.json`: `bundle.externalBin` mit den drei Binaries;
    `desktop:build`/`desktop:dev` rufen das Skript vorher auf.
3.  [x] `sidecar.rs`: Auflösung neben dem App-Binary (`current_exe`),
    genutzt von `spawn_process` (Start) und `mcp_status` (`binary_found`
    + neues Feld `binary_source`), Server-Tab zeigt die Quelle an.
4.  [x] Tests: reine Auflösungsfunktion gegen ein temporäres Verzeichnis
    (gebündelt gewinnt, Fallback PATH, absoluter Pfad unverändert).

### R5.2 — Engine-Bootstrap (uv) — der Knackpunkt
1.  `uv` als vierter Sidecar (Version gepinnt, Download-Skript mit
    SHA256-Prüfung, ebenfalls gitignored).
2.  `scripts/build_engine_payload.sh`: `uv build` für die vier
    Python-Pakete + `uv export` als `requirements.lock` → Resource-Ordner
    `apps/desktop/src-tauri/resources/engine/`.
3.  `engine.rs`: `engine_status` (venv vorhanden? Version?),
    `engine_install` (uv venv + `uv pip install`, Logs als `proc-log`),
    `engine_python_bin()`; Marker-Datei mit Payload-Hash → Re-Install bei
    App-Update.
4.  `open_composer` umgestellt: Repo-Modus (D3) > gebündelte Engine;
    Composer-SPA als Bundle-Resource, Pfad per Env an das Backend.
5.  Toolbox-Manifest `speccify-mcp` zeigt auf die gebündelte Engine statt
    auf `uv run` im Repo.
6.  Settings-/Doctor-Tab: Engine-Status + „Engine installieren"-Aktion.

### R5.3 — Signing + Notarisierung
1.  `tauri.conf.json` → `bundle.macOS` (Signing-Identity via Env,
    Hardened Runtime, Entitlements für unsandboxed Exec).
2.  `scripts/release_macos.sh`: build → codesign (inkl. Sidecars) →
    `notarytool submit --wait` → `stapler staple` → dmg.
3.  `docs/release.md`: welche Credentials wo hinterlegt werden
    (Keychain-Profil statt Repo-Secrets), Prüf-Kommandos (`spctl -a -vvv`).
4.  BO-Aktionsliste: Developer-ID-Zertifikat, App-Specific Password.

### R5.4 — Updater
1.  `tauri-plugin-updater` + `bundle.createUpdaterArtifacts`; Public Key
    in die Config, Private Key bleibt beim BO.
2.  `latest.json`-Vertrag + Ablage auf speccify.io; Update-Prüfung in der
    App (Hinweis statt Zwang).

### R5.5 — Wrap-up
1.  Download-Seite in `apps/marketing` (speccify.io) mit dmg-Link.
2.  dotagent archivieren (README-Verweis „Referenz für die
    Rust-Portierung"), Restore-Doku/Memories umziehen.
3.  Rust-Plan `rust-neustart-toolkit-mcps.md` schließen.

## Risiken

*   **Sidecar-Signatur:** eingebettete Binaries müssen mit signiert werden,
    sonst schlägt die Notarisierung fehl — `codesign` pro Datei in R5.3.
*   **Erstinstallation ohne Netz** schlägt fehl → klare Fehlermeldung mit
    Retry statt stiller Hänger (R5.2).
*   **Zwei Engine-Quellen** (Repo vs. Bundle) können auseinanderlaufen →
    Repo-Modus nur bei explizit gesetztem Working Dir, Quelle in der UI
    sichtbar machen.
*   **App-Größe:** uv (~35 MB) + Wheels; Sidecars nur für das Host-Triple
    bauen (kein Universal-Binary, bis der BO Intel-Support braucht).
