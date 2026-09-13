//! desktop-ui-MCP (Plan toolkit-discovery-terminal.md, T7/D4): App-gehosteter
//! MCP-Server (127.0.0.1:8768) mit dem Tool `ask_bo` — der Agent stellt eine
//! Frage mit UI-Element (buttons / multi_select / form, Schema 1:1 wie die
//! produktive `ChatInteraction`-Vorlage), die Sidebar rendert sie, der BO
//! klickt, die Antwort geht als Tool-Result zurück. Der Call BLOCKIERT bis
//! zur Antwort oder bis zum Timeout; danach lässt sich die Antwort über
//! `ask_bo_result` nachholen („später beantworten", T0.6).

use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};

use serde_json::{json, Map, Value};
use speccify_mcp_core::{error_result, text_result, ToolServer};
use tauri::{AppHandle, Emitter, Manager, State};

pub const DEFAULT_PORT: u16 = 8768;

fn port_from_args(args: impl Iterator<Item = String>) -> Result<u16, String> {
    let mut port = DEFAULT_PORT;
    for arg in args {
        if let Some(value) = arg.strip_prefix("--desktop-ui-port=") {
            port = value
                .parse::<u16>()
                .ok()
                .filter(|port| *port > 0)
                .ok_or_else(|| "Ungültiger --desktop-ui-port: erwartet 1–65535".to_string())?;
        }
    }
    Ok(port)
}

pub fn configured_port() -> Result<u16, String> {
    port_from_args(std::env::args().skip(1))
}

#[tauri::command]
pub fn desktop_ui_endpoint() -> Result<String, String> {
    Ok(format!("http://127.0.0.1:{}", configured_port()?))
}

pub fn render_endpoint(template: &str, port: u16) -> String {
    template.replace("http://127.0.0.1:8768", &format!("http://127.0.0.1:{port}"))
}
const DEFAULT_TIMEOUT_SECONDS: f64 = 300.0;
const KINDS: &[&str] = &["buttons", "multi_select", "form"];
/// Spec 038: Obergrenze für Ad-hoc-HTML (inline oder aus Datei).
const MAX_HTML_BYTES: usize = 512 * 1024;

#[derive(Clone)]
pub struct Answer {
    pub selected_options: Vec<String>,
    pub field_values: Vec<String>,
    /// Spec 038: Formularwerte einer Ad-hoc-UI (`show_ui`), sonst `Null`.
    pub values: Value,
}

struct Entry {
    /// Event-Payload inkl. `id` — damit die UI offene Fragen auch AKTIV
    /// nachladen kann (Events sind flüchtig: Reload/HMR/verpasster Start).
    payload: Value,
    answer: Option<Answer>,
}

#[derive(Default)]
struct RegistryInner {
    entries: Mutex<HashMap<String, Entry>>,
    condvar: Condvar,
    counter: AtomicU64,
    app: Mutex<Option<AppHandle>>,
}

/// Geteilter Zustand zwischen MCP-Server-Thread und Tauri-Commands.
#[derive(Clone, Default)]
pub struct AskBoRegistry(Arc<RegistryInner>);

impl AskBoRegistry {
    pub fn set_app(&self, app: AppHandle) {
        *self.0.app.lock().unwrap() = Some(app);
    }

    fn emit(&self, event: &str, payload: Value) {
        if let Some(app) = self.0.app.lock().unwrap().as_ref() {
            let _ = app.emit(event, payload);
        }
    }

    /// Legt eine Interaktion an und schickt sie als `ask-bo`-Event an die UI.
    fn create(&self, payload: &Value) -> String {
        let id = format!("ask-{}", self.0.counter.fetch_add(1, Ordering::SeqCst) + 1);
        let mut event = payload.clone();
        event["id"] = Value::String(id.clone());
        self.0.entries.lock().unwrap().insert(
            id.clone(),
            Entry {
                payload: event.clone(),
                answer: None,
            },
        );
        self.emit("ask-bo", event.clone());
        self.open_popup(&id, &event);
        id
    }

