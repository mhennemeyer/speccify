//! Anbindung des PTY-Hosts (Spec 070): findet oder startet den losgelösten
//! Host-Prozess `speccify-pty-host`, hält genau eine Verbindung je App und
//! reicht dessen Ereignisse als dieselben `term-out`/`term-exit`-Events ans
//! Frontend, die auch der In-Prozess-Reader sendet.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use serde_json::Value;
use speccify_pty_host::{
    read_state, state_path, AttachReply, Client, Event, HostState, PROTOCOL_VERSION,
};
use tauri::{AppHandle, Emitter, Manager};

use crate::agent_session::Utf8Chunker;
use crate::terminal::{TermExit, TermOut, Terminals};

/// Zustand des Ereignis-Dispatchers: UTF-8-Zusammensetzung je Sitzung und
/// zurückgehaltene Ausgabe, während ein `attach` seinen Puffer zurückspielt —
/// damit Replay und lebende Ausgabe in der richtigen Reihenfolge ankommen.
#[derive(Default)]
struct Dispatch {
    chunkers: HashMap<String, Utf8Chunker>,
    held: HashMap<String, Vec<Vec<u8>>>,
}

/// Die Verbindung zum Host; `None`, solange keine gebraucht wurde.
#[derive(Default)]
pub struct HostLink {
    client: Mutex<Option<Arc<Client>>>,
    dispatch: Arc<Mutex<Dispatch>>,
}

/// Wo Workspace-Kontextdateien gehosteter Sitzungen liegen: sie müssen den
/// App-Prozess überleben (D4).
pub fn context_dir() -> Result<PathBuf, String> {
    let dir = crate::settings::home_dir()?
        .join(".speccify")
        .join("pty-host");
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir)
}

fn host_binary() -> Result<PathBuf, String> {
    let (path, _) = crate::sidecar::resolve("speccify-pty-host");
    path.ok_or_else(|| {
        "speccify-pty-host nicht gefunden (Sidecar fehlt im Bundle und im PATH).".to_string()
    })
}

fn state_file() -> Result<PathBuf, String> {
    Ok(state_path(&crate::settings::home_dir()?))
}

/// Startet den Host losgelöst: eigene Sitzung/Prozessgruppe, keine geerbten
/// Ein-/Ausgaben — so überlebt er das App-Ende.
fn spawn_host(state: &PathBuf) -> Result<(), String> {
    let binary = host_binary()?;
    let log = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(context_dir()?.join("pty-host.log"))
        .map_err(|e| e.to_string())?;
    let mut command = std::process::Command::new(&binary);
    command
        .arg("--state")
        .arg(state)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(log);
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        // SAFETY: setsid ist async-signal-sicher und hat keine Vorbedingungen.
        unsafe {
            command.pre_exec(|| {
                libc::setsid();
                Ok(())
            });
        }
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const DETACHED_PROCESS: u32 = 0x0000_0008;
        const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
        command.creation_flags(DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP);
    }
    let mut child = command
        .spawn()
        .map_err(|e| format!("{}: {e}", binary.display()))?;
    // Der Host läuft weiter; nur den Zombie-Eintrag nicht liegen lassen.
    std::thread::spawn(move || {
        let _ = child.wait();
    });
    Ok(())
}

fn emit_out(app: &AppHandle, dispatch: &mut Dispatch, id: &str, data: &[u8]) {
    let text = dispatch
        .chunkers
        .entry(id.to_owned())
        .or_default()
        .push(data);
    if !text.is_empty() {
        let _ = app.emit(
            "term-out",
            TermOut {
                id: id.to_owned(),
                data: text,
            },
        );
    }
}

