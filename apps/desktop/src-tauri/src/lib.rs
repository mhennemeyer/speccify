use std::{
    collections::HashMap,
    io::{BufRead, BufReader},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, State};

mod actions_cmd;
mod agent_config;
mod agent_startup;
mod board_cmd;
mod desktop_ui;
mod engine;
mod files_cmd;
mod git_cmd;
mod help_docs;
mod playbook_cmd;
mod project_cmd;
mod project_watch;
mod settings;
mod sidecar;
mod skill_sources;
mod sources_cmd;
mod spec_tasks;
mod system_cmd;
mod terminal;
mod toolbox_cmd;
mod workflow_setup;
mod workspace_cmd;

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
    let desktop_ui_port = desktop_ui::configured_port().unwrap_or_else(|error| {
        eprintln!("{error}");
        std::process::exit(2);
    });

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
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(Supervisor(Mutex::new(HashMap::new())))
        .manage(project_cmd::ProjectWindows::default())
        .manage(project_watch::ProjectWatchers::default())
        .manage(actions_cmd::ActionRuns::default())
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
                    desktop_ui_port,
                    "speccify desktop-ui-mcp",
                    None,
                ) {
                    eprintln!("desktop-ui-MCP auf Port {desktop_ui_port}: {error}");
                }
            });
            // W7d: beim letzten Quit offene Projektfenster wieder öffnen.
            project_cmd::restore_open_windows(app.handle());
            workspace_cmd::restore_workspace_windows(app.handle());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            desktop_ui::desktop_ui_endpoint,
            spawn_process,
            kill_process,
            project_cmd::project_open,
            workspace_cmd::workspace_list,
            workspace_cmd::workspace_discover,
            workspace_cmd::workspace_edit,
            workspace_cmd::workspace_open,
            workspace_cmd::workspace_board,
            workspace_cmd::workspace_window_open,
            workspace_cmd::workspace_window_current,
            workspace_cmd::workspace_resolve_target,
            project_cmd::project_current,
            project_cmd::project_recent,
            project_cmd::project_skills,
            project_cmd::project_read_file,
            files_cmd::project_tree,
            files_cmd::project_file_info,
            git_cmd::project_git_status,
            git_cmd::project_git_diff,
            git_cmd::project_git_stage,
            git_cmd::project_git_commit,
            git_cmd::project_git_log,
            git_cmd::project_git_init,
            git_cmd::project_git_file_log,
            git_cmd::project_git_commit_detail,
            git_cmd::project_git_commit_diff,
            git_cmd::project_git_apply_patch,
            git_cmd::project_git_discard,
            git_cmd::project_git_branches,
            git_cmd::project_git_switch,
            git_cmd::project_git_branch_rename,
            git_cmd::project_git_branch_delete,
            git_cmd::project_git_blame,
            files_cmd::project_search,
            files_cmd::project_file_create,
            files_cmd::project_file_rename,
            files_cmd::project_file_delete,
            project_cmd::project_write_file,
            project_cmd::project_board,
            project_cmd::project_board_move,
            project_cmd::project_tools,
            project_cmd::project_platform,
            project_cmd::project_mcps,
            project_cmd::project_agent_files,
            workflow_setup::project_workflow_status,
            workflow_setup::project_workflow_install,
            workflow_setup::project_settings_get,
            workflow_setup::project_settings_set,
            actions_cmd::project_actions,
            actions_cmd::project_action_upsert,
            actions_cmd::project_action_delete,
            actions_cmd::project_action_confirm,
            actions_cmd::project_action_run,
            actions_cmd::project_action_stop,
            board_cmd::project_ticket_create,
            board_cmd::project_ticket_save,
            board_cmd::project_ticket_delete,
            board_cmd::project_ticket_history,
            board_cmd::project_board_kpis,
            board_cmd::project_ticket_questions,
            board_cmd::project_ticket_answer,
            board_cmd::project_spec_toggle_task,
            board_cmd::project_specs_number,
            help_docs::help_docs,
            help_docs::help_doc,
            agent_config::agent_config_list,
            agent_config::agent_config_read,
            agent_config::agent_config_write,
            skill_sources::project_skill_sources,
            skill_sources::source_browse,
            skill_sources::source_skill_read,
            skill_sources::source_validate,
            sources_cmd::sources_list,
            sources_cmd::source_add,
            sources_cmd::source_remove,
            sources_cmd::source_refresh,
            playbook_cmd::project_playbooks,
            playbook_cmd::project_playbook_create,
            playbook_cmd::project_playbook_delete,
            project_watch::project_watch_start,
            project_watch::project_watch_stop,
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
            agent_startup::project_agent_startup,
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
