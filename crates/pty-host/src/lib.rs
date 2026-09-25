//! PTY-Host (Spec 070): ein eigener Prozess besitzt die Agent-Terminals, damit
//! sie App-Neustarts überleben. Die App verbindet sich über TCP 127.0.0.1 mit
//! Token, öffnet Sitzungen, hängt sich an oder trennt sich; der Host puffert
//! die Ausgabe jeder Sitzung in einem Ringpuffer und spielt sie beim
//! Wiederanhängen zurück.
//!
//! Vertrag (zeilenweises JSON, eine Zeile = ein Objekt):
//!
//! - Erste Zeile des Clients: `{"op":"hello","token":…,"re":n}` →
//!   `{"re":n,"ok":true,"protocol":1,"version":…,"pid":…}`.
//! - Anfragen tragen `op` und `re` (Korrelations-Id); Antworten tragen `re`
//!   und `ok`, bei Fehlern `error`.
//! - Ereignisse ohne `re`: `{"ev":"out","id":…,"data":<base64>}` und
//!   `{"ev":"exit","id":…,"code":…}` — nur für Sitzungen, an die die
//!   Verbindung angehängt ist.
//! - `attach` liefert `replay` (base64 des Puffers) in der Antwort; Antwort und
//!   Sink-Registrierung geschehen unter einer Sperre, deshalb kommt keine
//!   Ausgabe doppelt oder in falscher Reihenfolge an.
//!
//! Ops: `hello`, `open`, `attach`, `detach`, `write`, `resize`, `kill`,
//! `list`, `shutdown`.

use std::collections::{HashMap, VecDeque};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::mpsc::{Receiver, Sender, channel};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use base64::Engine as _;
use base64::engine::general_purpose::STANDARD as B64;
use portable_pty::{ChildKiller, CommandBuilder, MasterPty, PtySize, native_pty_system};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};

/// Erhöht sich, wenn sich der Vertrag inkompatibel ändert. Die App vergleicht
/// beim `hello`; ein Host mit anderem Protokoll wird nur noch zum Auslaufen
/// bestehender Sitzungen benutzt.
pub const PROTOCOL_VERSION: u32 = 1;
pub const DEFAULT_BUFFER_BYTES: usize = 2 * 1024 * 1024;
pub const DEFAULT_IDLE_SECS: u64 = 60;
/// Beendete Sitzungen bleiben so lange abrufbar (Puffer, Exit-Code).
const EXITED_RETENTION: Duration = Duration::from_secs(10 * 60);
const REQUEST_TIMEOUT: Duration = Duration::from_secs(15);

/// Zustandsdatei `~/.speccify/pty-host.json`: wie die App den Host findet.
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct HostState {
    pub port: u16,
    pub token: String,
    pub pid: u32,
    pub protocol: u32,
    pub version: String,
}

pub fn state_path(home: &Path) -> PathBuf {
    home.join(".speccify").join("pty-host.json")
}

/// Schreibt die Zustandsdatei atomar (Temp + Rename), auf Unix mit 0600.
pub fn write_state(path: &Path, state: &HostState) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let tmp = path.with_extension(format!("tmp-{}", std::process::id()));
    {
        let mut file = std::fs::File::create(&tmp)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            file.set_permissions(std::fs::Permissions::from_mode(0o600))?;
        }
        file.write_all(serde_json::to_string_pretty(state)?.as_bytes())?;
        file.sync_all()?;
    }
    std::fs::rename(&tmp, path)
}

pub fn read_state(path: &Path) -> Option<HostState> {
    let bytes = std::fs::read(path).ok()?;
    serde_json::from_slice(&bytes).ok()
}

// --- Host ------------------------------------------------------------------

struct Sink {
    client: u64,
    out: Sender<String>,
}

/// Puffer und Abnehmer einer Sitzung hinter EINER Sperre: Anhängen (Replay +
/// Registrierung) und Ausgabe (Anhängen an den Puffer + Verteilen) sind so
/// gegeneinander atomar.
struct Stream {
    buffer: VecDeque<u8>,
    sinks: Vec<Sink>,
    exited: Option<i64>,
    exited_at: Option<Instant>,
}

