//! QA-Brücke (Spec 039): ein Loopback-HTTP-Endpunkt im App-Prozess, über den
//! ein Prüfwerkzeug (speccify-qa) die laufende App steuert — Fenster
//! auflisten, JavaScript in einem Fenster ausführen, Tauri-Befehle aufrufen,
//! Screenshot. Nur aktiv mit `--qa-bridge=<port>` oder
//! `SPECCIFY_QA_BRIDGE=<port>`; jede Anfrage braucht das Bearer-Token.
//! Port, Token und PID stehen in `<tmp>/speccify-qa-bridge.json` (0600).
//!
//! Warum kein WebDriver: Auf macOS gibt es keinen für Tauri, und der
//! WKWebView spricht kein CDP. `WebviewWindow::eval` liefert kein Ergebnis,
//! darum ruft das eingespeiste Skript den Befehl `qa_eval_result` mit einer
//! Kennung zurück, auf die der HTTP-Thread wartet.

use std::collections::HashMap;
use std::io::Read;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};

use serde_json::{json, Value};
use tauri::{AppHandle, Manager, State, WebviewWindow};

#[derive(Clone, Debug, PartialEq)]
pub struct Config {
    pub port: u16,
    pub token: String,
}

fn parse_port(value: &str, source: &str) -> Result<u16, String> {
    value
        .parse::<u16>()
        .ok()
        .filter(|port| *port > 0)
        .ok_or_else(|| format!("Ungültiger {source}: erwartet 1–65535"))
}

/// Konfiguration aus Argumenten und Umgebung; `None` = Brücke aus.
pub fn config_from(
    args: impl Iterator<Item = String>,
    env_port: Option<String>,
    env_token: Option<String>,
) -> Result<Option<Config>, String> {
    let mut port = None;
    for arg in args {
        if let Some(value) = arg.strip_prefix("--qa-bridge=") {
            port = Some(parse_port(value, "--qa-bridge")?);
        }
    }
    if port.is_none() {
        if let Some(value) = env_port.filter(|v| !v.trim().is_empty()) {
            port = Some(parse_port(value.trim(), "SPECCIFY_QA_BRIDGE")?);
        }
    }
    let Some(port) = port else {
        return Ok(None);
    };
    let token = env_token
        .filter(|t| !t.trim().is_empty())
        .unwrap_or_else(|| uuid::Uuid::new_v4().simple().to_string());
    Ok(Some(Config { port, token }))
}

pub fn configured() -> Result<Option<Config>, String> {
    config_from(
        std::env::args().skip(1),
        std::env::var("SPECCIFY_QA_BRIDGE").ok(),
        std::env::var("SPECCIFY_QA_TOKEN").ok(),
    )
}

pub fn discovery_path() -> std::path::PathBuf {
    std::env::temp_dir().join("speccify-qa-bridge.json")
}

fn write_discovery(config: &Config, desktop_ui_port: u16) -> std::io::Result<()> {
    let path = discovery_path();
    let payload = json!({
        "url": format!("http://127.0.0.1:{}", config.port),
        "port": config.port,
        "token": config.token,
        "pid": std::process::id(),
        "desktop_ui": format!("http://127.0.0.1:{desktop_ui_port}"),
    });
    std::fs::write(&path, serde_json::to_string_pretty(&payload).unwrap())?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600))?;
    }
    Ok(())
}

// --- Eval-Register -----------------------------------------------------------

#[derive(Default)]
struct Inner {
    pending: Mutex<HashMap<String, Option<Value>>>,
    condvar: Condvar,
    counter: AtomicU64,
}

#[derive(Clone, Default)]
pub struct EvalRegistry(Arc<Inner>);

impl EvalRegistry {
    fn begin(&self) -> String {
        let id = format!("qa-{}", self.0.counter.fetch_add(1, Ordering::SeqCst) + 1);
        self.0.pending.lock().unwrap().insert(id.clone(), None);
        id
    }

    fn complete(&self, id: &str, result: Value) -> bool {
        let mut pending = self.0.pending.lock().unwrap();
        match pending.get_mut(id) {
            Some(slot) => {
                *slot = Some(result);
                self.0.condvar.notify_all();
                true
            }
            None => false,
        }
    }

