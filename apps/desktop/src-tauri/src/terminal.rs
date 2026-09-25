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
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use portable_pty::{native_pty_system, ChildKiller, CommandBuilder, MasterPty, PtySize};
use serde::Serialize;
use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager, State};

use crate::agent_session::{self, AgentSession, SessionRequest, Utf8Chunker};
use crate::agent_startup::{self, login_shell, StartupReport};
use crate::pty_host::HostLink;
use crate::settings;

#[tauri::command]
pub fn terminal_attention(
    window: tauri::WebviewWindow,
    state: State<'_, Terminals>,
    id: String,
) -> Result<(), String> {
    let owned = state
        .windows
        .lock()
        .map_err(|e| e.to_string())?
        .get(window.label())
        .is_some_and(|entry| entry.ids.contains(&id));
    if !owned {
        return Err("Terminal gehört nicht zu diesem Fenster.".into());
    }
    if !crate::terminal_preferences::terminal_preferences()?.system_notifications
        || window.is_focused().map_err(|e| e.to_string())?
    {
        return Ok(());
    }
    let _ = window.request_user_attention(Some(tauri::UserAttentionType::Informational));
    notify_terminal(
        window.app_handle(),
        "Ein Terminal wartet auf Deine Aufmerksamkeit. Öffne Speccify und wähle ‚Zum Terminal‘.",
    )
}