struct Session {
    id: String,
    meta: Value,
    cwd: String,
    started_at: u64,
    writer: Mutex<Box<dyn Write + Send>>,
    master: Mutex<Box<dyn MasterPty + Send>>,
    killer: Mutex<Box<dyn ChildKiller + Send + Sync>>,
    stream: Mutex<Stream>,
}

impl Session {
    fn summary(&self) -> Value {
        let stream = self.stream.lock().unwrap();
        json!({
            "id": self.id,
            "meta": self.meta,
            "cwd": self.cwd,
            "started_at": self.started_at,
            "exited": stream.exited.is_some(),
            "exit_code": stream.exited,
            "buffered": stream.buffer.len(),
        })
    }
}

pub struct Host {
    token: String,
    version: String,
    limit: usize,
    sessions: Mutex<HashMap<String, Arc<Session>>>,
    clients: AtomicUsize,
    next_client: AtomicU64,
    activity: Mutex<Instant>,
    stopping: AtomicBool,
}

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn send_line(out: &Sender<String>, value: &Value) {
    let _ = out.send(value.to_string());
}

fn str_arg<'a>(req: &'a Value, key: &str) -> Result<&'a str, String> {
    req.get(key)
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty())
        .ok_or_else(|| format!("'{key}' fehlt"))
}

fn u16_arg(req: &Value, key: &str, default: u16) -> u16 {
    req.get(key)
        .and_then(Value::as_u64)
        .and_then(|v| u16::try_from(v).ok())
        .filter(|v| *v > 0)
        .unwrap_or(default)
}

impl Host {
    pub fn new(token: String, version: String, limit: usize) -> Arc<Self> {
        Arc::new(Self {
            token,
            version,
            limit: limit.max(64 * 1024),
            sessions: Mutex::new(HashMap::new()),
            clients: AtomicUsize::new(0),
            next_client: AtomicU64::new(1),
            activity: Mutex::new(Instant::now()),
            stopping: AtomicBool::new(false),
        })
    }

    fn touch(&self) {
        *self.activity.lock().unwrap() = Instant::now();
    }

    /// Anzahl laufender (nicht beendeter) Sitzungen.
    pub fn live_sessions(&self) -> usize {
        self.sessions
            .lock()
            .unwrap()
            .values()
            .filter(|s| s.stream.lock().unwrap().exited.is_none())
            .count()
    }

    pub fn connected_clients(&self) -> usize {
        self.clients.load(Ordering::SeqCst)
    }

    /// Ob der Host sich beenden darf: keine lebende Sitzung, kein Client und
    /// seit `idle` keine Aktivität.
    pub fn is_idle(&self, idle: Duration) -> bool {
        self.connected_clients() == 0
            && self.live_sessions() == 0
            && self.activity.lock().unwrap().elapsed() >= idle
    }

    /// Entfernt beendete Sitzungen nach der Aufbewahrungsfrist.
    pub fn purge_exited(&self) {
        let mut sessions = self.sessions.lock().unwrap();
        sessions.retain(|_, session| {
            let stream = session.stream.lock().unwrap();
            match stream.exited_at {
                Some(at) => at.elapsed() < EXITED_RETENTION,
                None => true,
            }
        });
    }

    /// Nimmt Verbindungen an, bis der Listener schließt oder `shutdown` kam.
    pub fn serve(self: &Arc<Self>, listener: TcpListener) {
        for stream in listener.incoming() {
            if self.stopping.load(Ordering::SeqCst) {
                break;
            }
            let Ok(stream) = stream else { continue };
            let host = self.clone();
            std::thread::spawn(move || host.handle_connection(stream));
        }
    }