    /// Spec 038 (BO-Finding): jede Frage bekommt ein eigenes kleines Fenster
    /// `ask-<n>`, das die SPA als Frage-Popup rendert und nach der Antwort
    /// schließt. Fensterbau gehört auf den Main-Thread.
    fn open_popup(&self, id: &str, payload: &Value) {
        let Some(app) = self.0.app.lock().unwrap().clone() else {
            return;
        };
        let label = id.to_string();
        let title = payload
            .get("title")
            .and_then(Value::as_str)
            .filter(|t| !t.is_empty())
            .or_else(|| payload.get("prompt").and_then(Value::as_str))
            .unwrap_or("Agent fragt")
            .to_string();
        let html = payload.get("kind").and_then(Value::as_str) == Some("html");
        let app_for_build = app.clone();
        let _ = app.run_on_main_thread(move || {
            let builder = tauri::WebviewWindowBuilder::new(
                &app_for_build,
                label,
                tauri::WebviewUrl::App("index.html".into()),
            )
            .title(format!("{title} — Speccify"))
            .inner_size(
                if html { 620.0 } else { 460.0 },
                if html { 560.0 } else { 360.0 },
            )
            .min_inner_size(360.0, 240.0)
            .center()
            .focused(true);
            #[cfg(target_os = "macos")]
            let builder = builder
                .title_bar_style(tauri::TitleBarStyle::Overlay)
                .hidden_title(true);
            if let Err(error) = builder.build() {
                eprintln!("Frage-Popup: {error}");
            }
        });
    }

    /// Alle noch unbeantworteten Interaktionen (UI-Sync beim Mount/Poll).
    pub fn pending(&self) -> Vec<Value> {
        self.0
            .entries
            .lock()
            .unwrap()
            .values()
            .filter(|entry| entry.answer.is_none())
            .map(|entry| entry.payload.clone())
            .collect()
    }

    /// Blockiert bis zur Antwort oder bis zum Timeout.
    fn wait(&self, id: &str, timeout: Duration) -> Option<Answer> {
        let deadline = Instant::now() + timeout;
        let mut entries = self.0.entries.lock().unwrap();
        loop {
            if let Some(answer) = entries.get(id).and_then(|entry| entry.answer.clone()) {
                return Some(answer);
            }
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                return None;
            }
            let (guard, wait_result) = self.0.condvar.wait_timeout(entries, remaining).unwrap();
            entries = guard;
            if wait_result.timed_out() {
                return entries.get(id).and_then(|entry| entry.answer.clone());
            }
        }
    }

    fn lookup(&self, id: &str) -> Result<Option<Answer>, String> {
        let entries = self.0.entries.lock().unwrap();
        match entries.get(id) {
            Some(entry) => Ok(entry.answer.clone()),
            None => Err(format!("Unbekannte Interaktion: {id}")),
        }
    }

    pub fn answer(
        &self,
        id: &str,
        selected_options: Vec<String>,
        field_values: Vec<String>,
    ) -> Result<(), String> {
        self.resolve(
            id,
            Answer {
                selected_options,
                field_values,
                values: Value::Null,
            },
        )
    }

    /// Spec 038: Antwort einer Ad-hoc-UI — beliebiges JSON-Objekt aus dem Formular.
    pub fn answer_values(&self, id: &str, values: Value) -> Result<(), String> {
        self.resolve(
            id,
            Answer {
                selected_options: Vec::new(),
                field_values: Vec::new(),
                values,
            },
        )
    }

    fn resolve(&self, id: &str, answer: Answer) -> Result<(), String> {
        {
            let mut entries = self.0.entries.lock().unwrap();
            let entry = entries
                .get_mut(id)
                .ok_or_else(|| format!("Unbekannte Interaktion: {id}"))?;
            if entry.answer.is_some() {
                return Err(format!("Interaktion {id} ist schon beantwortet."));
            }
            entry.answer = Some(answer.clone());
        }
        self.0.condvar.notify_all();
        self.emit(
            "ask-bo-answered",
            json!({
                "id": id,
                "selected_options": answer.selected_options,
                "field_values": answer.field_values,
                "values": answer.values,
            }),
        );
        self.close_popup(id);
        Ok(())
    }

    /// Das Popup schließt sich nach der Antwort — von hier aus, damit es nicht
    /// von Frontend-Berechtigungen abhängt (BO-Finding: Fenster blieb stehen).
    fn close_popup(&self, id: &str) {
        let Some(app) = self.0.app.lock().unwrap().clone() else {
            return;
        };
        let label = id.to_string();
        std::thread::spawn(move || {
            std::thread::sleep(Duration::from_millis(700));
            let app_for_close = app.clone();
            let _ = app.run_on_main_thread(move || {
                if let Some(window) = app_for_close.get_webview_window(&label) {
                    let _ = window.close();
                }
            });
        });
    }
}