    fn wait(&self, id: &str, timeout: Duration) -> Option<Value> {
        let deadline = Instant::now() + timeout;
        let mut pending = self.0.pending.lock().unwrap();
        loop {
            if let Some(Some(_)) = pending.get(id) {
                return pending.remove(id).flatten();
            }
            let now = Instant::now();
            if now >= deadline {
                pending.remove(id);
                return None;
            }
            let (guard, _) = self
                .0
                .condvar
                .wait_timeout(pending, deadline - now)
                .unwrap();
            pending = guard;
        }
    }
}

/// Rückkanal des eingespeisten Skripts.
#[tauri::command]
pub fn qa_eval_result(
    registry: State<EvalRegistry>,
    id: String,
    result: Value,
) -> Result<(), String> {
    if registry.complete(&id, result) {
        Ok(())
    } else {
        Err(format!("Unbekannte QA-Auswertung {id}"))
    }
}

/// Das Skript ist ein Funktionsrumpf (`return …`, `await` erlaubt); das
/// Ergebnis muss JSON-fähig sein, sonst kommt seine String-Form.
pub fn wrap_script(id: &str, body: &str) -> String {
    let id_json = serde_json::to_string(id).unwrap();
    format!(
        "(function(){{var __id={id_json};\
function __send(r){{try{{window.__TAURI_INTERNALS__.invoke(\"qa_eval_result\",{{id:__id,result:r}});}}catch(e){{}}}}\
Promise.resolve().then(function(){{return (async function(){{\n{body}\n}})();}})\
.then(function(v){{var c;try{{c=(v===undefined)?null:JSON.parse(JSON.stringify(v));}}catch(e){{c=String(v);}}__send({{ok:true,value:c}});}},\
function(e){{__send({{ok:false,error:String(e&&e.stack||e)}});}});}})();"
    )
}

// --- Hauptthread ----------------------------------------------------------------

/// Fensterabfragen (Titel, Position, Fokus) und `eval` gehören auf den
/// Hauptthread. Ein blockierter Hauptthread (Systemdialog, z. B. die
/// macOS-Dateizugriffsfrage) darf die Brücke nicht einfrieren: nach dem
/// Timeout kommt eine klare Meldung statt einer hängenden Anfrage.
const MAIN_THREAD_TIMEOUT: Duration = Duration::from_secs(5);

fn on_main<T: Send + 'static>(
    app: &AppHandle,
    work: impl FnOnce() -> T + Send + 'static,
) -> Result<T, String> {
    let (sender, receiver) = std::sync::mpsc::channel();
    app.run_on_main_thread(move || {
        let _ = sender.send(work());
    })
    .map_err(|error| error.to_string())?;
    receiver
        .recv_timeout(MAIN_THREAD_TIMEOUT)
        .map_err(|_| "Der Hauptthread der App antwortet nicht (offener Systemdialog?)".to_string())
}

// --- HTTP ---------------------------------------------------------------------

const DEFAULT_TIMEOUT_MS: u64 = 10_000;
const MAX_TIMEOUT_MS: u64 = 120_000;
const MAX_BODY: usize = 1024 * 1024;

pub fn serve(
    app: AppHandle,
    registry: EvalRegistry,
    config: Config,
    desktop_ui_port: u16,
) -> Result<(), String> {
    let http = tiny_http::Server::http(("127.0.0.1", config.port))
        .map_err(|e| format!("QA-Brücke auf Port {}: {e}", config.port))?;
    if let Err(error) = write_discovery(&config, desktop_ui_port) {
        eprintln!("QA-Brücke: Discovery-Datei nicht geschrieben: {error}");
    }
    eprintln!(
        "QA-Brücke aktiv auf http://127.0.0.1:{} (Token in {})",
        config.port,
        discovery_path().display()
    );
    let http = Arc::new(http);
    let token = Arc::new(config.token);
    loop {
        let request = match http.recv() {
            Ok(request) => request,
            Err(_) => continue,
        };
        let app = app.clone();
        let registry = registry.clone();
        let token = Arc::clone(&token);
        std::thread::spawn(move || {
            let _ = handle(&app, &registry, &token, request);
        });
    }
}