    fn handle_connection(self: Arc<Self>, stream: TcpStream) {
        let client = self.next_client.fetch_add(1, Ordering::SeqCst);
        let Ok(mut write_half) = stream.try_clone() else {
            return;
        };
        let (out, inbox): (Sender<String>, Receiver<String>) = channel();
        let writer = std::thread::spawn(move || {
            for line in inbox {
                if write_half
                    .write_all(line.as_bytes())
                    .and_then(|_| write_half.write_all(b"\n"))
                    .is_err()
                {
                    break;
                }
            }
            let _ = write_half.shutdown(std::net::Shutdown::Both);
        });
        let reader = BufReader::new(stream);
        let mut authenticated = false;
        for line in reader.lines() {
            let Ok(line) = line else { break };
            if line.trim().is_empty() {
                continue;
            }
            let req: Value = match serde_json::from_str(&line) {
                Ok(v) => v,
                Err(error) => {
                    send_line(
                        &out,
                        &json!({"ok": false, "error": format!("Ungültiges JSON: {error}")}),
                    );
                    continue;
                }
            };
            let re = req.get("re").cloned().unwrap_or(Value::Null);
            let op = req.get("op").and_then(Value::as_str).unwrap_or("");
            if !authenticated {
                if op == "hello"
                    && req.get("token").and_then(Value::as_str) == Some(self.token.as_str())
                {
                    authenticated = true;
                    self.clients.fetch_add(1, Ordering::SeqCst);
                    self.touch();
                    send_line(
                        &out,
                        &json!({"re": re, "ok": true, "protocol": PROTOCOL_VERSION,
                                "version": self.version, "pid": std::process::id()}),
                    );
                    continue;
                }
                send_line(
                    &out,
                    &json!({"re": re, "ok": false, "error": "Nicht autorisiert"}),
                );
                break;
            }
            let mut response = match self.dispatch(client, &out, op, &req) {
                Ok(mut value) => {
                    value.insert("ok".into(), Value::Bool(true));
                    value
                }
                Err(error) => {
                    let mut value = Map::new();
                    value.insert("ok".into(), Value::Bool(false));
                    value.insert("error".into(), Value::String(error));
                    value
                }
            };
            // `attach` hat seine Antwort bereits unter der Sperre geschickt.
            if response.remove("__sent").is_none() {
                response.insert("re".into(), re);
                send_line(&out, &Value::Object(response));
            }
            if op == "shutdown" {
                break;
            }
        }
        if authenticated {
            self.detach_all(client);
            self.clients.fetch_sub(1, Ordering::SeqCst);
            self.touch();
        }
        drop(out);
        let _ = writer.join();
    }

    fn detach_all(&self, client: u64) {
        for session in self.sessions.lock().unwrap().values() {
            session
                .stream
                .lock()
                .unwrap()
                .sinks
                .retain(|sink| sink.client != client);
        }
    }

    fn session(&self, id: &str) -> Result<Arc<Session>, String> {
        self.sessions
            .lock()
            .unwrap()
            .get(id)
            .cloned()
            .ok_or_else(|| format!("Keine Sitzung: {id}"))
    }