fn answer_json(answer: &Answer) -> Value {
    json!({
        "answered": true,
        "selected_options": answer.selected_options,
        "field_values": answer.field_values,
        "values": answer.values,
    })
}

/// Der MCP-Server über der Registry.
pub struct DesktopUiMcp {
    registry: AskBoRegistry,
}

impl DesktopUiMcp {
    pub fn new(registry: AskBoRegistry) -> Self {
        Self { registry }
    }

    fn ask_bo(&self, arguments: &Map<String, Value>) -> Value {
        let kind = arguments.get("kind").and_then(Value::as_str).unwrap_or("");
        if !KINDS.contains(&kind) {
            return error_result(format!(
                "ask_bo benötigt 'kind' ∈ {{{}}}.",
                KINDS.join(", ")
            ));
        }
        let prompt = arguments
            .get("prompt")
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|prompt| !prompt.is_empty());
        let Some(prompt) = prompt else {
            return error_result("ask_bo benötigt 'prompt' (String).");
        };
        let options: Vec<String> = arguments
            .get("options")
            .and_then(Value::as_array)
            .map(|options| {
                options
                    .iter()
                    .filter_map(Value::as_str)
                    .map(String::from)
                    .collect()
            })
            .unwrap_or_default();
        let fields: Vec<Value> = arguments
            .get("fields")
            .and_then(Value::as_array)
            .map(|fields| {
                fields
                    .iter()
                    .filter_map(|field| {
                        let label = field.get("label")?.as_str()?;
                        Some(json!({
                            "label": label,
                            "recommended": field.get("recommended").and_then(Value::as_str),
                        }))
                    })
                    .collect()
            })
            .unwrap_or_default();

        if (kind == "buttons" || kind == "multi_select") && options.is_empty() {
            return error_result(format!("'{kind}' benötigt 'options' (Liste von Strings)."));
        }
        if kind == "form" && fields.is_empty() {
            return error_result("'form' benötigt 'fields' ([{label, recommended?}]).");
        }

        let payload = json!({
            "kind": kind,
            "prompt": prompt,
            "options": options,
            "fields": fields,
        });
        let id = self.registry.create(&payload);

