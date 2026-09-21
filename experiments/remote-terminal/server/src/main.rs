//! Spec 062 spike: PTY sessions owned by the server, attached to from a browser.
//!
//! Not product code. It answers whether a terminal that today lives inside the
//! Tauri app (`apps/desktop/src-tauri/src/terminal.rs`) can live in a container
//! and survive its viewer: the server hands out the session id, keeps the PTY
//! alive without a connection and replays the screen on attach.

use std::collections::{HashMap, VecDeque};
use std::io::{Read, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Path, Query, State};
use axum::http::{header, HeaderMap, StatusCode};
use axum::response::{Html, IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router};
use futures_util::{SinkExt, StreamExt};
use portable_pty::{native_pty_system, ChildKiller, CommandBuilder, MasterPty, PtySize};
use serde::{Deserialize, Serialize};
use tokio::sync::broadcast;

const INDEX_HTML: &str = include_str!("../../web/index.html");

struct Replay {
    /// Raw PTY bytes, oldest dropped first.
    ring: VecDeque<u8>,
    ring_cap: usize,
    dropped: u64,
    /// Headless terminal fed with the same bytes; yields the screen state.
    parser: vt100::Parser,
}

impl Replay {
    fn push(&mut self, bytes: &[u8]) {
        self.parser.process(bytes);
        self.ring.extend(bytes);
        while self.ring.len() > self.ring_cap {
            self.ring.pop_front();
            self.dropped += 1;
        }
    }

    fn snapshot(&self, mode: ReplayMode) -> Vec<u8> {
        match mode {
            ReplayMode::None => Vec::new(),
            ReplayMode::Ring => self.ring.iter().copied().collect(),
            ReplayMode::Vt => {
                let screen = self.parser.screen();
                let mut out = Vec::new();
                // `state_formatted` paints the visible grid only; without this the
                // client would draw a full-screen program onto its normal buffer.
                if screen.alternate_screen() {
                    out.extend_from_slice(b"\x1b[?1049h");
                }
                out.extend_from_slice(&screen.state_formatted());
                out
            }
        }
    }
}

struct Session {
    id: String,
    command: String,
    writer: Mutex<Box<dyn Write + Send>>,
    master: Mutex<Box<dyn MasterPty + Send>>,
    killer: Mutex<Box<dyn ChildKiller + Send + Sync>>,
    replay: Mutex<Replay>,
    size: Mutex<(u16, u16)>,
    tx: broadcast::Sender<Vec<u8>>,
    exited: AtomicBool,
}

#[derive(Clone)]
struct App {
    token: Arc<String>,
    ring_cap: usize,
    sessions: Arc<Mutex<HashMap<String, Arc<Session>>>>,
}

#[derive(Clone, Copy, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
enum ReplayMode {
    #[default]
    Ring,
    Vt,
    None,
}

#[derive(Deserialize)]
struct NewSession {
    #[serde(default = "default_cols")]
    cols: u16,
    #[serde(default = "default_rows")]
    rows: u16,
    /// Typed into the login shell, like `terminal.rs` does with the host launch.
    #[serde(default)]
    command: String,
}

fn default_cols() -> u16 {
    120
}
fn default_rows() -> u16 {
    32
}

#[derive(Serialize)]
struct SessionInfo {
    id: String,
    command: String,
    exited: bool,
    viewers: usize,
    ring_bytes: usize,
    ring_dropped: u64,
}

#[derive(Deserialize)]
struct WsQuery {
    #[serde(default)]
    token: String,
    #[serde(default)]
    replay: ReplayMode,
}

#[derive(Deserialize)]
#[serde(tag = "type", rename_all = "lowercase")]
enum ClientMsg {
    Input { data: String },
    Resize { cols: u16, rows: u16 },
}

fn authorized(headers: &HeaderMap, token: &str) -> bool {
    headers
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "))
        .is_some_and(|given| given == token)
}

fn info(session: &Session) -> SessionInfo {
    let replay = session.replay.lock().unwrap();
    SessionInfo {
        id: session.id.clone(),
        command: session.command.clone(),
        exited: session.exited.load(Ordering::SeqCst),
        viewers: session.tx.receiver_count(),
        ring_bytes: replay.ring.len(),
        ring_dropped: replay.dropped,
    }
}