    fn dispatch(
        self: &Arc<Self>,
        client: u64,
        out: &Sender<String>,
        op: &str,
        req: &Value,
    ) -> Result<Map<String, Value>, String> {
        let mut reply = Map::new();
        match op {
            "open" => {
                self.open(client, out, req)?;
            }
            "attach" => {
                let id = str_arg(req, "id")?;
                let session = self.session(id)?;
                let mut stream = session.stream.lock().unwrap();
                let replay: Vec<u8> = stream.buffer.iter().copied().collect();
                send_line(
                    out,
                    &json!({"re": req.get("re").cloned().unwrap_or(Value::Null), "ok": true,
                            "replay": B64.encode(&replay), "exited": stream.exited.is_some(),
                            "exit_code": stream.exited, "meta": session.meta, "cwd": session.cwd,
                            "started_at": session.started_at}),
                );
                stream.sinks.retain(|sink| sink.client != client);
                if stream.exited.is_none() {
                    stream.sinks.push(Sink {
                        client,
                        out: out.clone(),
                    });
                }
                reply.insert("__sent".into(), Value::Bool(true));
            }
            "detach" => {
                let id = str_arg(req, "id")?;
                let session = self.session(id)?;
                session
                    .stream
                    .lock()
                    .unwrap()
                    .sinks
                    .retain(|sink| sink.client != client);
            }
            "write" => {
                let id = str_arg(req, "id")?;
                let data = B64
                    .decode(str_arg(req, "data").unwrap_or(""))
                    .map_err(|e| format!("data: {e}"))?;
                let session = self.session(id)?;
                let mut writer = session.writer.lock().unwrap();
                writer
                    .write_all(&data)
                    .and_then(|_| writer.flush())
                    .map_err(|e| e.to_string())?;
            }
            "resize" => {
                let id = str_arg(req, "id")?;
                let session = self.session(id)?;
                session
                    .master
                    .lock()
                    .unwrap()
                    .resize(PtySize {
                        rows: u16_arg(req, "rows", 24),
                        cols: u16_arg(req, "cols", 80),
                        pixel_width: 0,
                        pixel_height: 0,
                    })
                    .map_err(|e| e.to_string())?;
            }
            "kill" => {
                let id = str_arg(req, "id")?;
                let removed = self.sessions.lock().unwrap().remove(id);
                let existed = removed.is_some();
                if let Some(session) = removed {
                    let _ = session.killer.lock().unwrap().kill();
                }
                self.touch();
                reply.insert("existed".into(), Value::Bool(existed));
            }
            "list" => {
                self.purge_exited();
                let sessions: Vec<Value> = self
                    .sessions
                    .lock()
                    .unwrap()
                    .values()
                    .map(|s| s.summary())
                    .collect();
                reply.insert("sessions".into(), Value::Array(sessions));
            }
            "shutdown" => {
                self.stopping.store(true, Ordering::SeqCst);
                let sessions: Vec<_> = self.sessions.lock().unwrap().drain().collect();
                for (_, session) in sessions {
                    let _ = session.killer.lock().unwrap().kill();
                }
            }
            other => return Err(format!("Unbekannte Operation: {other}")),
        }
        Ok(reply)
    }

    fn open(
        self: &Arc<Self>,
        client: u64,
        out: &Sender<String>,
        req: &Value,
    ) -> Result<(), String> {
        let id = str_arg(req, "id")?.to_owned();
        if self.sessions.lock().unwrap().contains_key(&id) {
            return Err(format!("Sitzung existiert schon: {id}"));
        }
        let program = str_arg(req, "program")?;
        let cwd = str_arg(req, "cwd")?.to_owned();
        let args: Vec<String> = req
            .get("args")
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(Value::as_str)
                    .map(str::to_owned)
                    .collect()
            })
            .unwrap_or_default();
        let pty = native_pty_system()
            .openpty(PtySize {
                rows: u16_arg(req, "rows", 24),
                cols: u16_arg(req, "cols", 80),
                pixel_width: 0,
                pixel_height: 0,
            })
            .map_err(|e| format!("PTY: {e}"))?;
        let mut command = CommandBuilder::new(program);
        command.args(&args);
        command.cwd(&cwd);
        if let Some(env) = req.get("env").and_then(Value::as_object) {
            for (key, value) in env {
                if let Some(value) = value.as_str() {
                    command.env(key, value);
                }
            }
        }
        let mut child = pty
            .slave
            .spawn_command(command)
            .map_err(|e| format!("{program}: {e}"))?;
        let killer = child.clone_killer();
        let mut reader = pty
            .master
            .try_clone_reader()
            .map_err(|e| format!("PTY-Reader: {e}"))?;
        let mut writer = pty
            .master
            .take_writer()
            .map_err(|e| format!("PTY-Writer: {e}"))?;
        if let Some(input) = req.get("input").and_then(Value::as_str) {
            let bytes = B64.decode(input).map_err(|e| format!("input: {e}"))?;
            if !bytes.is_empty() {
                writer
                    .write_all(&bytes)
                    .and_then(|_| writer.flush())
                    .map_err(|e| format!("Startkommando: {e}"))?;
            }
        }
        let session = Arc::new(Session {
            id: id.clone(),
            meta: req.get("meta").cloned().unwrap_or(Value::Null),
            cwd,
            started_at: now_secs(),
            writer: Mutex::new(writer),
            master: Mutex::new(pty.master),
            killer: Mutex::new(killer),
            stream: Mutex::new(Stream {
                buffer: VecDeque::new(),
                sinks: vec![Sink {
                    client,
                    out: out.clone(),
                }],
                exited: None,
                exited_at: None,
            }),
        });
        self.sessions
            .lock()
            .unwrap()
            .insert(id.clone(), session.clone());
        self.touch();
        let limit = self.limit;
        std::thread::spawn(move || {
            let mut buffer = [0u8; 8192];
            loop {
                match reader.read(&mut buffer) {
                    Ok(0) | Err(_) => break,
                    Ok(count) => {
                        let chunk = &buffer[..count];
                        let mut stream = session.stream.lock().unwrap();
                        stream.buffer.extend(chunk.iter().copied());
                        while stream.buffer.len() > limit {
                            stream.buffer.pop_front();
                        }
                        let event =
                            json!({"ev": "out", "id": session.id, "data": B64.encode(chunk)})
                                .to_string();
                        stream
                            .sinks
                            .retain(|sink| sink.out.send(event.clone()).is_ok());
                    }
                }
            }
            let code = child
                .wait()
                .ok()
                .map(|status| i64::from(status.exit_code()));
            let mut stream = session.stream.lock().unwrap();
            stream.exited = Some(code.unwrap_or(-1));
            stream.exited_at = Some(Instant::now());
            let event = json!({"ev": "exit", "id": session.id, "code": code}).to_string();
            for sink in stream.sinks.drain(..) {
                let _ = sink.out.send(event.clone());
            }
        });
        Ok(())
    }
}