        let timeout = arguments
            .get("timeout_seconds")
            .and_then(Value::as_f64)
            .filter(|seconds| *seconds > 0.0)
            .unwrap_or(DEFAULT_TIMEOUT_SECONDS);
        match self.registry.wait(&id, Duration::from_secs_f64(timeout)) {
            Some(answer) => text_result(answer_json(&answer).to_string(), false),
            None => text_result(
                json!({
                    "answered": false,
                    "interaction_id": id,
                    "hint": "Noch keine Antwort — die Frage bleibt in der App offen. \
                             Später mit ask_bo_result nachfragen; nicht erneut stellen.",
                })
                .to_string(),
                false,
            ),
        }
    }

    /// Spec 038: Ad-hoc-UI aus HTML (Tailwind-Klassen erlaubt) — `ask` wartet auf
    /// das Formular, `show` zeigt nur an.
    fn show_ui(&self, arguments: &Map<String, Value>) -> Value {
        let title = arguments
            .get("title")
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|t| !t.is_empty())
            .unwrap_or("Agent fragt");
        let mode = arguments
            .get("mode")
            .and_then(Value::as_str)
            .unwrap_or("ask");
        if mode != "ask" && mode != "show" {
            return error_result(
                "show_ui: 'mode' ist 'ask' (wartet auf Antwort) oder 'show' (nur anzeigen).",
            );
        }
        let inline = arguments
            .get("html")
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|h| !h.is_empty())
            .map(str::to_string);
        let html = match (inline, arguments.get("file").and_then(Value::as_str)) {
            (Some(html), _) => html,
            (None, Some(file)) => {
                let path = std::path::Path::new(file);
                if !path.is_absolute() {
                    return error_result("show_ui: 'file' muss ein absoluter Pfad sein (z. B. <projekt>/.agent/skills/<skill>/ui/frage.html).");
                }
                match std::fs::metadata(path) {
                    Ok(meta) if meta.is_file() && meta.len() as usize <= MAX_HTML_BYTES => {
                        match std::fs::read_to_string(path) {
                            Ok(text) => text,
                            Err(error) => return error_result(format!("show_ui: {file}: {error}")),
                        }
                    }
                    Ok(meta) if meta.is_file() => {
                        return error_result(format!(
                            "show_ui: {file} ist größer als {} KB.",
                            MAX_HTML_BYTES / 1024
                        ))
                    }
                    _ => return error_result(format!("show_ui: keine Datei: {file}")),
                }
            }
            (None, None) => {
                return error_result(
                    "show_ui benötigt 'html' (String) oder 'file' (absoluter Pfad).",
                )
            }
        };
        if html.len() > MAX_HTML_BYTES {
            return error_result(format!(
                "show_ui: HTML ist größer als {} KB.",
                MAX_HTML_BYTES / 1024
            ));
        }
        let payload = json!({
            "kind": "html",
            "prompt": title,
            "title": title,
            "html": html,
            "mode": mode,
            "options": [],
            "fields": [],
        });
        let id = self.registry.create(&payload);
        if mode == "show" {
            return text_result(
                json!({"shown": true, "interaction_id": id, "hint": "Die Anzeige bleibt offen, bis die Person sie schließt; ui_result liefert dann {closed: true}."}).to_string(),
                false,
            );
        }
        let timeout = arguments
            .get("timeout_seconds")
            .and_then(Value::as_f64)
            .filter(|seconds| *seconds > 0.0)
            .unwrap_or(DEFAULT_TIMEOUT_SECONDS);
        match self.registry.wait(&id, Duration::from_secs_f64(timeout)) {
            Some(answer) => text_result(answer_json(&answer).to_string(), false),
            None => text_result(
                json!({
                    "answered": false,
                    "interaction_id": id,
                    "hint": "Noch keine Antwort — die Oberfläche bleibt in der App offen. Später mit ui_result nachfragen; nicht erneut zeigen.",
                })
                .to_string(),
                false,
            ),
        }
    }

    fn ask_bo_result(&self, arguments: &Map<String, Value>) -> Value {
        let id = arguments
            .get("interaction_id")
            .and_then(Value::as_str)
            .unwrap_or("");
        match self.registry.lookup(id) {
            Err(error) => error_result(error),
            Ok(Some(answer)) => text_result(answer_json(&answer).to_string(), false),
            Ok(None) => text_result(
                json!({"answered": false, "interaction_id": id}).to_string(),
                false,
            ),
        }
    }
}

impl ToolServer for DesktopUiMcp {
    fn server_info(&self) -> Value {
        json!({
            "name": "speccify-desktop-ui-mcp",
            "version": env!("CARGO_PKG_VERSION"),
            "mode": "desktop-ui",
        })
    }

