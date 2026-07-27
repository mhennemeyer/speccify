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
mod settings;
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
struct LogEvent {
    id: String,
    line: String,
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

/// dotagent-CLI auffinden: `DOTAGENT_BIN` > angereicherter PATH.
/// Windows-Discovery folgt in Step 2+.
fn find_dotagent() -> Option<PathBuf> {
    if let Ok(bin) = std::env::var("DOTAGENT_BIN") {
        let path = PathBuf::from(bin);
        if path.is_file() {
            return Some(path);
        }
    }
    std::env::split_paths(&augmented_path())
        .map(|dir| dir.join("dotagent"))
        .find(|candidate| candidate.is_file())
}

/// Einzige CLI-Bridge der App: führt `dotagent <args>` aus und liefert stdout.
#[tauri::command]
fn run_dotagent(args: Vec<String>) -> Result<String, String> {
    let bin = find_dotagent()
        .ok_or("dotagent-CLI nicht gefunden (PATH, ~/.local/bin oder DOTAGENT_BIN prüfen)")?;
    let output = Command::new(&bin)
        .args(&args)
        .env("PATH", augmented_path())
        .output()
        .map_err(|e| format!("{}: {e}", bin.display()))?;
    if output.status.success() {
        String::from_utf8(output.stdout).map_err(|e| e.to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).into_owned())
    }
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
    let mut child = Command::new(&command)
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

/// Öffnet ein Composer-Fenster für das Speccify-Repo unter `repo`:
/// spawnt ein eigenes `speccify-web-backend` auf einem freien Port
/// (Supervisor-verwaltet, Logs als `proc-log`), wartet auf den Port und
/// lädt `http://127.0.0.1:<port>/ui/` (Backend serviert die gebaute
/// Composer-SPA same-origin). Fenster zu → Backend-Prozess stirbt.
#[tauri::command]
fn open_composer(app: AppHandle, state: State<Supervisor>, repo: String) -> Result<String, String> {
    let repo = expand_home(repo.trim());
    let backend_bin = repo.join(".venv/bin/speccify-web-backend");
    if !backend_bin.is_file() {
        return Err(format!(
            "Kein speccify-web-backend unter {} — Repo-Pfad prüfen und einmal `uv sync` ausführen.",
            backend_bin.display()
        ));
    }
    if !repo.join("apps/composer/dist/index.html").is_file() {
        return Err(
            "Composer-SPA ist nicht gebaut — einmal `pnpm run composer:build` im Repo ausführen."
                .into(),
        );
    }

    let port = free_port()?;
    // macOS-Quarantäne versteckt venv-.pth-Dateien wiederkehrend; PYTHONPATH
    // auf die src/-Verzeichnisse umgeht das (gleicher Workaround wie CLI/CI).
    let pythonpath = ["core/src", "cli/src", "mcp/src", "apps/web/backend/src"]
        .iter()
        .map(|p| repo.join(p).to_string_lossy().into_owned())
        .collect::<Vec<_>>()
        .join(":");

    let mut child = Command::new(&backend_bin)
        .args(["--host", "127.0.0.1", "--port", &port.to_string()])
        .current_dir(&repo)
        .env("PATH", augmented_path())
        .env("PYTHONPATH", pythonpath)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("{}: {e}", backend_bin.display()))?;

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
            "speccify-web-backend auf Port {port} nicht erreichbar (Log im Server-Tab prüfen)."
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
    .title(format!("Speccify Composer · :{port}"))
    .inner_size(1320.0, 880.0)
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let ask_bo = desktop_ui::AskBoRegistry::default();
    let ask_bo_for_setup = ask_bo.clone();
    tauri::Builder::default()
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
            run_dotagent,
            spawn_process,
            kill_process,
            open_composer,
            settings::get_settings,
            settings::save_settings,
            settings::briefing_status,
            settings::create_briefing_file,
            toolbox_cmd::toolbox_list,
            toolbox_cmd::toolbox_scaffold,
            toolbox_cmd::mcp_status,
            terminal::terminal_open,
            terminal::terminal_write,
            terminal::terminal_resize,
            terminal::terminal_kill,
            desktop_ui::ask_bo_answer,
            desktop_ui::ask_bo_pending
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