/// Der Wächter-Thread des Host-Prozesses: räumt beendete Sitzungen auf und
/// beendet den Prozess, sobald er `idle` lang unbenutzt ist.
pub fn idle_watch(host: Arc<Host>, idle: Duration, on_exit: impl FnOnce() + Send + 'static) {
    std::thread::spawn(move || {
        loop {
            std::thread::sleep(Duration::from_secs(2));
            host.purge_exited();
            if host.stopping.load(Ordering::SeqCst) || host.is_idle(idle) {
                on_exit();
                std::process::exit(0);
            }
        }
    });
}

// --- Client ----------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Event {
    Out { id: String, data: Vec<u8> },
    Exit { id: String, code: Option<i64> },
}

#[derive(Debug, Clone)]
pub struct AttachReply {
    pub replay: Vec<u8>,
    pub exit_code: Option<i64>,
    pub meta: Value,
    pub cwd: String,
}

#[derive(Debug, Clone)]
pub struct Hello {
    pub protocol: u32,
    pub version: String,
    pub pid: u32,
}

pub struct Client {
    writer: Mutex<TcpStream>,
    pending: Arc<Mutex<HashMap<u64, Sender<Value>>>>,
    next: AtomicU64,
    alive: Arc<AtomicBool>,
    pub hello: Hello,
}

impl Drop for Client {
    /// Der Lese-Thread hält eine Kopie des Sockets; erst `shutdown` schließt
    /// die Verbindung für beide Seiten, sodass der Host den Client abmeldet
    /// und ohne Sitzungen auslaufen kann.
    fn drop(&mut self) {
        if let Ok(stream) = self.writer.lock() {
            let _ = stream.shutdown(std::net::Shutdown::Both);
        }
        self.alive.store(false, Ordering::SeqCst);
    }
}