fn spawn_session(app: &App, req: NewSession) -> Result<Arc<Session>, String> {
    let pair = native_pty_system()
        .openpty(PtySize {
            rows: req.rows,
            cols: req.cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|e| e.to_string())?;

    let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/bash".into());
    let mut cmd = CommandBuilder::new(shell);
    cmd.arg("-l");
    cmd.env("TERM", "xterm-256color");
    cmd.env("COLORTERM", "truecolor");
    if let Ok(dir) = std::env::var("SPIKE_WORKDIR") {
        cmd.cwd(dir);
    }
    let mut child = pair.slave.spawn_command(cmd).map_err(|e| e.to_string())?;
    drop(pair.slave);

    let mut reader = pair.master.try_clone_reader().map_err(|e| e.to_string())?;
    let mut writer = pair.master.take_writer().map_err(|e| e.to_string())?;
    if !req.command.trim().is_empty() {
        writer
            .write_all(format!("{}\r", req.command.trim()).as_bytes())
            .map_err(|e| e.to_string())?;
    }

    let (tx, _) = broadcast::channel(1024);
    let session = Arc::new(Session {
        id: format!("term-{}", uuid::Uuid::new_v4()),
        command: req.command,
        writer: Mutex::new(writer),
        master: Mutex::new(pair.master),
        killer: Mutex::new(child.clone_killer()),
        replay: Mutex::new(Replay {
            ring: VecDeque::new(),
            ring_cap: app.ring_cap,
            dropped: 0,
            parser: vt100::Parser::new(req.rows, req.cols, 0),
        }),
        size: Mutex::new((req.cols, req.rows)),
        tx,
        exited: AtomicBool::new(false),
    });

    let for_reader = session.clone();
    std::thread::spawn(move || {
        let mut buf = [0u8; 8192];
        loop {
            match reader.read(&mut buf) {
                Ok(0) | Err(_) => break,
                Ok(n) => {
                    // Buffer and broadcast under one lock so an attaching viewer
                    // gets every byte exactly once: snapshot, then live stream.
                    let mut replay = for_reader.replay.lock().unwrap();
                    replay.push(&buf[..n]);
                    let _ = for_reader.tx.send(buf[..n].to_vec());
                }
            }
        }
    });

    let for_wait = session.clone();
    std::thread::spawn(move || {
        let _ = child.wait();
        for_wait.exited.store(true, Ordering::SeqCst);
        let _ = for_wait
            .tx
            .send(b"\r\n\x1b[2m[session ended]\x1b[0m\r\n".to_vec());
    });

    app.sessions
        .lock()
        .unwrap()
        .insert(session.id.clone(), session.clone());
    Ok(session)
}

async fn list_sessions(State(app): State<App>, headers: HeaderMap) -> Response {
    if !authorized(&headers, &app.token) {
        return StatusCode::UNAUTHORIZED.into_response();
    }
    let sessions = app.sessions.lock().unwrap();
    let mut list: Vec<SessionInfo> = sessions.values().map(|s| info(s)).collect();
    list.sort_by(|a, b| a.id.cmp(&b.id));
    Json(list).into_response()
}

async fn create_session(
    State(app): State<App>,
    headers: HeaderMap,
    Json(req): Json<NewSession>,
) -> Response {
    if !authorized(&headers, &app.token) {
        return StatusCode::UNAUTHORIZED.into_response();
    }
    match spawn_session(&app, req) {
        Ok(session) => Json(info(&session)).into_response(),
        Err(e) => (StatusCode::INTERNAL_SERVER_ERROR, e).into_response(),
    }
}

async fn kill_session(
    State(app): State<App>,
    headers: HeaderMap,
    Path(id): Path<String>,
) -> Response {
    if !authorized(&headers, &app.token) {
        return StatusCode::UNAUTHORIZED.into_response();
    }
    match app.sessions.lock().unwrap().remove(&id) {
        Some(session) => {
            let _ = session.killer.lock().unwrap().kill();
            StatusCode::NO_CONTENT.into_response()
        }
        None => StatusCode::NOT_FOUND.into_response(),
    }
}

/// Question 6 of the spec: what does the replay buffer hold after a login?
async fn dump_buffer(
    State(app): State<App>,
    headers: HeaderMap,
    Path(id): Path<String>,
) -> Response {
    if !authorized(&headers, &app.token) {
        return StatusCode::UNAUTHORIZED.into_response();
    }
    let Some(session) = app.sessions.lock().unwrap().get(&id).cloned() else {
        return StatusCode::NOT_FOUND.into_response();
    };
    let bytes = session.replay.lock().unwrap().snapshot(ReplayMode::Ring);
    (
        [(header::CONTENT_TYPE, "text/plain; charset=utf-8")],
        String::from_utf8_lossy(&bytes).into_owned(),
    )
        .into_response()
}

async fn attach(
    State(app): State<App>,
    Path(id): Path<String>,
    Query(query): Query<WsQuery>,
    upgrade: WebSocketUpgrade,
) -> Response {
    // Checked before the upgrade: a wrong token never reaches a session.
    if query.token != *app.token {
        return StatusCode::UNAUTHORIZED.into_response();
    }
    let Some(session) = app.sessions.lock().unwrap().get(&id).cloned() else {
        return StatusCode::NOT_FOUND.into_response();
    };
    upgrade.on_upgrade(move |socket| serve_viewer(socket, session, query.replay))
}

async fn serve_viewer(socket: WebSocket, session: Arc<Session>, mode: ReplayMode) {
    let (mut sink, mut stream) = socket.split();

    let (snapshot, mut rx) = {
        let replay = session.replay.lock().unwrap();
        (replay.snapshot(mode), session.tx.subscribe())
    };
    // Announce the replay so the client can discard what its terminal answers
    // to queries inside it (DA, DSR, colour requests): those answers were given
    // once already and would reach the running program as typed input.
    let announce = format!(r#"{{"type":"replay","bytes":{}}}"#, snapshot.len());
    if sink.send(Message::Text(announce.into())).await.is_err() {
        return;
    }
    if !snapshot.is_empty() && sink.send(Message::Binary(snapshot.into())).await.is_err() {
        return;
    }

    let outbound = tokio::spawn(async move {
        loop {
            match rx.recv().await {
                Ok(bytes) => {
                    if sink.send(Message::Binary(bytes.into())).await.is_err() {
                        break;
                    }
                }
                // A viewer that fell behind loses bytes; it should re-attach.
                Err(broadcast::error::RecvError::Lagged(_)) => break,
                Err(broadcast::error::RecvError::Closed) => break,
            }
        }
    });

    while let Some(Ok(message)) = stream.next().await {
        let Message::Text(text) = message else {
            continue;
        };
        match serde_json::from_str::<ClientMsg>(text.as_str()) {
            Ok(ClientMsg::Input { data }) => {
                let mut writer = session.writer.lock().unwrap();
                let _ = writer.write_all(data.as_bytes());
                let _ = writer.flush();
            }
            Ok(ClientMsg::Resize { cols, rows }) => {
                // Every attach reports its size; only a real change may reach the
                // program as SIGWINCH.
                let mut size = session.size.lock().unwrap();
                if *size == (cols, rows) || cols == 0 || rows == 0 {
                    continue;
                }
                *size = (cols, rows);
                eprintln!("{} resize {cols}x{rows}", session.id);
                let _ = session.master.lock().unwrap().resize(PtySize {
                    rows,
                    cols,
                    pixel_width: 0,
                    pixel_height: 0,
                });
                session.replay.lock().unwrap().parser.set_size(rows, cols);
            }
            Err(_) => {}
        }
    }
    // The viewer is gone; the PTY deliberately is not.
    outbound.abort();
}

#[tokio::main]
async fn main() {
    let token = std::env::var("SPIKE_TOKEN").unwrap_or_default();
    if token.len() < 16 {
        eprintln!("SPIKE_TOKEN must be set (at least 16 characters).");
        std::process::exit(2);
    }
    let ring_cap = std::env::var("SPIKE_RING_BYTES")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(1024 * 1024);
    let bind = std::env::var("SPIKE_BIND").unwrap_or_else(|_| "0.0.0.0:8791".into());

    let app = App {
        token: Arc::new(token),
        ring_cap,
        sessions: Arc::default(),
    };
    let router = Router::new()
        .route("/", get(|| async { Html(INDEX_HTML) }))
        .route("/healthz", get(|| async { "ok" }))
        .route("/api/sessions", get(list_sessions).post(create_session))
        .route("/api/sessions/{id}", axum::routing::delete(kill_session))
        .route("/api/sessions/{id}/buffer", get(dump_buffer))
        .route("/ws/{id}", get(attach))
        .with_state(app);

    let listener = tokio::net::TcpListener::bind(&bind).await.expect("bind");
    eprintln!("remote-terminal-spike listening on {bind} (ring {ring_cap} bytes)");
    axum::serve(listener, router).await.expect("serve");
}