    fn tool_descriptors(&self) -> Vec<Value> {
        vec![
            json!({
                "name": "ask_bo",
                "description": "Ask the project owner a question through the Speccify app UI and wait for the answer. kinds: 'buttons' (single choice), 'multi_select' (checkboxes), 'form' (list of questions; empty input means the recommended value applies). Blocks until answered or timeout_seconds (default 300); on timeout the question stays open — poll with ask_bo_result instead of asking again.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "enum": ["buttons", "multi_select", "form"]},
                        "prompt": {"type": "string", "description": "The question/heading."},
                        "options": {"type": "array", "items": {"type": "string"}, "description": "Choices for buttons/multi_select."},
                        "fields": {"type": "array", "items": {"type": "object", "properties": {"label": {"type": "string"}, "recommended": {"type": "string"}}, "required": ["label"]}, "description": "Rows for form."},
                        "timeout_seconds": {"type": "number"},
                    },
                    "required": ["kind", "prompt"],
                },
            }),
            json!({
                "name": "show_ui",
                "description": "Show the project owner an ad-hoc user interface in the Speccify app: a fragment of HTML (Tailwind utility classes work, no external scripts). mode 'ask' (default) blocks until the owner submits a <form> or clicks an element with data-answer=\"…\" and returns {answered, values} where values are the form fields by name (checkboxes with the same name become arrays; the submit button's name/value is included). mode 'show' just displays it (tables, progress, previews) and returns at once. Use 'html' for inline markup or 'file' (absolute path) for a UI saved in a skill (.agent/skills/<name>/ui/*.html). Blocks until answered or timeout_seconds (default 300); on timeout poll ui_result instead of showing again.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Heading shown above the UI."},
                        "html": {"type": "string", "description": "HTML fragment (body content)."},
                        "file": {"type": "string", "description": "Absolute path to an HTML file instead of 'html'."},
                        "mode": {"type": "string", "enum": ["ask", "show"]},
                        "timeout_seconds": {"type": "number"},
                    },
                },
            }),
            json!({
                "name": "ui_result",
                "description": "Fetch the answer of an earlier show_ui interaction that timed out or was shown ({answered:false} until the owner responds or closes it).",
                "inputSchema": {
                    "type": "object",
                    "properties": {"interaction_id": {"type": "string"}},
                    "required": ["interaction_id"],
                },
            }),
            json!({
                "name": "ask_bo_result",
                "description": "Fetch the answer of an earlier ask_bo interaction that timed out (answered=false until the owner responds).",
                "inputSchema": {
                    "type": "object",
                    "properties": {"interaction_id": {"type": "string"}},
                    "required": ["interaction_id"],
                },
            }),
        ]
    }

    fn call_tool(&self, name: Option<&str>, arguments: &Map<String, Value>) -> Value {
        match name {
            Some("ask_bo") => self.ask_bo(arguments),
            Some("ask_bo_result") | Some("ui_result") => self.ask_bo_result(arguments),
            Some("show_ui") => self.show_ui(arguments),
            other => error_result(format!("Unbekanntes Tool: {}", other.unwrap_or("(none)"))),
        }
    }
}

/// Antwort aus der Sidebar (Tauri-Command).
#[tauri::command]
pub fn ask_bo_answer(
    registry: State<AskBoRegistry>,
    id: String,
    selected_options: Vec<String>,
    field_values: Vec<String>,
) -> Result<(), String> {
    registry.answer(&id, selected_options, field_values)
}

/// Spec 038: Antwort einer Ad-hoc-UI (Formularwerte als JSON-Objekt).
#[tauri::command]
pub fn ui_answer(registry: State<AskBoRegistry>, id: String, values: Value) -> Result<(), String> {
    registry.answer_values(&id, values)
}