impl Client {
    /// Verbindet sich, meldet sich mit dem Token an und liefert Ereignisse
    /// angehängter Sitzungen über `on_event` (aus einem Lese-Thread).
    pub fn connect(
        port: u16,
        token: &str,
        on_event: Box<dyn Fn(Event) + Send + 'static>,
    ) -> Result<Client, String> {
        let stream = TcpStream::connect_timeout(
            &std::net::SocketAddr::from(([127, 0, 0, 1], port)),
            Duration::from_secs(3),
        )
        .map_err(|e| format!("PTY-Host nicht erreichbar: {e}"))?;
        stream.set_nodelay(true).ok();
        let reader_half = stream.try_clone().map_err(|e| e.to_string())?;
        let pending: Arc<Mutex<HashMap<u64, Sender<Value>>>> = Arc::default();
        let alive = Arc::new(AtomicBool::new(true));
        let pending_for_reader = pending.clone();
        let alive_for_reader = alive.clone();
        std::thread::spawn(move || {
            let reader = BufReader::new(reader_half);
            for line in reader.lines() {
                let Ok(line) = line else { break };
                let Ok(value) = serde_json::from_str::<Value>(&line) else {
                    continue;
                };
                if let Some(re) = value.get("re").and_then(Value::as_u64) {
                    if let Some(sender) = pending_for_reader.lock().unwrap().remove(&re) {
                        let _ = sender.send(value);
                    }
                    continue;
                }
                match value.get("ev").and_then(Value::as_str) {
                    Some("out") => {
                        let id = value
                            .get("id")
                            .and_then(Value::as_str)
                            .unwrap_or("")
                            .to_owned();
                        let data = value
                            .get("data")
                            .and_then(Value::as_str)
                            .and_then(|d| B64.decode(d).ok())
                            .unwrap_or_default();
                        on_event(Event::Out { id, data });
                    }
                    Some("exit") => {
                        let id = value
                            .get("id")
                            .and_then(Value::as_str)
                            .unwrap_or("")
                            .to_owned();
                        on_event(Event::Exit {
                            id,
                            code: value.get("code").and_then(Value::as_i64),
                        });
                    }
                    _ => {}
                }
            }
            alive_for_reader.store(false, Ordering::SeqCst);
            pending_for_reader.lock().unwrap().clear();
        });
        let mut client = Client {
            writer: Mutex::new(stream),
            pending,
            next: AtomicU64::new(1),
            alive,
            hello: Hello {
                protocol: 0,
                version: String::new(),
                pid: 0,
            },
        };
        let reply = client.request("hello", json!({"token": token}))?;
        client.hello = Hello {
            protocol: reply.get("protocol").and_then(Value::as_u64).unwrap_or(0) as u32,
            version: reply
                .get("version")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_owned(),
            pid: reply.get("pid").and_then(Value::as_u64).unwrap_or(0) as u32,
        };
        Ok(client)
    }

    pub fn is_alive(&self) -> bool {
        self.alive.load(Ordering::SeqCst)
    }

    pub fn request(&self, op: &str, mut params: Value) -> Result<Value, String> {
        let re = self.next.fetch_add(1, Ordering::SeqCst);
        let (sender, receiver) = channel();
        self.pending.lock().unwrap().insert(re, sender);
        let object = params
            .as_object_mut()
            .ok_or("Parameter müssen ein Objekt sein")?;
        object.insert("op".into(), Value::String(op.to_owned()));
        object.insert("re".into(), Value::from(re));
        let line = format!("{params}\n");
        {
            let mut writer = self.writer.lock().map_err(|e| e.to_string())?;
            writer
                .write_all(line.as_bytes())
                .and_then(|_| writer.flush())
                .map_err(|e| format!("PTY-Host: Verbindung verloren ({e})"))?;
        }
        let reply = receiver.recv_timeout(REQUEST_TIMEOUT).map_err(|_| {
            self.pending.lock().unwrap().remove(&re);
            if self.is_alive() {
                "PTY-Host antwortet nicht".to_string()
            } else {
                "PTY-Host: Verbindung verloren".to_string()
            }
        })?;
        if reply.get("ok").and_then(Value::as_bool) == Some(true) {
            Ok(reply)
        } else {
            Err(reply
                .get("error")
                .and_then(Value::as_str)
                .unwrap_or("PTY-Host: unbekannter Fehler")
                .to_owned())
        }
    }

    /// Öffnet eine Sitzung; die Verbindung ist danach angehängt. `input` wird
    /// vor der ersten Ausgabe in die Sitzung geschrieben (Startkommando).
    #[allow(clippy::too_many_arguments)]
    pub fn open(
        &self,
        id: &str,
        program: &str,
        args: &[String],
        cwd: &str,
        env: &[(String, String)],
        cols: u16,
        rows: u16,
        input: &[u8],
        meta: Value,
    ) -> Result<(), String> {
        let env: Map<String, Value> = env
            .iter()
            .map(|(k, v)| (k.clone(), Value::String(v.clone())))
            .collect();
        self.request(
            "open",
            json!({"id": id, "program": program, "args": args, "cwd": cwd, "env": env,
                   "cols": cols, "rows": rows, "input": B64.encode(input), "meta": meta}),
        )
        .map(|_| ())
    }