struct Reply {
    status: u16,
    body: Vec<u8>,
    content_type: &'static str,
}

fn json_reply(status: u16, value: Value) -> Reply {
    Reply {
        status,
        body: value.to_string().into_bytes(),
        content_type: "application/json",
    }
}

fn error_reply(status: u16, message: impl Into<String>) -> Reply {
    json_reply(status, json!({ "ok": false, "error": message.into() }))
}

fn header<'a>(request: &'a tiny_http::Request, name: &'static str) -> Option<&'a str> {
    request
        .headers()
        .iter()
        .find(|h| h.field.equiv(name))
        .map(|h| h.value.as_str())
}

/// Bearer-Token und Loopback-Host; alles andere wird abgelehnt.
pub fn authorize(
    host: Option<&str>,
    authorization: Option<&str>,
    token: &str,
) -> Result<(), (u16, &'static str)> {
    let host = host.unwrap_or("");
    let host_name = host.rsplit_once(':').map(|(h, _)| h).unwrap_or(host);
    if !matches!(host_name, "127.0.0.1" | "localhost" | "[::1]") {
        return Err((403, "Nur Loopback-Anfragen"));
    }
    match authorization.and_then(|a| a.strip_prefix("Bearer ")) {
        Some(given) if given.trim() == token => Ok(()),
        _ => Err((401, "Token fehlt oder ist falsch")),
    }
}

fn handle(
    app: &AppHandle,
    registry: &EvalRegistry,
    token: &str,
    mut request: tiny_http::Request,
) -> std::io::Result<()> {
    let reply = match authorize(
        header(&request, "Host"),
        header(&request, "Authorization"),
        token,
    ) {
        Err((status, message)) => error_reply(status, message),
        Ok(()) => {
            let mut body = Vec::new();
            if request.body_length().unwrap_or(0) > MAX_BODY {
                error_reply(413, "Anfrage zu groß")
            } else {
                request
                    .as_reader()
                    .take(MAX_BODY as u64)
                    .read_to_end(&mut body)?;
                let payload: Value = if body.is_empty() {
                    json!({})
                } else {
                    serde_json::from_slice(&body).unwrap_or(Value::Null)
                };
                if payload.is_null() {
                    error_reply(400, "Body ist kein JSON")
                } else {
                    let method = request.method().as_str().to_string();
                    let url = request.url().split('?').next().unwrap_or("").to_string();
                    route(app, registry, &method, &url, payload)
                }
            }
        }
    };
    let mut response = tiny_http::Response::from_data(reply.body).with_status_code(reply.status);
    response.add_header(
        tiny_http::Header::from_bytes(&b"Content-Type"[..], reply.content_type.as_bytes()).unwrap(),
    );
    request.respond(response)
}

fn window_of(app: &AppHandle, payload: &Value) -> Result<WebviewWindow, Reply> {
    let label = payload
        .get("window")
        .and_then(Value::as_str)
        .unwrap_or("main");
    app.get_webview_window(label)
        .ok_or_else(|| error_reply(404, format!("Kein Fenster `{label}`")))
}

fn window_info(window: &WebviewWindow) -> Value {
    let scale = window.scale_factor().unwrap_or(1.0);
    let position = window
        .outer_position()
        .map(|p| json!({ "x": p.x, "y": p.y }))
        .unwrap_or(Value::Null);
    let size = window
        .outer_size()
        .map(|s| json!({ "width": s.width, "height": s.height }))
        .unwrap_or(Value::Null);
    json!({
        "label": window.label(),
        "title": window.title().unwrap_or_default(),
        "visible": window.is_visible().unwrap_or(false),
        "focused": window.is_focused().unwrap_or(false),
        "position": position,
        "size": size,
        "scale": scale,
    })
}

