//! Terminal-Seitenleiste (Plan toolkit-discovery-terminal.md, T6/D5):
//! echtes PTY (portable-pty) mit der Login-Shell des Users, cwd = Working
//! Dir aus den Settings. Output geht als `term-out`-Events ans Frontend
//! (xterm.js), Input über `terminal_write`. Beim Öffnen wird der
//! Autostart-Command aus den Settings in die Shell getippt (T0.5).
//! macOS/Linux: Login-Shell aus `$SHELL`; Windows (D16, Plan
//! projektfenster.md): ConPTY via portable-pty, `pwsh` wenn auf dem PATH,
//! sonst `powershell.exe` — und kein `-l` (das ist ein Unix-Login-Flag).

use std::collections::{HashMap, HashSet};
use std::io::{Read, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use portable_pty::{native_pty_system, ChildKiller, CommandBuilder, MasterPty, PtySize};
use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, State};

use crate::agent_startup::{self, login_shell, StartupReport};
use crate::settings;

struct TerminalSession {
    writer: Box<dyn Write + Send>,
    master: Box<dyn MasterPty + Send>,
    killer: Box<dyn ChildKiller + Send + Sync>,
    _workspace_claim: Option<WorkspaceClaim>,
    _workspace_context: Option<tempfile::NamedTempFile>,
}

struct WorkspaceClaim {
    id: String,
    claims: Arc<Mutex<HashSet<String>>>,
}
impl WorkspaceClaim {
    fn acquire(id: String, claims: Arc<Mutex<HashSet<String>>>) -> Result<Self, String> {
        if !claims.lock().map_err(|e| e.to_string())?.insert(id.clone()) {
            return Err("In diesem Workspace läuft bereits ein Terminal.".into());
        }
        Ok(Self { id, claims })
    }
}
impl Drop for WorkspaceClaim {
    fn drop(&mut self) {
        if let Ok(mut claims) = self.claims.lock() {
            claims.remove(&self.id);
        }
    }
}

/// Only plain presets are extended. Free shell commands keep their semantics.
fn workspace_launch(command: &str, launch: &str, context: &std::path::Path) -> String {
    let Ok(argv) = shell_words::split(command) else {
        return launch.into();
    };
    if argv.len() != 1 {
        return launch.into();
    }
    let host = std::path::Path::new(&argv[0])
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("");
    let path = agent_startup::quote(&context.to_string_lossy());
    match host {
        "claude" => format!("{launch} --append-system-prompt-file {path}"),
        "codex" => {
            let prompt = agent_startup::quote(&format!("Read the workspace context file at {} first, then read the listed repository guidance as needed. Briefly explain the workspace structure and wait for my task. Do not modify files during orientation.", context.display()));
            format!("{launch} {prompt}")
        }
        _ => launch.into(),
    }
}

/// Laufende Terminals; Drop killt die Shells beim App-Quit.
pub struct Terminals(
    Mutex<HashMap<String, TerminalSession>>,
    Arc<Mutex<HashSet<String>>>,
    AtomicBool,
);

impl Default for Terminals {
    fn default() -> Self {
        Self(
            Mutex::new(HashMap::new()),
            Arc::new(Mutex::new(HashSet::new())),
            AtomicBool::new(false),
        )
    }
}

impl Terminals {
    pub fn shutdown(&self) {
        self.2.store(true, Ordering::SeqCst);
        if let Ok(mut sessions) = self.0.lock() {
            for (_, mut session) in sessions.drain() {
                let _ = session.killer.kill();
            }
        }
    }
}

impl Drop for Terminals {
    fn drop(&mut self) {
        self.shutdown();
    }
}

#[derive(Clone, Serialize)]
struct TermOut {
    id: String,
    data: String,
}

#[derive(Clone, Serialize)]
struct TermExit {
    id: String,
}

#[derive(Serialize)]
pub struct TerminalOpened {
    cwd: String,
    startup: Option<StartupReport>,
}