fn notify_terminal(app: &AppHandle, body: &str) -> Result<(), String> {
    use tauri_plugin_notification::NotificationExt;
    app.notification()
        .builder()
        .title("Speccify · Terminal")
        .body(body)
        .show()
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_notification_test(app: AppHandle) -> Result<(), String> {
    notify_terminal(
        &app,
        "Test: Rückfragen aus dem Terminal können hier angezeigt werden.",
    )
}

/// Wo das PTY lebt: im App-Prozess (wie bisher) oder im PTY-Host (Spec 070),
/// dessen Sitzungen das App-Ende überleben.
enum Backend {
    Local {
        writer: Box<dyn Write + Send>,
        master: Box<dyn MasterPty + Send>,
        killer: Box<dyn ChildKiller + Send + Sync>,
    },
    Hosted {
        client: Arc<speccify_pty_host::Client>,
    },
}

struct TerminalSession {
    id: String,
    backend: Backend,
    _workspace_claim: Option<WorkspaceClaim>,
    _workspace_context: Option<tempfile::NamedTempFile>,
    /// Kontextdatei einer gehosteten Sitzung (D4): bleibt liegen, bis die
    /// Sitzung bewusst beendet wird.
    hosted_context: Option<PathBuf>,
}

impl TerminalSession {
    fn hosted(&self) -> bool {
        matches!(self.backend, Backend::Hosted { .. })
    }
    fn write(&mut self, data: &[u8]) -> Result<(), String> {
        match &mut self.backend {
            Backend::Local { writer, .. } => writer
                .write_all(data)
                .and_then(|_| writer.flush())
                .map_err(|e| e.to_string()),
            Backend::Hosted { client } => client.write(&self.id, data),
        }
    }
    fn resize(&self, cols: u16, rows: u16) -> Result<(), String> {
        match &self.backend {
            Backend::Local { master, .. } => master
                .resize(PtySize {
                    rows,
                    cols,
                    pixel_width: 0,
                    pixel_height: 0,
                })
                .map_err(|e| e.to_string()),
            Backend::Hosted { client } => client.resize(&self.id, cols, rows),
        }
    }
    /// Beendet den Prozess — auch im Host.
    fn kill(&mut self) {
        match &mut self.backend {
            Backend::Local { killer, .. } => {
                let _ = killer.kill();
            }
            Backend::Hosted { client } => {
                let _ = client.kill(&self.id);
            }
        }
        if let Some(path) = self.hosted_context.take() {
            let _ = std::fs::remove_file(path);
        }
    }
    /// Lässt eine gehostete Sitzung weiterlaufen und trennt nur die App;
    /// eine lokale Sitzung kann nicht getrennt werden und wird beendet.
    fn detach_or_kill(&mut self) {
        match &self.backend {
            Backend::Hosted { client } => {
                let _ = client.detach(&self.id);
            }
            Backend::Local { .. } => self.kill(),
        }
    }
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

/// Terminals eines Fensters: Ids plus ein Lebenszeichen, das der einmal je
/// Fenster registrierte Destroyed-Listener löscht (Spec 009, D6 — kein
/// Listener pro Start).
struct WindowTerminals {
    ids: HashSet<String>,
    alive: Arc<AtomicBool>,
}

/// Laufende Terminals; Drop killt die lokalen Shells beim App-Quit, gehostete
/// (Spec 070) werden nur getrennt.
#[derive(Default)]
pub struct Terminals {
    sessions: Mutex<HashMap<String, TerminalSession>>,
    workspace_claims: Arc<Mutex<HashSet<String>>>,
    windows: Mutex<HashMap<String, WindowTerminals>>,
    shutting_down: AtomicBool,
    pub(crate) host: HostLink,
}

impl Terminals {
    /// Running work that a restart would destroy: local shells only — hosted
    /// sessions survive the app (Spec 070), so they never block an update.
    pub(crate) fn has_active_work(&self) -> bool {
        self.sessions.lock().unwrap().values().any(|s| !s.hosted())
    }
    pub(crate) fn active_count(&self) -> usize {
        self.sessions
            .lock()
            .unwrap()
            .values()
            .filter(|s| !s.hosted())
            .count()
    }
    /// Ends every shell but keeps the app usable: unlike `shutdown`, new
    /// terminals may be opened afterwards. The reader threads report the exits.
    pub(crate) fn stop_all(&self) -> usize {
        // Kill outside the map lock; the reader threads take it on exit.
        let sessions: Vec<_> = self.sessions.lock().unwrap().drain().collect();
        let count = sessions.len();
        for (id, mut session) in sessions {
            session.kill();
            self.untrack(&id);
        }
        self.release_host_if_unused();
        count
    }
    /// A shell that ended on its own is no running work any more.
    pub(crate) fn forget(&self, id: &str) {
        self.sessions.lock().unwrap().remove(id);
        self.untrack(id);
        self.release_host_if_unused();
    }
    /// Without hosted sessions the app drops its host connection, so a host
    /// with no sessions and no clients can end itself (Spec 070).
    fn release_host_if_unused(&self) {
        let hosted = self.sessions.lock().unwrap().values().any(|s| s.hosted());
        if !hosted {
            self.host.disconnect();
        }
    }
    /// The app is about to exit: from now on a destroyed window detaches its
    /// hosted terminals instead of killing them (D3).
    pub(crate) fn begin_shutdown(&self) {
        self.shutting_down.store(true, Ordering::SeqCst);
    }
    /// A window went away: kill local terminals; hosted ones only when the
    /// window was closed deliberately, not when the whole app exits.
    fn release(&self, id: &str) {
        self.untrack(id);
        let removed = self.sessions.lock().unwrap().remove(id);
        if let Some(mut session) = removed {
            if self.shutting_down.load(Ordering::SeqCst) {
                session.detach_or_kill();
            } else {
                session.kill();
            }
        }
        if !self.shutting_down.load(Ordering::SeqCst) {
            self.release_host_if_unused();
        }
    }
    pub fn shutdown(&self) {
        self.shutting_down.store(true, Ordering::SeqCst);
        if let Ok(mut sessions) = self.sessions.lock() {
            for (_, mut session) in sessions.drain() {
                session.detach_or_kill();
            }
        }
        if let Ok(mut windows) = self.windows.lock() {
            windows.clear();
        }
    }

    /// Registers the window's destroy listener once and records `id` for it.
    /// Returns the window's liveness flag for the pending open.
    fn track(&self, window: &tauri::WebviewWindow, id: &str) -> Result<Arc<AtomicBool>, String> {
        let mut windows = self.windows.lock().map_err(|e| e.to_string())?;
        let label = window.label().to_owned();
        let entry = windows.entry(label.clone()).or_insert_with(|| {
            let alive = Arc::new(AtomicBool::new(true));
            let alive_event = alive.clone();
            let app = window.app_handle().clone();
            window.on_window_event(move |event| {
                if matches!(event, tauri::WindowEvent::Destroyed) {
                    alive_event.store(false, Ordering::SeqCst);
                    let state = app.state::<Terminals>();
                    let ids = state
                        .windows
                        .lock()
                        .ok()
                        .and_then(|mut windows| windows.remove(&label))
                        .map(|entry| entry.ids)
                        .unwrap_or_default();
                    for id in ids {
                        state.release(&id);
                    }
                }
            });
            WindowTerminals {
                ids: HashSet::new(),
                alive,
            }
        });
        entry.ids.insert(id.to_owned());
        Ok(entry.alive.clone())
    }

    fn untrack(&self, id: &str) {
        if let Ok(mut windows) = self.windows.lock() {
            for entry in windows.values_mut() {
                entry.ids.remove(id);
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
pub(crate) struct TermOut {
    pub id: String,
    pub data: String,
}

#[derive(Clone, Serialize)]
pub(crate) struct TermExit {
    pub id: String,
}

#[derive(Serialize)]
pub struct TerminalOpened {
    cwd: String,
    startup: Option<StartupReport>,
    /// Identity the UI remembers for an exact resume (Spec 009, D4).
    session: Option<AgentSession>,
    /// The command line that was typed into the shell.
    launch: String,
    /// Spec 070: the terminal was re-attached to a session that kept running
    /// in the PTY host; nothing was started.
    reattached: bool,
}

/// A session in the PTY host that belongs to a window (Spec 070).
#[derive(Serialize)]
pub struct LiveSession {
    id: String,
    cwd: String,
    launch: String,
    autostart: String,
    session: Option<AgentSession>,
    started_at: u64,
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
    session: Option<SessionRequest>,
) -> Result<TerminalOpened, String> {
    let _permit = crate::updates::begin_work(&app)?;
    let window_workspace = window.label().strip_prefix("workspace-");
    if workspace_id
        .as_deref()
        .is_some_and(|id| Some(id) != window_workspace)
    {
        return Err("Workspace passt nicht zum Terminal-Fenster.".into());
    }
    let claim = window_workspace
        .map(|id| WorkspaceClaim::acquire(id.to_owned(), state.workspace_claims.clone()))
        .transpose()?;
    // Webview destruction does not guarantee a React cleanup: the window's
    // single destroy listener kills every terminal id recorded for it.
    let alive = state.track(&window, &id)?;
    let session = session.unwrap_or_default();
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
    if !alive.load(Ordering::SeqCst) || state.shutting_down.load(Ordering::SeqCst) {
        state.untrack(&id);
        return Err("Terminal-Fenster wurde geschlossen.".into());
    }
    let launch_base = startup
        .as_ref()
        .map(|r| r.launch.as_str())
        .unwrap_or(&autostart);
    let launch_base = context_file
        .as_ref()
        .map(|file| workspace_launch(&autostart, launch_base, file.path()))
        .unwrap_or_else(|| launch_base.to_owned());
    // Exact resume or a fresh identity — checked before anything is spawned,
    // so a missing session is an error, never a silently different session.
    let home = settings::home_dir()?;
    let (launch, identity) =
        agent_session::session_launch(&autostart, &launch_base, &session, &home)
            .inspect_err(|_| state.untrack(&id))?;

    let shell = login_shell();
    // Autostart-Command vortippen (die tty-Eingabe puffert, bis die Shell
    // liest). Leer = reines Terminal.
    let preamble = startup
        .as_ref()
        .map(|report| {
            agent_startup::path_setup(report.runtime_dir.as_deref().map(std::path::Path::new))
        })
        .unwrap_or_default();
    let input = if preamble.is_empty() && launch.is_empty() {
        String::new()
    } else {
        format!("{preamble}{launch}\r")
    };
    let persist = crate::terminal_preferences::terminal_preferences()
        .map(|prefs| prefs.persist_sessions)
        .unwrap_or(false);
    // Spec 070, D4: die Kontextdatei einer gehosteten Sitzung muss den
    // App-Prozess überleben — Kopie außerhalb des App-Temp.
    let hosted_context = if persist {
        context_file
            .as_ref()
            .map(|file| -> Result<PathBuf, String> {
                let target = crate::pty_host::context_dir()?.join(format!("{id}-context.md"));
                std::fs::copy(file.path(), &target).map_err(|e| e.to_string())?;
                Ok(target)
            })
            .transpose()?
    } else {
        None
    };
    let mut env: Vec<(String, String)> = vec![
        ("TERM".into(), "xterm-256color".into()),
        (
            "PATH".into(),
            crate::augmented_path().to_string_lossy().into_owned(),
        ),
    ];
    if let Some(file) = &context_file {
        env.push(("SPECCIFY_WORKSPACE_ROOT".into(), cwd.display().to_string()));
        let path = hosted_context.as_deref().unwrap_or(file.path());
        env.push((
            "SPECCIFY_WORKSPACE_CONTEXT".into(),
            path.display().to_string(),
        ));
    }

    if persist {
        let kind = if window_workspace.is_some() {
            "workspace"
        } else if window.label() == "main" {
            "dashboard"
        } else {
            "project"
        };
        let meta = json!({
            "window": window.label(),
            "kind": kind,
            "cwd": cwd.display().to_string(),
            "autostart": autostart,
            "launch": launch,
            "session": identity,
            "workspace_id": window_workspace,
            "context": hosted_context.as_ref().map(|p| p.display().to_string()),
        });
        let mut args: Vec<String> = Vec::new();
        #[cfg(not(windows))]
        args.push("-l".into()); // Login-Shell: PATH/Profile des Users
        let hosted = state.host.client(&app).and_then(|client| {
            client
                .open(
                    &id,
                    &shell,
                    &args,
                    &cwd.display().to_string(),
                    &env,
                    cols,
                    rows,
                    input.as_bytes(),
                    meta,
                )
                .map(|_| client)
        });
        match hosted {
            Ok(client) => {
                let mut sessions = state.sessions.lock().map_err(|e| e.to_string())?;
                if !alive.load(Ordering::SeqCst) || state.shutting_down.load(Ordering::SeqCst) {
                    let _ = client.kill(&id);
                    state.untrack(&id);
                    return Err("Terminal-Fenster wurde geschlossen.".into());
                }
                sessions.insert(
                    id.clone(),
                    TerminalSession {
                        id: id.clone(),
                        backend: Backend::Hosted { client },
                        _workspace_claim: claim,
                        _workspace_context: None,
                        hosted_context,
                    },
                );
                return Ok(TerminalOpened {
                    cwd: cwd.display().to_string(),
                    startup,
                    session: identity,
                    launch,
                    reattached: false,
                });
            }
            Err(error) => {
                // Sichtbarer Rückfall auf den App-Prozess statt stillem Scheitern.
                eprintln!("PTY-Host: {error}");
                let _ = app.emit(
                    "term-out",
                    TermOut {
                        id: id.clone(),
                        data: format!(
                            "\x1b[33m[PTY-Host nicht verfügbar: {error} — dieses Terminal läuft im App-Prozess und überlebt keinen Neustart]\x1b[0m\r\n"
                        ),
                    },
                );
                if let Some(path) = &hosted_context {
                    let _ = std::fs::remove_file(path);
                }
            }
        }
    }

    let pty = native_pty_system()
        .openpty(PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|e| format!("PTY: {e}"))?;

    let mut command = CommandBuilder::new(&shell);
    #[cfg(not(windows))]
    command.arg("-l"); // Login-Shell: PATH/Profile des Users
    command.cwd(&cwd);
    for (key, value) in &env {
        command.env(key, value);
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

    if !input.is_empty() {
        if let Err(error) = writer
            .write_all(input.as_bytes())
            .and_then(|_| writer.flush())
        {
            let _ = killer.kill();
            state.untrack(&id);
            return Err(format!(
                "Terminal-Start konnte nicht geschrieben werden: {error}"
            ));
        }
    }

    // Reader-Thread: PTY-Output als Events. Der Thread läuft, bevor diese
    // Antwort das Frontend erreicht; das Frontend registriert seine Listener
    // vor dem Aufruf, frühe Ausgabe geht also nicht verloren. UTF-8 wird über
    // Blockgrenzen zusammengesetzt (D6); nach EOF wird das Kind abgewartet,
    // damit kein Zombie zurückbleibt.
    let app_for_reader = app.clone();
    let id_for_reader = id.clone();
    let mut child = child;
    let exited = Arc::new(AtomicBool::new(false));
    let exited_for_reader = exited.clone();
    std::thread::spawn(move || {
        let mut buffer = [0u8; 8192];
        let mut chunker = Utf8Chunker::default();
        let emit = |data: String| {
            if !data.is_empty() {
                let _ = app_for_reader.emit(
                    "term-out",
                    TermOut {
                        id: id_for_reader.clone(),
                        data,
                    },
                );
            }
        };
        loop {
            match reader.read(&mut buffer) {
                Ok(0) | Err(_) => break,
                Ok(count) => emit(chunker.push(&buffer[..count])),
            }
        }
        emit(chunker.finish());
        let _ = child.wait();
        // An ended shell must not count as running work (it blocked updates
        // until its panel closed). The flag covers an exit before registration.
        exited_for_reader.store(true, Ordering::SeqCst);
        app_for_reader.state::<Terminals>().forget(&id_for_reader);
        let _ = app_for_reader.emit("term-exit", TermExit { id: id_for_reader });
    });

    let mut sessions = state.sessions.lock().map_err(|e| e.to_string())?;
    if !alive.load(Ordering::SeqCst) || state.shutting_down.load(Ordering::SeqCst) {
        let _ = killer.kill();
        state.untrack(&id);
        return Err("Terminal-Fenster wurde geschlossen.".into());
    }
    sessions.insert(
        id.clone(),
        TerminalSession {
            id: id.clone(),
            backend: Backend::Local {
                writer,
                master: pty.master,
                killer,
            },
            _workspace_claim: claim,
            _workspace_context: context_file,
            hosted_context: None,
        },
    );
    if exited.load(Ordering::SeqCst) {
        sessions.remove(&id);
    }
    Ok(TerminalOpened {
        cwd: cwd.display().to_string(),
        startup,
        session: identity,
        launch,
        reattached: false,
    })
}

fn meta_str(meta: &Value, key: &str) -> String {
    meta.get(key)
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_owned()
}

fn meta_session(meta: &Value) -> Option<AgentSession> {
    meta.get("session")
        .cloned()
        .and_then(|value| serde_json::from_value(value).ok())
}

/// Spec 070: Sitzungen im PTY-Host, die zu diesem Fenster gehören und noch
/// laufen. Leer, wenn die Einstellung aus ist oder kein Host läuft; startet
/// keinen Host.
#[tauri::command]
pub fn terminal_live(
    app: AppHandle,
    window: tauri::WebviewWindow,
    state: State<'_, Terminals>,
) -> Result<Vec<LiveSession>, String> {
    let attached: HashSet<String> = state.sessions.lock().unwrap().keys().cloned().collect();
    Ok(state
        .host
        .live_sessions(&app)
        .into_iter()
        .filter(|entry| {
            entry.get("meta").map(|m| meta_str(m, "window")) == Some(window.label().to_owned())
        })
        .filter(|entry| !attached.contains(entry.get("id").and_then(Value::as_str).unwrap_or("")))
        .map(|entry| {
            let meta = entry.get("meta").cloned().unwrap_or(Value::Null);
            LiveSession {
                id: entry
                    .get("id")
                    .and_then(Value::as_str)
                    .unwrap_or("")
                    .to_owned(),
                cwd: meta_str(&meta, "cwd"),
                launch: meta_str(&meta, "launch"),
                autostart: meta_str(&meta, "autostart"),
                session: meta_session(&meta),
                started_at: entry.get("started_at").and_then(Value::as_u64).unwrap_or(0),
            }
        })
        .collect())
}

/// Spec 070: hängt das Fenster wieder an eine laufende Host-Sitzung. Der
/// Puffer kommt als `term-out`, bevor der Aufruf zurückkehrt; danach folgt
/// die lebende Ausgabe in Reihenfolge.
#[tauri::command]
pub async fn terminal_attach(
    app: AppHandle,
    window: tauri::WebviewWindow,
    state: State<'_, Terminals>,
    id: String,
    cols: u16,
    rows: u16,
) -> Result<TerminalOpened, String> {
    let window_workspace = window.label().strip_prefix("workspace-");
    let claim = window_workspace
        .map(|ws| WorkspaceClaim::acquire(ws.to_owned(), state.workspace_claims.clone()))
        .transpose()?;
    let alive = state.track(&window, &id)?;
    let client = state
        .host
        .client(&app)
        .inspect_err(|_| state.untrack(&id))?;
    let listed = client
        .list()
        .inspect_err(|_| state.untrack(&id))?
        .into_iter()
        .find(|entry| entry.get("id").and_then(Value::as_str) == Some(id.as_str()))
        .ok_or_else(|| {
            state.untrack(&id);
            format!("Keine laufende Sitzung {id} im PTY-Host.")
        })?;
    let meta = listed.get("meta").cloned().unwrap_or(Value::Null);
    if meta_str(&meta, "window") != window.label() {
        state.untrack(&id);
        return Err("Die Sitzung gehört zu einem anderen Fenster.".into());
    }
    let reply = state
        .host
        .attach(&app, &client, &id)
        .inspect_err(|_| state.untrack(&id))?;
    let _ = client.resize(&id, cols, rows);
    let mut sessions = state.sessions.lock().map_err(|e| e.to_string())?;
    if !alive.load(Ordering::SeqCst) || state.shutting_down.load(Ordering::SeqCst) {
        let _ = client.detach(&id);
        state.untrack(&id);
        return Err("Terminal-Fenster wurde geschlossen.".into());
    }
    sessions.insert(
        id.clone(),
        TerminalSession {
            id: id.clone(),
            backend: Backend::Hosted { client },
            _workspace_claim: claim,
            _workspace_context: None,
            hosted_context: meta
                .get("context")
                .and_then(Value::as_str)
                .map(PathBuf::from),
        },
    );
    if reply.exit_code.is_some() {
        sessions.remove(&id);
    }
    Ok(TerminalOpened {
        cwd: meta_str(&meta, "cwd"),
        startup: None,
        session: meta_session(&meta),
        launch: meta_str(&meta, "launch"),
        reattached: true,
    })
}

#[tauri::command]
pub fn terminal_write(state: State<Terminals>, id: String, data: String) -> Result<(), String> {
    let mut sessions = state.sessions.lock().unwrap();
    let session = sessions
        .get_mut(&id)
        .ok_or_else(|| format!("Kein Terminal: {id}"))?;
    session.write(data.as_bytes())
}

#[tauri::command]
pub fn terminal_resize(
    state: State<Terminals>,
    id: String,
    cols: u16,
    rows: u16,
) -> Result<(), String> {
    let sessions = state.sessions.lock().unwrap();
    let session = sessions
        .get(&id)
        .ok_or_else(|| format!("Kein Terminal: {id}"))?;
    session.resize(cols, rows)
}

/// Beendet ein Terminal bewusst — auch eine gehostete Sitzung („Neu starten“,
/// Panel geschlossen).
#[tauri::command]
pub fn terminal_kill(state: State<Terminals>, id: String) -> Result<bool, String> {
    state.untrack(&id);
    let removed = state.sessions.lock().unwrap().remove(&id);
    let existed = match removed {
        Some(mut session) => {
            session.kill();
            true
        }
        None => false,
    };
    state.release_host_if_unused();
    Ok(existed)
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
        let claim = WorkspaceClaim::acquire("shutdown-test".into(), state.workspace_claims.clone())
            .unwrap();
        state.sessions.lock().unwrap().insert(
            "test".into(),
            TerminalSession {
                id: "test".into(),
                backend: Backend::Local {
                    writer,
                    master: pty.master,
                    killer: child.clone_killer(),
                },
                _workspace_claim: Some(claim),
                _workspace_context: Some(context),
                hosted_context: None,
            },
        );
        // "Alles stoppen": ends the work, releases claim and context, and
        // leaves the app able to open terminals again.
        assert_eq!(state.active_count(), 1);
        assert!(state.has_active_work());
        assert_eq!(state.stop_all(), 1);
        assert!(!state.has_active_work());
        assert!(!state.shutting_down.load(Ordering::SeqCst));
        assert!(!context_path.exists());
        state.forget("already-gone");
        state.shutdown();
        assert!(state.shutting_down.load(Ordering::SeqCst));
        assert!(state.sessions.lock().unwrap().is_empty());
        assert!(state.workspace_claims.lock().unwrap().is_empty());
        assert!(
            !context_path.exists(),
            "shutdown removes the private context before process exit"
        );
    }
}