fn route(
    app: &AppHandle,
    registry: &EvalRegistry,
    method: &str,
    path: &str,
    payload: Value,
) -> Reply {
    match (method, path) {
        ("GET", "/health") => json_reply(
            200,
            json!({ "ok": true, "pid": std::process::id(), "version": app.package_info().version.to_string() }),
        ),
        ("GET", "/windows") => {
            let handle = app.clone();
            match on_main(app, move || {
                let mut windows: Vec<Value> =
                    handle.webview_windows().values().map(window_info).collect();
                windows.sort_by(|a, b| a["label"].as_str().cmp(&b["label"].as_str()));
                windows
            }) {
                Ok(windows) => json_reply(200, json!({ "ok": true, "windows": windows })),
                Err(error) => error_reply(503, error),
            }
        }
        ("POST", "/eval") => {
            let window = match window_of(app, &payload) {
                Ok(window) => window,
                Err(reply) => return reply,
            };
            let Some(js) = payload.get("js").and_then(Value::as_str) else {
                return error_reply(400, "`js` fehlt");
            };
            let timeout = payload
                .get("timeout_ms")
                .and_then(Value::as_u64)
                .unwrap_or(DEFAULT_TIMEOUT_MS)
                .min(MAX_TIMEOUT_MS);
            eval_in(app, registry, &window, js, Duration::from_millis(timeout))
        }
        ("POST", "/invoke") => {
            let window = match window_of(app, &payload) {
                Ok(window) => window,
                Err(reply) => return reply,
            };
            let Some(command) = payload.get("command").and_then(Value::as_str) else {
                return error_reply(400, "`command` fehlt");
            };
            let args = payload.get("args").cloned().unwrap_or_else(|| json!({}));
            let js = format!(
                "return await window.__TAURI_INTERNALS__.invoke({}, {});",
                serde_json::to_string(command).unwrap(),
                args
            );
            let timeout = payload
                .get("timeout_ms")
                .and_then(Value::as_u64)
                .unwrap_or(DEFAULT_TIMEOUT_MS)
                .min(MAX_TIMEOUT_MS);
            eval_in(app, registry, &window, &js, Duration::from_millis(timeout))
        }
        ("POST", "/focus") => match window_of(app, &payload) {
            Ok(window) => match on_main(app, move || window.set_focus().map_err(|e| e.to_string()))
            {
                Ok(Ok(())) => json_reply(200, json!({ "ok": true })),
                Ok(Err(error)) => error_reply(500, error),
                Err(error) => error_reply(503, error),
            },
            Err(reply) => reply,
        },
        ("POST", "/screenshot") => match window_of(app, &payload) {
            Ok(window) => screenshot(app, &window),
            Err(reply) => reply,
        },
        _ => error_reply(404, format!("Unbekannte Route {method} {path}")),
    }
}

fn eval_in(
    app: &AppHandle,
    registry: &EvalRegistry,
    window: &WebviewWindow,
    js: &str,
    timeout: Duration,
) -> Reply {
    let id = registry.begin();
    let script = wrap_script(&id, js);
    let target = window.clone();
    match on_main(app, move || target.eval(&script).map_err(|e| e.to_string())) {
        Ok(Ok(())) => {}
        Ok(Err(error)) => {
            registry.wait(&id, Duration::ZERO);
            return error_reply(500, format!("eval: {error}"));
        }
        Err(error) => {
            registry.wait(&id, Duration::ZERO);
            return error_reply(503, error);
        }
    }
    match registry.wait(&id, timeout) {
        Some(result) => {
            let ok = result.get("ok").and_then(Value::as_bool).unwrap_or(false);
            json_reply(if ok { 200 } else { 422 }, result)
        }
        None => error_reply(
            504,
            format!(
                "Keine Antwort aus dem Fenster nach {} ms",
                timeout.as_millis()
            ),
        ),
    }
}