/// Offene Interaktionen abholen (Robustheit: Events sind flüchtig).
#[tauri::command]
pub fn ask_bo_pending(registry: State<AskBoRegistry>) -> Vec<Value> {
    registry.pending()
}

#[cfg(test)]
mod tests {
    #[test]
    fn port_selection_is_explicit_and_validated() {
        assert_eq!(super::port_from_args(std::iter::empty()).unwrap(), 8768);
        assert_eq!(
            super::port_from_args(["--desktop-ui-port=18768".into()].into_iter()).unwrap(),
            18768
        );
        for value in ["0", "65536", "no", ""] {
            assert!(
                super::port_from_args([format!("--desktop-ui-port={value}")].into_iter()).is_err()
            );
        }
    }

    #[test]
    fn new_host_configs_use_selected_port_and_preserve_other_endpoints() {
        let json = super::render_endpoint(include_str!("../templates/mcp.json"), 18768);
        let toml = super::render_endpoint(include_str!("../templates/codex-config.toml"), 18768);
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert_eq!(
            parsed["mcpServers"]["speccify-desktop-ui"]["url"],
            "http://127.0.0.1:18768"
        );
        let parsed: toml::Value = toml::from_str(&toml).unwrap();
        assert_eq!(
            parsed["mcp_servers"]["speccify-desktop-ui"]["url"].as_str(),
            Some("http://127.0.0.1:18768")
        );
        assert!(json.contains("http://127.0.0.1:8765"));
        assert!(toml.contains("http://127.0.0.1:8767"));
    }

    use super::*;

    fn call(server: &DesktopUiMcp, name: &str, args: Value) -> Value {
        server.call_tool(Some(name), args.as_object().unwrap())
    }

    fn content_json(result: &Value) -> Value {
        serde_json::from_str(result["content"][0]["text"].as_str().unwrap()).unwrap()
    }

    #[test]
    fn ask_bo_blocks_until_answered() {
        let registry = AskBoRegistry::default();
        let server = DesktopUiMcp::new(registry.clone());

        // Antwort-Thread: wartet kurz, beantwortet dann die erste Interaktion.
        let registry_for_answer = registry.clone();
        let answerer = std::thread::spawn(move || {
            std::thread::sleep(Duration::from_millis(150));
            registry_for_answer
                .answer("ask-1", vec!["Ja".into()], vec![])
                .unwrap();
        });

        let result = call(
            &server,
            "ask_bo",
            json!({"kind": "buttons", "prompt": "Deploy?", "options": ["Ja", "Nein"], "timeout_seconds": 10}),
        );
        answerer.join().unwrap();
        let body = content_json(&result);
        assert_eq!(body["answered"], true);
        assert_eq!(body["selected_options"], json!(["Ja"]));
    }

    #[test]
    fn ask_bo_timeout_leaves_interaction_open_for_result() {
        let registry = AskBoRegistry::default();
        let server = DesktopUiMcp::new(registry.clone());
        let result = call(
            &server,
            "ask_bo",
            json!({"kind": "multi_select", "prompt": "Welche?", "options": ["a", "b"], "timeout_seconds": 0.2}),
        );
        let body = content_json(&result);
        assert_eq!(body["answered"], false);
        let id = body["interaction_id"].as_str().unwrap().to_string();

        // Noch offen …
        let pending = content_json(&call(
            &server,
            "ask_bo_result",
            json!({"interaction_id": id}),
        ));
        assert_eq!(pending["answered"], false);
        // … und über pending() für die UI abholbar.
        let open = registry.pending();
        assert_eq!(open.len(), 1);
        assert_eq!(open[0]["id"].as_str().unwrap(), id);
        assert_eq!(open[0]["kind"], "multi_select");
        // … später beantwortet → ask_bo_result liefert sie.
        registry
            .answer(&id, vec!["a".into(), "b".into()], vec![])
            .unwrap();
        let answered = content_json(&call(
            &server,
            "ask_bo_result",
            json!({"interaction_id": id}),
        ));
        assert_eq!(answered["answered"], true);
        assert_eq!(answered["selected_options"], json!(["a", "b"]));
        assert!(registry.pending().is_empty()); // beantwortet ⇒ nicht mehr offen
                                                // Doppelt beantworten ist ein Fehler.
        assert!(registry.answer(&id, vec![], vec![]).is_err());
    }