/// Öffnet ein Terminal und tippt den Autostart-Command vor. Ohne `cwd`/
/// `autostart` gelten die App-Settings (Dashboard); das Projektfenster
/// übergibt beides selbst (Plan projektfenster.md, P1: cwd = Projektwurzel,
/// Agent-Kommando pro Projekt). → Startverzeichnis (für die UI-Anzeige).
#[tauri::command]
pub async fn terminal_open(
    app: AppHandle,
    window: tauri::WebviewWindow,
    state: State<'_, Terminals>,
    id: String,
    cols: u16,
    rows: u16,
    cwd: Option<String>,
    autostart: Option<String>,
    workspace_id: Option<String>,
) -> Result<TerminalOpened, String> {
    let window_workspace = window.label().strip_prefix("workspace-");
    if workspace_id
        .as_deref()
        .is_some_and(|id| Some(id) != window_workspace)
    {
        return Err("Workspace passt nicht zum Terminal-Fenster.".into());
    }
    let claim = window_workspace
        .map(|id| WorkspaceClaim::acquire(id.to_owned(), state.1.clone()))
        .transpose()?;
    // Webview destruction does not guarantee a React cleanup. Use the immutable
    // PTY id so an old window callback can never stop a replacement session.
    let destroyed = Arc::new(AtomicBool::new(false));
    let destroyed_event = destroyed.clone();
    let close_app = app.clone();
    let close_id = id.clone();
    window.on_window_event(move |event| {
        if matches!(event, tauri::WindowEvent::Destroyed) {
            destroyed_event.store(true, Ordering::SeqCst);
            let _ = terminal_kill(close_app.state(), close_id.clone());
        }
    });
    let context = match window_workspace {
        Some(id) => Some(crate::workspace_cmd::context_for_terminal(id.to_owned()).await?),
        None => None,
    };
    let app_settings = settings::get_settings()?;
    let cwd = match (context.as_ref(), cwd) {
        (Some(context), requested) => {
            if requested.as_ref().is_some_and(|path| path != &context.root) {
                return Err("Workspace-Terminal startet ausschließlich im Parent-Ordner.".into());
            }
            settings::resolve_working_dir(&context.root)?
        }
        (None, Some(dir)) => settings::resolve_working_dir(&dir)?,
        (None, None) => {
            let raw_dir = app_settings
                .working_dir
                .ok_or("Kein Working Dir gesetzt — zuerst im Settings-Tab wählen.")?;
            settings::resolve_working_dir(&raw_dir)?
        }
    };
    // None = Settings-Default; Some("") = bewusst reine Shell.
    let autostart = autostart
        .unwrap_or(app_settings.terminal_autostart_command)
        .trim()
        .to_string();

    let probe_app = app.clone();
    let probe_cwd = cwd.clone();
    let probe_command = autostart.clone();
    let prepared = tauri::async_runtime::spawn_blocking(move || {
        agent_startup::prepare(&probe_app, &probe_cwd, &probe_command)
    })
    .await
    .map_err(|e| e.to_string())?;
    // A plain shell remains available even if a profile cannot be probed.
    let startup = match prepared {
        Ok(report) if !report.host_ready => {
            return Err(report
                .error
                .unwrap_or_else(|| "Agent nicht startbar".into()))
        }
        Ok(report) => Some(report),
        Err(_) if autostart.is_empty() => None,
        Err(error) => return Err(error),
    };

    let context_file = context
        .as_ref()
        .map(|context| -> Result<_, String> {
            let mut file = tempfile::Builder::new()
                .prefix("speccify-workspace-")
                .suffix(".md")
                .tempfile()
                .map_err(|e| e.to_string())?;
            file.write_all(context.markdown.as_bytes())
                .map_err(|e| e.to_string())?;
            file.flush().map_err(|e| e.to_string())?;
            Ok(file)
        })
        .transpose()?;
    if destroyed.load(Ordering::SeqCst) || state.2.load(Ordering::SeqCst) {
        return Err("Terminal-Fenster wurde geschlossen.".into());
    }

    let pty = native_pty_system()
        .openpty(PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|e| format!("PTY: {e}"))?;

    let shell = login_shell();
    let mut command = CommandBuilder::new(&shell);
    #[cfg(not(windows))]
    command.arg("-l"); // Login-Shell: PATH/Profile des Users
    command.cwd(&cwd);
    command.env("TERM", "xterm-256color");
    command.env("PATH", crate::augmented_path());
    if let Some(file) = &context_file {
        command.env("SPECCIFY_WORKSPACE_ROOT", &cwd);
        command.env("SPECCIFY_WORKSPACE_CONTEXT", file.path());
    }

    let child = pty
        .slave
        .spawn_command(command)
        .map_err(|e| format!("{shell}: {e}"))?;
    let mut killer = child.clone_killer();

    let mut reader = pty
        .master
        .try_clone_reader()
        .map_err(|e| format!("PTY-Reader: {e}"))?;
    let mut writer = pty
        .master
        .take_writer()
        .map_err(|e| format!("PTY-Writer: {e}"))?;

    // Autostart-Command vortippen (die tty-Eingabe puffert, bis die Shell
    // liest). Leer = reines Terminal.
    let preamble = startup
        .as_ref()
        .map(|report| {
            agent_startup::path_setup(report.runtime_dir.as_deref().map(std::path::Path::new))
        })
        .unwrap_or_default();
    let launch = startup
        .as_ref()
        .map(|r| r.launch.as_str())
        .unwrap_or(&autostart);
    let launch = context_file
        .as_ref()
        .map(|file| workspace_launch(&autostart, launch, file.path()))
        .unwrap_or_else(|| launch.to_owned());
    if !preamble.is_empty() || !launch.is_empty() {
        if let Err(error) = writer
            .write_all(format!("{preamble}{launch}\r").as_bytes())
            .and_then(|_| writer.flush())
        {
            let _ = killer.kill();
            return Err(format!(
                "Terminal-Start konnte nicht geschrieben werden: {error}"
            ));
        }
    }

    // Reader-Thread: PTY-Output als Events (lossy — Escape-Sequenzen sind
    // Bytes, xterm.js verdaut UTF-8-Strings).
    let app_for_reader = app.clone();
    let id_for_reader = id.clone();
    std::thread::spawn(move || {
        let mut buffer = [0u8; 8192];
        loop {
            match reader.read(&mut buffer) {
                Ok(0) | Err(_) => break,
                Ok(count) => {
                    let data = String::from_utf8_lossy(&buffer[..count]).into_owned();
                    let _ = app_for_reader.emit(
                        "term-out",
                        TermOut {
                            id: id_for_reader.clone(),
                            data,
                        },
                    );
                }
            }
        }
        let _ = app_for_reader.emit("term-exit", TermExit { id: id_for_reader });
    });

    let mut sessions = state.0.lock().map_err(|e| e.to_string())?;
    if destroyed.load(Ordering::SeqCst) || state.2.load(Ordering::SeqCst) {
        let _ = killer.kill();
        return Err("Terminal-Fenster wurde geschlossen.".into());
    }
    sessions.insert(
        id,
        TerminalSession {
            writer,
            master: pty.master,
            killer,
            _workspace_claim: claim,
            _workspace_context: context_file,
        },
    );
    Ok(TerminalOpened {
        cwd: cwd.display().to_string(),
        startup,
    })
}