#[cfg(target_os = "macos")]
fn screenshot(app: &AppHandle, window: &WebviewWindow) -> Reply {
    let target = window.clone();
    let rect = on_main(app, move || {
        let scale = target.scale_factor().unwrap_or(1.0);
        match (target.outer_position(), target.outer_size()) {
            (Ok(position), Ok(size)) => Some((scale, position, size)),
            _ => None,
        }
    });
    let (scale, position, size) = match rect {
        Ok(Some(rect)) => rect,
        Ok(None) => return error_reply(500, "Fensterrechteck nicht lesbar"),
        Err(error) => return error_reply(503, error),
    };
    let rect = format!(
        "{},{},{},{}",
        (position.x as f64 / scale).round() as i64,
        (position.y as f64 / scale).round() as i64,
        (size.width as f64 / scale).round() as i64,
        (size.height as f64 / scale).round() as i64
    );
    let path =
        std::env::temp_dir().join(format!("speccify-qa-{}.png", uuid::Uuid::new_v4().simple()));
    let output = std::process::Command::new("screencapture")
        .args(["-x", "-R", &rect])
        .arg(&path)
        .output();
    let result = match output {
        Ok(output) if output.status.success() => std::fs::read(&path).map_err(|e| e.to_string()),
        Ok(output) => Err(String::from_utf8_lossy(&output.stderr).trim().to_string()),
        Err(error) => Err(error.to_string()),
    };
    let _ = std::fs::remove_file(&path);
    match result {
        Ok(bytes) if !bytes.is_empty() => Reply {
            status: 200,
            body: bytes,
            content_type: "image/png",
        },
        Ok(_) => error_reply(500, "Leerer Screenshot (Bildschirmaufnahme erlaubt?)"),
        Err(error) => error_reply(500, format!("screencapture: {error}")),
    }
}

#[cfg(not(target_os = "macos"))]
fn screenshot(_app: &AppHandle, _window: &WebviewWindow) -> Reply {
    error_reply(501, "Screenshot nur auf macOS")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn off_without_flag_or_env() {
        assert_eq!(config_from(std::iter::empty(), None, None).unwrap(), None);
        assert_eq!(
            config_from(std::iter::empty(), Some("  ".into()), None).unwrap(),
            None
        );
    }

    #[test]
    fn flag_wins_and_token_is_generated_or_taken() {
        let config = config_from(
            ["--qa-bridge=18769".to_string()].into_iter(),
            Some("1".into()),
            None,
        )
        .unwrap()
        .unwrap();
        assert_eq!(config.port, 18769);
        assert_eq!(config.token.len(), 32);
        let config = config_from(
            std::iter::empty(),
            Some("18770".into()),
            Some("geheim".into()),
        )
        .unwrap()
        .unwrap();
        assert_eq!((config.port, config.token.as_str()), (18770, "geheim"));
        assert!(config_from(["--qa-bridge=0".to_string()].into_iter(), None, None).is_err());
        assert!(config_from(std::iter::empty(), Some("abc".into()), None).is_err());
    }

    #[test]
    fn authorization_needs_loopback_host_and_token() {
        assert!(authorize(Some("127.0.0.1:18769"), Some("Bearer t"), "t").is_ok());
        assert!(authorize(Some("localhost:1"), Some("Bearer t"), "t").is_ok());
        assert_eq!(
            authorize(Some("evil.example:1"), Some("Bearer t"), "t")
                .unwrap_err()
                .0,
            403
        );
        assert_eq!(
            authorize(Some("127.0.0.1"), Some("Bearer x"), "t")
                .unwrap_err()
                .0,
            401
        );
        assert_eq!(authorize(Some("127.0.0.1"), None, "t").unwrap_err().0, 401);
    }

    #[test]
    fn wrapper_embeds_id_and_body() {
        let js = wrap_script("qa-7", "return document.title");
        assert!(js.contains("var __id=\"qa-7\""));
        assert!(js.contains("\nreturn document.title\n"));
        assert!(js.contains("qa_eval_result"));
    }

    #[test]
    fn registry_round_trip_and_timeout() {
        let registry = EvalRegistry::default();
        let id = registry.begin();
        assert!(!registry.complete("qa-unbekannt", json!({})));
        assert!(registry.complete(&id, json!({ "ok": true, "value": 1 })));
        assert_eq!(
            registry.wait(&id, Duration::from_millis(10)).unwrap()["value"],
            json!(1)
        );
        let id = registry.begin();
        assert!(registry.wait(&id, Duration::from_millis(20)).is_none());
        assert!(
            !registry.complete(&id, json!({})),
            "abgelaufene Kennung wird verworfen"
        );
    }
}