fn connect(
    app: &AppHandle,
    state: &HostState,
    dispatch: Arc<Mutex<Dispatch>>,
) -> Result<Arc<Client>, String> {
    let app = app.clone();
    let client = Client::connect(
        state.port,
        &state.token,
        Box::new(move |event| match event {
            Event::Out { id, data } => {
                let mut dispatch = dispatch.lock().unwrap();
                if let Some(held) = dispatch.held.get_mut(&id) {
                    held.push(data);
                    return;
                }
                emit_out(&app, &mut dispatch, &id, &data);
            }
            Event::Exit { id, .. } => {
                let mut dispatch = dispatch.lock().unwrap();
                dispatch.held.remove(&id);
                let tail = dispatch
                    .chunkers
                    .remove(&id)
                    .map(|mut chunker| chunker.finish())
                    .unwrap_or_default();
                if !tail.is_empty() {
                    let _ = app.emit(
                        "term-out",
                        TermOut {
                            id: id.clone(),
                            data: tail,
                        },
                    );
                }
                app.state::<Terminals>().forget(&id);
                let _ = app.emit("term-exit", TermExit { id });
            }
        }),
    )?;
    if client.hello.protocol != PROTOCOL_VERSION {
        return Err(format!(
            "PTY-Host spricht Protokoll {}, die App erwartet {}.",
            client.hello.protocol, PROTOCOL_VERSION
        ));
    }
    Ok(Arc::new(client))
}

impl HostLink {
    /// Verbindung zum Host: die bestehende, wenn sie lebt; sonst der laufende
    /// Host aus der Zustandsdatei; sonst ein frisch gestarteter Host.
    pub fn client(&self, app: &AppHandle) -> Result<Arc<Client>, String> {
        let mut slot = self.client.lock().map_err(|e| e.to_string())?;
        if let Some(client) = slot.as_ref() {
            if client.is_alive() {
                return Ok(client.clone());
            }
        }
        let state_file = state_file()?;
        let previous = read_state(&state_file);
        if let Some(state) = previous.as_ref() {
            if let Ok(client) = connect(app, state, self.dispatch.clone()) {
                *slot = Some(client.clone());
                return Ok(client);
            }
        }
        // Kein erreichbarer Host: alte Zustandsdatei ignorieren, neu starten.
        spawn_host(&state_file)?;
        let deadline = Instant::now() + Duration::from_secs(8);
        while Instant::now() < deadline {
            if let Some(state) = read_state(&state_file) {
                if previous.as_ref().map(|p| p.pid) != Some(state.pid) {
                    if let Ok(client) = connect(app, &state, self.dispatch.clone()) {
                        *slot = Some(client.clone());
                        return Ok(client);
                    }
                }
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        Err("PTY-Host ist nicht gestartet (keine Zustandsdatei innerhalb von 8 s).".into())
    }

    /// Trennt die Verbindung, wenn die App keine gehostete Sitzung mehr hat,
    /// damit der Host ohne Sitzungen und Clients auslaufen kann.
    pub fn disconnect(&self) {
        if let Ok(mut slot) = self.client.lock() {
            slot.take();
        }
    }

    /// Nur eine bestehende, lebende Verbindung — startet nichts.
    pub fn existing(&self) -> Option<Arc<Client>> {
        self.client
            .lock()
            .ok()
            .and_then(|slot| slot.clone())
            .filter(|client| client.is_alive())
    }

    /// Lebende Host-Sitzungen (Metadaten), ohne einen Host zu starten, wenn
    /// keiner läuft.
    pub fn live_sessions(&self, app: &AppHandle) -> Vec<Value> {
        let Ok(state_file) = state_file() else {
            return Vec::new();
        };
        if self.existing().is_none() && read_state(&state_file).is_none() {
            return Vec::new();
        }
        match self.client(app) {
            Ok(client) => client
                .list()
                .unwrap_or_default()
                .into_iter()
                .filter(|s| s.get("exited").and_then(Value::as_bool) == Some(false))
                .collect(),
            Err(_) => Vec::new(),
        }
    }

    /// Hängt sich an eine Sitzung: der Puffer geht als `term-out` raus, bevor
    /// lebende Ausgabe dieser Sitzung weitergereicht wird (zurückgehalten,
    /// solange das Replay läuft).
    pub fn attach(
        &self,
        app: &AppHandle,
        client: &Client,
        id: &str,
    ) -> Result<AttachReply, String> {
        self.dispatch
            .lock()
            .unwrap()
            .held
            .insert(id.to_owned(), Vec::new());
        let result = client.attach(id);
        let mut dispatch = self.dispatch.lock().unwrap();
        let held = dispatch.held.remove(id).unwrap_or_default();
        let reply = result?;
        dispatch
            .chunkers
            .insert(id.to_owned(), Utf8Chunker::default());
        emit_out(app, &mut dispatch, id, &reply.replay);
        for chunk in held {
            emit_out(app, &mut dispatch, id, &chunk);
        }
        Ok(reply)
    }
}