#[tauri::command]
pub fn terminal_write(state: State<Terminals>, id: String, data: String) -> Result<(), String> {
    let mut sessions = state.0.lock().unwrap();
    let session = sessions
        .get_mut(&id)
        .ok_or_else(|| format!("Kein Terminal: {id}"))?;
    session
        .writer
        .write_all(data.as_bytes())
        .and_then(|_| session.writer.flush())
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_resize(
    state: State<Terminals>,
    id: String,
    cols: u16,
    rows: u16,
) -> Result<(), String> {
    let sessions = state.0.lock().unwrap();
    let session = sessions
        .get(&id)
        .ok_or_else(|| format!("Kein Terminal: {id}"))?;
    session
        .master
        .resize(PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_kill(state: State<Terminals>, id: String) -> Result<bool, String> {
    match state.0.lock().unwrap().remove(&id) {
        Some(mut session) => {
            let _ = session.killer.kill();
            Ok(true)
        }
        None => Ok(false),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn workspace_claim_covers_pending_open_and_releases_on_failure() {
        let claims = Arc::new(Mutex::new(HashSet::new()));
        let first = WorkspaceClaim::acquire("one".into(), claims.clone()).unwrap();
        assert!(WorkspaceClaim::acquire("one".into(), claims.clone()).is_err());
        assert!(WorkspaceClaim::acquire("two".into(), claims.clone()).is_ok());
        drop(first);
        assert!(WorkspaceClaim::acquire("one".into(), claims).is_ok());
    }

    #[test]
    fn workspace_presets_quote_context_without_changing_custom_commands() {
        let path = std::path::Path::new("/tmp/context with ' quotes.md");
        let claude = workspace_launch("claude", "claude", path);
        assert!(claude.starts_with("claude --append-system-prompt-file "));
        assert!(claude.ends_with(&agent_startup::quote(&path.to_string_lossy())));
        let codex = workspace_launch("codex", "codex", path);
        assert!(codex.contains("Read the workspace context file"));
        assert!(codex.contains("Do not modify files"));
        for command in [
            "",
            "my-host",
            "codex --model custom",
            "claude && echo custom",
        ] {
            assert_eq!(workspace_launch(command, command, path), command);
        }
    }

    /// Validiert das Kern-Muster von terminal_open ohne Tauri: Shell im PTY
    /// spawnen, Kommando VOR dem Shell-Prompt vortippen (tty puffert),
    /// Output lesen. Genau so tippt terminal_open den Autostart-Command.
    // Windows: im cargo-test-Harness liefert ConPTY keine Ausgabe (leerer
    // Reader trotz laufender Shell; als SYSTEM wie als interaktiver Benutzer
    // reproduziert, 2026-08-27). Das App-Terminal — derselbe Codepfad in
    // terminal_open — ist auf Windows E2E verifiziert (Plan projektfenster.md,
    // P2). Bis die Harness-Ursache verstanden ist, läuft der Test dort nicht.
    #[cfg_attr(
        windows,
        ignore = "ConPTY schweigt im Test-Harness; D16 ist E2E belegt"
    )]
    #[test]
    fn pty_spawn_pretype_and_read() {
        let pty = native_pty_system()
            .openpty(PtySize {
                rows: 24,
                cols: 80,
                pixel_width: 0,
                pixel_height: 0,
            })
            .unwrap();
        let mut command = CommandBuilder::new(login_shell());
        command.cwd(std::env::temp_dir());
        command.env("TERM", "xterm-256color");
        let mut child = pty.slave.spawn_command(command).unwrap();
        // Slave nach dem Spawn schließen wie in terminal_open (dort fällt er
        // beim Return aus dem Scope) — auf ConPTY kommt sonst kein Output an.
        drop(pty.slave);

        let mut writer = pty.master.take_writer().unwrap();
        writer.write_all(b"echo pty-smoke-ok; exit\r").unwrap();

        // Lesen im eigenen Thread: `read` blockiert, und wenn die Shell im
        // PTY gar nichts liefert (z. B. Session 0 ohne Interaktivität), würde
        // eine Deadline in der Leseschleife nie geprüft — der Test hinge.
        let mut reader = pty.master.try_clone_reader().unwrap();
        let (sender, receiver) = std::sync::mpsc::channel();
        std::thread::spawn(move || {
            let mut collected = String::new();
            let mut buffer = [0u8; 4096];
            loop {
                match reader.read(&mut buffer) {
                    Ok(0) | Err(_) => break,
                    Ok(count) => {
                        collected.push_str(&String::from_utf8_lossy(&buffer[..count]));
                        if collected.contains("pty-smoke-ok") {
                            break;
                        }
                    }
                }
            }
            let _ = sender.send(collected);
        });
        let collected = receiver
            .recv_timeout(std::time::Duration::from_secs(20))
            .unwrap_or_default();
        let _ = child.kill();
        assert!(
            collected.contains("pty-smoke-ok"),
            "PTY-Output: {collected}"
        );
        let context = tempfile::NamedTempFile::new().unwrap();
        let context_path = context.path().to_owned();
        let state = Terminals::default();
        let claim = WorkspaceClaim::acquire("shutdown-test".into(), state.1.clone()).unwrap();
        state.0.lock().unwrap().insert(
            "test".into(),
            TerminalSession {
                writer,
                master: pty.master,
                killer: child.clone_killer(),
                _workspace_claim: Some(claim),
                _workspace_context: Some(context),
            },
        );
        state.shutdown();
        assert!(state.2.load(Ordering::SeqCst));
        assert!(state.0.lock().unwrap().is_empty());
        assert!(state.1.lock().unwrap().is_empty());
        assert!(
            !context_path.exists(),
            "shutdown removes the private context before process exit"
        );
    }
}
