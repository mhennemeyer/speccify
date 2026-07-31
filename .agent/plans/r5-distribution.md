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

### R5.2 — Engine-Bootstrap (uv) ✅ (2026-07-29) — der Knackpunkt
1.  [x] `scripts/build_engine_payload.sh`: Wheels der vier Python-Pakete
    (`uv build --wheel`) + `uv export` (gehashte Pins aus `uv.lock`) +
    Composer-SPA + `registry-fixtures/` + `llm-cache/` nach
    `apps/desktop/src-tauri/resources/` (gitignored, 612 KB); `payload.json`
    trägt Hash, Python-Version und Wheel-Liste.
2.  [x] `tauri.conf.json`: `bundle.resources = ["resources/**/*"]` →
    `Contents/Resources/resources/…`.
3.  [x] `engine.rs`: `engine_status` (ready/needs_update/payload_found/
    uv_source) und `engine_install` (`uv venv` + `uv pip install -r` +
    Wheels `--no-deps`, Live-Log als `proc-log`); Marker `installed.json`
    mit Payload-Hash ⇒ Re-Install nach App-Update.
4.  [x] `open_composer` mit zwei Quellen: `repo_launch` (D3, Repo mit
    `.venv` + Composer-Build) > `engine_launch` (venv + Resources via
    `SPECCIFY_COMPOSER_DIST`/`_REGISTRY_PATH`/`_CACHE_DIR`/`_PROJECT_ROOT`);
    Fenstertitel nennt die Quelle. Repo-Feld ist jetzt optional.
5.  [x] `mcp_status` löst `[run]`-Blöcke auf: Engine-venv (auch
    `uv run <bin>` → `<venv>/bin/<bin>`) > Sidecar > PATH; Client-Config
    und Supervisor-Start nutzen den aufgelösten absoluten Pfad.
6.  [x] Umgebungs-Tab: Engine-Karte mit Status, Installation und Live-Log.
7.  [ ] **Offen:** `uv` als vierter Sidecar mitliefern (heute PATH/brew).
    Bis dahin braucht die verteilte App einmalig ein installiertes `uv` —
    der Doctor sagt das, die Engine-Karte auch.

**Verifiziert:** Bootstrap-Kommandos 1:1 außerhalb des Repos durchgespielt
(venv aus dem Payload, `speccify-web-backend` gegen die Resources:
`/api/v1/health` 200, `/ui/` 200, `/api/v1/specs` liefert die Fixtures);
`.app` enthält Payload + Sidecars (17 MB App, 5,7 MB dmg) und startet
(desktop-ui-MCP :8768 antwortet). Der Klick auf „Engine installieren"
in der laufenden App ist BO-Dogfooding-Stoff.

### R5.3 — Signing + Notarisierung ⏸ vorbereitet (2026-07-31)
1.  [x] `tauri.conf.json` → `bundle.macOS`: `hardenedRuntime: true`,
    `minimumSystemVersion: "10.15"` (Tauri-2-Minimum; Default wäre 10.13).
    **Keine** `signingIdentity` in der Config — sie kommt aus
    `APPLE_SIGNING_IDENTITY`, sonst wäre kein Dev-Build ohne Zertifikat
    mehr möglich. **Keine Entitlements**: für Developer-ID-Distribution
    ohne Sandbox braucht es keine; die Engine-venv läuft als eigener
    Prozess, nicht als Code in unserem Adressraum.
2.  [x] `scripts/release_macos.sh`: Preflight (Werkzeuge, Identity wirklich
    im Keychain, Credentials — bricht **vor** dem Compile ab) → Sidecars +
    Payload → `tauri build` (signiert, notarisiert und stapelt selbst) →
    Verifikation: `codesign --verify --deep --strict`, Authority/Team,
    **jedes Sidecar einzeln** auf Signatur + Hardened Runtime, `spctl`,
    `stapler validate` für .app und .dmg. Flags: `--no-notarize`,
    `--verify-only`.
3.  [x] [`docs/release.md`](../../docs/release.md): Zertifikat und
    App-Specific Password einrichten, Env-Variablen (mit dem Hinweis,
    dass nichts davon ins Repo gehört), Verifikations-Kommandos,
    Quarantäne-Test auf einem fremden Mac, Fehlerbild-Tabelle,
    `notarytool log`-Abruf.
4.  [ ] **BO-Aktion, blockiert R5.3-Abschluss:** Developer-ID-Zertifikat
    (Apple Developer Program, 99 $/Jahr) in den Keychain + App-Specific
    Password erzeugen, dann `./scripts/release_macos.sh` laufen lassen.
    Erst dieser Lauf zeigt, ob Signatur/Notarisierung wirklich durchgehen.

**Verifiziert (soweit ohne Zertifikat möglich):** Preflight bricht mit
klarer Liste ab, wenn Credentials fehlen (Exit 1, nichts gebaut);
`--verify-only` diagnostiziert das aktuelle unsignierte Bundle korrekt
(kein TeamIdentifier, Sidecars ohne Hardened Runtime, Gatekeeper lehnt ab,
kein Ticket); `tauri build` mit der neuen macOS-Config läuft durch,
`LSMinimumSystemVersion` steht auf 10.15.

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

## Folgen von R5.2 (bewusst so entschieden)

*   Steht die Engine, gewinnt sie für `speccify-mcp` auch dann, wenn ein
    Repo vorhanden ist — `uv run speccify-mcp` funktioniert nur mit dem
    Repo als CWD, die Engine dagegen aus jedem Working Dir. Der Server-Tab
    zeigt die Quelle, ein eigenes Toolbox-Manifest mit absolutem Pfad
    überstimmt sie.
*   Das Composer-Repo-Feld ist neu leer vorbelegt; bestehende Eingaben
    bleiben in `localStorage` erhalten.

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
