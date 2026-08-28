use std::{
    collections::HashMap,
    io::{BufRead, BufReader},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, State};

mod desktop_ui;
mod engine;
mod project_cmd;
mod settings;
mod sidecar;
mod system_cmd;
mod terminal;
mod toolbox_cmd;

/// Laufende Kind-Prozesse des Spike-Supervisors. Drop killt alle Kinder,
/// damit beim App-Quit nichts weiterläuft.
struct Supervisor(Mutex<HashMap<String, Child>>);

impl Drop for Supervisor {
    fn drop(&mut self) {
        if let Ok(mut children) = self.0.lock() {
            for child in children.values_mut() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

#[derive(Clone, Serialize)]
pub(crate) struct LogEvent {
    pub(crate) id: String,
    pub(crate) line: String,
}

#[derive(Clone, Serialize)]
struct ExitEvent {
    id: String,
}

/// PATH um Standard-Install-Orte erweitern. GUI-Apps erben auf macOS nur
/// den Minimal-PATH (/usr/bin:/bin:…) — ohne Anreicherung sehen die
/// CLI-Subprozesse weder Homebrew noch pipx.
pub(crate) fn augmented_path() -> std::ffi::OsString {
    let home = std::env::var("HOME").unwrap_or_default();
    let extras = [
        "/opt/homebrew/bin".to_string(),
        "/opt/homebrew/opt/rustup/bin".to_string(),
        "/usr/local/bin".to_string(),
        format!("{home}/.local/bin"),
        format!("{home}/.cargo/bin"),
    ];
    let current = std::env::var_os("PATH").unwrap_or_default();
    let mut dirs: Vec<PathBuf> = std::env::split_paths(&current).collect();
    for extra in extras {
        let dir = PathBuf::from(extra);
        if !dirs.contains(&dir) {
            dirs.push(dir);
        }
    }
    std::env::join_paths(dirs).unwrap_or(current)
}

fn stream_reader(app: AppHandle, id: String, reader: impl BufRead + Send + 'static) {
    std::thread::spawn(move || {
        for line in reader.lines().map_while(Result::ok) {
            let _ = app.emit(
                "proc-log",
                LogEvent {
                    id: id.clone(),
                    line,
                },
            );
        }
    });
}

/// Spike P0.1: Prozess starten, stdout/stderr zeilenweise als `proc-log`-Events
/// in die UI streamen; `kill_process` beendet ihn wieder.
#[tauri::command]
fn spawn_process(
    app: AppHandle,
    state: State<Supervisor>,
    id: String,
    command: String,
    args: Vec<String>,
) -> Result<u32, String> {
    // Gebündelte Sidecars gewinnen über den PATH (R5.1/D1) — in der
    // verteilten App gibt es kein `cargo install`.
    let binary = sidecar::command_for_spawn(&command);
    let mut child = Command::new(&binary)
        .args(&args)
        .env("PATH", augmented_path())
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("{command}: {e}"))?;
    let pid = child.id();

    if let Some(stdout) = child.stdout.take() {
        stream_reader(app.clone(), id.clone(), BufReader::new(stdout));
    }
    if let Some(stderr) = child.stderr.take() {
        stream_reader(app.clone(), id.clone(), BufReader::new(stderr));
    }
    state.0.lock().unwrap().insert(id, child);
    Ok(pid)
}

#[tauri::command]
fn kill_process(app: AppHandle, state: State<Supervisor>, id: String) -> Result<bool, String> {
    match state.0.lock().unwrap().remove(&id) {
        Some(mut child) => {
            child.kill().map_err(|e| e.to_string())?;
            let _ = child.wait();
            let _ = app.emit("proc-exit", ExitEvent { id });
            Ok(true)
        }
        None => Ok(false),
    }
}

// --- Composer-Fenster (Plan desktop-app-und-composer.md, A1) ----------------

/// `~`-Expansion für Pfade aus der UI.
fn expand_home(raw: &str) -> PathBuf {
    if let Some(rest) = raw.strip_prefix("~/") {
        if let Ok(home) = std::env::var("HOME") {
            return PathBuf::from(home).join(rest);
        }
    }
    PathBuf::from(raw)
}

/// Freien localhost-Port vom OS holen (bind auf Port 0, wieder freigeben).
fn free_port() -> Result<u16, String> {
    let listener =
        std::net::TcpListener::bind(("127.0.0.1", 0)).map_err(|e| format!("Port-Suche: {e}"))?;
    listener
        .local_addr()
        .map(|addr| addr.port())
        .map_err(|e| format!("Port-Suche: {e}"))
}

/// Wartet, bis der Backend-Port annimmt (Health-Gate fürs Fenster).
fn wait_for_port(port: u16, timeout: std::time::Duration) -> bool {
    let deadline = std::time::Instant::now() + timeout;
    let addr = std::net::SocketAddr::from(([127, 0, 0, 1], port));
    while std::time::Instant::now() < deadline {
        if std::net::TcpStream::connect_timeout(&addr, std::time::Duration::from_millis(300))
            .is_ok()
        {
            return true;
        }
        std::thread::sleep(std::time::Duration::from_millis(200));
    }
    false
}

/// Start-Rezept fürs Composer-Backend: Binary + Arbeitsverzeichnis + Env.
/// Zwei Quellen (Plan r5-distribution.md, D3): ein angegebenes Repo mit
/// `.venv` gewinnt (Quellstand, Dogfooding), sonst die mitgelieferte Engine.
struct BackendLaunch {
    binary: PathBuf,
    cwd: PathBuf,
    env: Vec<(String, String)>,
    source: &'static str,
}

fn repo_launch(repo: &std::path::Path) -> Option<BackendLaunch> {
    let binary = repo.join(".venv/bin/speccify-web-backend");
    if !binary.is_file() || !repo.join("apps/composer/dist/index.html").is_file() {
        return None;
    }
    // macOS-Quarantäne versteckt venv-.pth-Dateien wiederkehrend; PYTHONPATH
    // auf die src/-Verzeichnisse umgeht das (gleicher Workaround wie CLI/CI).
    let pythonpath = ["core/src", "cli/src", "mcp/src", "apps/web/backend/src"]
        .iter()
        .map(|p| repo.join(p).to_string_lossy().into_owned())
        .collect::<Vec<_>>()
        .join(":");
    Some(BackendLaunch {
        binary,
        cwd: repo.to_path_buf(),
        env: vec![("PYTHONPATH".into(), pythonpath)],
        source: "Repo",
    })
}

/// Gebündelte Engine: Backend aus der Engine-venv, Specs/Cache/SPA aus den
/// App-Resources (das Backend liest genau diese vier Env-Variablen).
fn engine_launch(app: &AppHandle) -> Result<BackendLaunch, String> {
    let status = engine::engine_status(app.clone())?;
    if !status.ready {
        return Err(if status.needs_update {
            "Die mitgelieferte Engine stammt aus einer älteren App-Version — im Umgebungs-Tab neu installieren.".into()
        } else {
            "Keine Python-Engine installiert — im Umgebungs-Tab „Engine installieren“ (oder oben ein Speccify-Repo mit .venv angeben).".to_string()
        });
    }
    let resources = engine::resources_dir(app).ok_or("Kein Engine-Payload im App-Bundle.")?;
    let binary = engine::venv_bin(app, "speccify-web-backend")?;
    if !binary.is_file() {
        return Err(format!(
            "{} fehlt — Engine neu installieren.",
            binary.display()
        ));
    }
    let project_root = settings::get_settings()
        .ok()
        .and_then(|s| s.working_dir)
        .and_then(|raw| settings::resolve_working_dir(&raw).ok())
        .unwrap_or_else(|| expand_home("~"));
    Ok(BackendLaunch {
        env: vec![
            (
                "SPECCIFY_COMPOSER_DIST".into(),
                resources.join("composer").display().to_string(),
            ),
            (
                "SPECCIFY_LIBRARY_PATH".into(),
                resources.join("skills").display().to_string(),
            ),
            (
                "SPECCIFY_PROJECT_ROOT".into(),
                project_root.display().to_string(),
            ),
        ],
        cwd: project_root,
        binary,
        source: "mitgelieferte Engine",
    })
}

/// Öffnet ein Composer-Fenster: spawnt ein eigenes `speccify-web-backend` auf
/// einem freien Port (Supervisor-verwaltet, Logs als `proc-log`), wartet auf
/// den Port und lädt `http://127.0.0.1:<port>/ui/` (Backend serviert die
/// gebaute Composer-SPA same-origin). Fenster zu → Backend-Prozess stirbt.
///
/// `repo` darf leer sein — dann läuft der Composer gegen die mitgelieferte
/// Engine (verteilte App ohne Repo).
#[tauri::command]
fn open_composer(app: AppHandle, state: State<Supervisor>, repo: String) -> Result<String, String> {
    let trimmed = repo.trim();
    let launch = match (!trimmed.is_empty()).then(|| expand_home(trimmed)) {
        Some(repo) => match repo_launch(&repo) {
            Some(launch) => launch,
            // Repo angegeben, aber unbrauchbar: Engine-Fallback versuchen und
            // im Fehlerfall beide Ursachen nennen.
            None => engine_launch(&app).map_err(|engine_error| {
                format!(
                    "Kein nutzbares Repo unter {} (nötig: .venv/bin/speccify-web-backend via `uv sync` und apps/composer/dist via `pnpm run composer:build`). {engine_error}",
                    repo.display()
                )
            })?,
        },
        None => engine_launch(&app)?,
    };

    let port = free_port()?;
    let mut command = Command::new(&launch.binary);
    command
        .args(["--host", "127.0.0.1", "--port", &port.to_string()])
        .current_dir(&launch.cwd)
        .env("PATH", augmented_path())
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    for (key, value) in &launch.env {
        command.env(key, value);
    }
    let mut child = command
        .spawn()
        .map_err(|e| format!("{}: {e}", launch.binary.display()))?;

    let id = format!("composer-backend-{port}");
    if let Some(stdout) = child.stdout.take() {
        stream_reader(app.clone(), id.clone(), BufReader::new(stdout));
    }
    if let Some(stderr) = child.stderr.take() {
        stream_reader(app.clone(), id.clone(), BufReader::new(stderr));
    }
    state.0.lock().unwrap().insert(id.clone(), child);

    if !wait_for_port(port, std::time::Duration::from_secs(20)) {
        if let Some(mut child) = state.0.lock().unwrap().remove(&id) {
            let _ = child.kill();
            let _ = child.wait();
        }
        return Err(format!(
            "speccify-web-backend ({}) auf Port {port} nicht erreichbar (Log im Server-Tab prüfen).",
            launch.source
        ));
    }

    let url = format!("http://127.0.0.1:{port}/ui/");
    let parsed = url
        .parse()
        .map_err(|e| format!("Composer-URL ungültig: {e}"))?;
    let window = tauri::WebviewWindowBuilder::new(
        &app,
        format!("composer-{port}"),
        tauri::WebviewUrl::External(parsed),
    )
    .title(format!("Speccify Composer · {} · :{port}", launch.source))
    .inner_size(1320.0, 880.0)
    // Ohne das schluckt Tauris OS-Datei-Drop-Handler die HTML5-Drag-Events —
    // im Composer wird per Drag & Drop komponiert (Palette → Canvas/Slot).
    .disable_drag_drop_handler()
    .build()
    .map_err(|e| format!("Fenster: {e}"))?;

    // Fenster zu → Backend-Prozess sofort beenden (kein Weiterlaufen).
    let app_for_close = app.clone();
    window.on_window_event(move |event| {
        if matches!(event, tauri::WindowEvent::Destroyed) {
            let supervisor: State<Supervisor> = app_for_close.state();
            if let Some(mut child) = supervisor.0.lock().unwrap().remove(&id) {
                let _ = child.kill();
                let _ = child.wait();
            }
            let _ = app_for_close.emit("proc-exit", ExitEvent { id: id.clone() });
        }
    });

    Ok(url)
}

// --- Updater (Plan r5-distribution.md, R5.4) --------------------------------

/// Public Key des Updaters aus der Config. Leer bedeutet „noch kein
/// Signaturschlüssel erzeugt" — dann bleibt der Updater aus, statt beim
/// App-Start am unlesbaren Schlüssel zu scheitern.
fn updater_pubkey(config: &tauri::Config) -> Option<String> {
    pubkey_from_plugin_config(config.plugins.0.get("updater"))
}

fn pubkey_from_plugin_config(updater: Option<&serde_json::Value>) -> Option<String> {
    let key = updater?.get("pubkey")?.as_str()?.trim();
    (!key.is_empty()).then(|| key.to_string())
}

#[derive(Serialize)]
struct UpdaterStatus {
    /// Ist ein Public Key hinterlegt? Sonst kann die UI gar nicht erst prüfen.
    configured: bool,
    current_version: String,
    endpoints: Vec<String>,
}

/// Die UI fragt das ab, bevor sie einen „Nach Updates suchen"-Knopf zeigt.
#[tauri::command]
fn updater_status(app: AppHandle) -> UpdaterStatus {
    let config = app.config();
    let endpoints = config
        .plugins
        .0
        .get("updater")
        .and_then(|updater| updater.get("endpoints"))
        .and_then(|value| value.as_array())
        .map(|entries| {
            entries
                .iter()
                .filter_map(|entry| entry.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default();
    UpdaterStatus {
        configured: updater_pubkey(config).is_some(),
        current_version: app.package_info().version.to_string(),
        endpoints,
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let ask_bo = desktop_ui::AskBoRegistry::default();
    let ask_bo_for_setup = ask_bo.clone();
    let context = tauri::generate_context!();
    let updater_configured = updater_pubkey(context.config()).is_some();

    let builder = tauri::Builder::default()
        // Single-Instance zuerst (Plugin-Doku): eine zweite App-Instanz
        // würde sonst still einen eigenen desktop-ui-MCP versuchen und
        // ask_bo-Fragen in der falschen Instanz landen lassen.
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(Supervisor(Mutex::new(HashMap::new())))
        .manage(project_cmd::ProjectWindows::default())
        .manage(terminal::Terminals::default())
        .manage(ask_bo)
        .setup(move |app| {
            // desktop-ui-MCP (ask_bo) im App-Prozess: Agents erreichen ihn
            // über http://127.0.0.1:8768 (.mcp.json im Working Dir).
            ask_bo_for_setup.set_app(app.handle().clone());
            let server = desktop_ui::DesktopUiMcp::new(ask_bo_for_setup.clone());
            std::thread::spawn(move || {
                if let Err(error) = speccify_mcp_core::serve_http(
                    std::sync::Arc::new(server),
                    desktop_ui::DEFAULT_PORT,
                    "speccify desktop-ui-mcp",
                    None,
                ) {
                    eprintln!("desktop-ui-MCP: {error} (läuft die App doppelt?)");
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            spawn_process,
            kill_process,
            open_composer,
            project_cmd::project_open,
            project_cmd::project_current,
            project_cmd::project_recent,
            project_cmd::project_plans,
            project_cmd::project_skills,
            project_cmd::project_read_file,
            project_cmd::project_write_file,
            project_cmd::project_board,
            project_cmd::project_board_move,
            project_cmd::project_tools,
            project_cmd::project_platform,
            project_cmd::project_mcps,
            project_cmd::project_agent_files,
            settings::get_settings,
            settings::save_settings,
            settings::briefing_status,
            settings::create_briefing_file,
            toolbox_cmd::toolbox_list,
            toolbox_cmd::toolbox_scaffold,
            toolbox_cmd::mcp_status,
            engine::engine_status,
            engine::engine_install,
            system_cmd::doctor,
            system_cmd::python_list,
            system_cmd::python_install,
            system_cmd::kb_list,
            terminal::terminal_open,
            terminal::terminal_write,
            terminal::terminal_resize,
            terminal::terminal_kill,
            desktop_ui::ask_bo_answer,
            desktop_ui::ask_bo_pending,
            updater_status
        ]);

    // Updater erst anhängen, wenn ein Public Key hinterlegt ist — ohne
    // Schlüssel könnte er ohnehin keine Signatur prüfen.
    let builder = if updater_configured {
        builder.plugin(tauri_plugin_updater::Builder::new().build())
    } else {
        builder
    };

    builder
        .run(context)
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    /// Ohne hinterlegten Public Key darf der Updater nicht angehängt werden —
    /// sonst scheitert der Plugin-Setup und die App startet nicht mehr (R5.4).
    #[test]
    fn updater_stays_off_without_a_pubkey() {
        assert_eq!(pubkey_from_plugin_config(None), None);
        assert_eq!(pubkey_from_plugin_config(Some(&json!({}))), None);
        assert_eq!(
            pubkey_from_plugin_config(Some(&json!({"pubkey": ""}))),
            None
        );
        assert_eq!(
            pubkey_from_plugin_config(Some(&json!({"pubkey": "   \n"}))),
            None
        );
        assert_eq!(
            pubkey_from_plugin_config(Some(&json!({"pubkey": 42}))),
            None,
            "kein String ⇒ nicht konfiguriert statt Panik"
        );

        // Der Wert aus der ausgelieferten tauri.conf.json ist heute leer —
        // schlägt hier fehl, sobald jemand einen echten Key einträgt und
        // die Erwartung nicht mitzieht.
        let configured = pubkey_from_plugin_config(Some(&json!({
            "pubkey": "dW50cnVzdGVkIGNvbW1lbnQ6..."
        })));
        assert_eq!(configured.as_deref(), Some("dW50cnVzdGVkIGNvbW1lbnQ6..."));
    }
}