    pub fn attach(&self, id: &str) -> Result<AttachReply, String> {
        let reply = self.request("attach", json!({"id": id}))?;
        Ok(AttachReply {
            replay: reply
                .get("replay")
                .and_then(Value::as_str)
                .and_then(|r| B64.decode(r).ok())
                .unwrap_or_default(),
            exit_code: reply.get("exit_code").and_then(Value::as_i64),
            meta: reply.get("meta").cloned().unwrap_or(Value::Null),
            cwd: reply
                .get("cwd")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_owned(),
        })
    }

    pub fn detach(&self, id: &str) -> Result<(), String> {
        self.request("detach", json!({"id": id})).map(|_| ())
    }

    pub fn write(&self, id: &str, data: &[u8]) -> Result<(), String> {
        self.request("write", json!({"id": id, "data": B64.encode(data)}))
            .map(|_| ())
    }

    pub fn resize(&self, id: &str, cols: u16, rows: u16) -> Result<(), String> {
        self.request("resize", json!({"id": id, "cols": cols, "rows": rows}))
            .map(|_| ())
    }

    pub fn kill(&self, id: &str) -> Result<bool, String> {
        self.request("kill", json!({"id": id})).map(|reply| {
            reply
                .get("existed")
                .and_then(Value::as_bool)
                .unwrap_or(false)
        })
    }

    pub fn list(&self) -> Result<Vec<Value>, String> {
        self.request("list", json!({})).map(|reply| {
            reply
                .get("sessions")
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default()
        })
    }

    pub fn shutdown(&self) -> Result<(), String> {
        self.request("shutdown", json!({})).map(|_| ())
    }
}

/// Startet einen Host im aktuellen Prozess (Tests, eingebetteter Betrieb) und
/// liefert Port und Host.
pub fn spawn_in_process(token: &str, limit: usize) -> std::io::Result<(u16, Arc<Host>)> {
    let listener = TcpListener::bind(("127.0.0.1", 0))?;
    let port = listener.local_addr()?.port();
    let host = Host::new(
        token.to_owned(),
        env!("CARGO_PKG_VERSION").to_owned(),
        limit,
    );
    let serving = host.clone();
    std::thread::spawn(move || serving.serve(listener));
    Ok((port, host))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn state_file_roundtrip_is_private() {
        let dir =
            std::env::temp_dir().join(format!("speccify-pty-host-state-{}", std::process::id()));
        let path = dir.join("pty-host.json");
        let state = HostState {
            port: 4242,
            token: "t".into(),
            pid: 7,
            protocol: PROTOCOL_VERSION,
            version: "x".into(),
        };
        write_state(&path, &state).unwrap();
        assert_eq!(read_state(&path), Some(state));
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                std::fs::metadata(&path).unwrap().permissions().mode() & 0o777,
                0o600
            );
        }
        assert!(read_state(&dir.join("missing.json")).is_none());
        let _ = std::fs::remove_dir_all(dir);
    }

    #[test]
    fn hello_requires_the_token() {
        let (port, _host) = spawn_in_process("secret", DEFAULT_BUFFER_BYTES).unwrap();
        let wrong = Client::connect(port, "nope", Box::new(|_| {}));
        assert!(wrong.is_err());
        let right = Client::connect(port, "secret", Box::new(|_| {})).unwrap();
        assert_eq!(right.hello.protocol, PROTOCOL_VERSION);
        assert!(right.list().unwrap().is_empty());
        assert_eq!(_host.connected_clients(), 1);
        drop(right);
        // Dropping the client closes the socket for the reader clone too, so the
        // host sees the disconnect and can become idle.
        let deadline = Instant::now() + Duration::from_secs(3);
        while _host.connected_clients() != 0 && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(20));
        }
        assert_eq!(_host.connected_clients(), 0);
        assert!(_host.is_idle(Duration::ZERO));
    }
}