    #[test]
    fn ask_bo_validates_shape() {
        let server = DesktopUiMcp::new(AskBoRegistry::default());
        assert_eq!(
            call(&server, "ask_bo", json!({"kind": "nope", "prompt": "x"}))["isError"],
            true
        );
        assert_eq!(
            call(&server, "ask_bo", json!({"kind": "buttons", "prompt": "x"}))["isError"],
            true
        );
        assert_eq!(
            call(&server, "ask_bo", json!({"kind": "form", "prompt": "x"}))["isError"],
            true
        );
        assert_eq!(
            call(
                &server,
                "ask_bo_result",
                json!({"interaction_id": "gibtsnicht"})
            )["isError"],
            true
        );
    }

    #[test]
    fn show_ui_waits_for_form_values_and_supports_show_and_files() {
        let registry = AskBoRegistry::default();
        let server = DesktopUiMcp::new(registry.clone());
        // Validierung.
        assert_eq!(call(&server, "show_ui", json!({}))["isError"], true);
        assert_eq!(
            call(
                &server,
                "show_ui",
                json!({"html": "<p>x</p>", "mode": "later"})
            )["isError"],
            true
        );
        assert_eq!(
            call(&server, "show_ui", json!({"file": "relative.html"}))["isError"],
            true
        );
        assert_eq!(
            call(&server, "show_ui", json!({"file": "/nonexistent/x.html"}))["isError"],
            true
        );
        // ask: blockiert bis ui_answer.
        let answering = registry.clone();
        std::thread::spawn(move || {
            std::thread::sleep(std::time::Duration::from_millis(150));
            let pending = answering.pending();
            let id = pending[0]["id"].as_str().unwrap().to_string();
            assert_eq!(pending[0]["kind"], "html");
            answering
                .answer_values(&id, json!({"deploy": "yes", "targets": ["a", "b"]}))
                .unwrap();
        });
        let result = call(
            &server,
            "show_ui",
            json!({"title": "Deploy?", "html": "<form><button name='deploy' value='yes'>Ja</button></form>", "timeout_seconds": 10}),
        );
        let body = content_json(&result);
        assert_eq!(body["answered"], true);
        assert_eq!(body["values"]["deploy"], "yes");
        assert_eq!(body["values"]["targets"], json!(["a", "b"]));
        // show: kehrt sofort zurück, ui_result meldet später das Schließen.
        let shown = content_json(&call(
            &server,
            "show_ui",
            json!({"html": "<table></table>", "mode": "show"}),
        ));
        assert_eq!(shown["shown"], true);
        let id = shown["interaction_id"].as_str().unwrap().to_string();
        assert_eq!(
            content_json(&call(&server, "ui_result", json!({"interaction_id": id})))["answered"],
            false
        );
        registry
            .answer_values(&id, json!({"closed": true}))
            .unwrap();
        assert_eq!(
            content_json(&call(&server, "ui_result", json!({"interaction_id": id})))["values"]
                ["closed"],
            true
        );
        // file: absoluter Pfad wird gelesen; Timeout lässt die UI offen.
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("frage.html");
        std::fs::write(&file, "<p class='font-bold'>Aus Datei</p>").unwrap();
        let timed_out = content_json(&call(
            &server,
            "show_ui",
            json!({"file": file.to_string_lossy(), "timeout_seconds": 0.2}),
        ));
        assert_eq!(timed_out["answered"], false);
        let open = registry.pending();
        assert!(open
            .iter()
            .any(|entry| entry["html"] == "<p class='font-bold'>Aus Datei</p>"));
    }
}
