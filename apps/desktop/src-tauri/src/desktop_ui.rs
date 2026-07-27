//! desktop-ui-MCP (Plan toolkit-discovery-terminal.md, T7/D4): App-gehosteter
//! MCP-Server (127.0.0.1:8768) mit dem Tool `ask_bo` — der Agent stellt eine
//! Frage mit UI-Element (buttons / multi_select / form, Schema 1:1 wie die
//! produktive iKanbanAi-`ChatInteraction`), die Sidebar rendert sie, der BO
//! klickt, die Antwort geht als Tool-Result zurück. Der Call BLOCKIERT bis
//! zur Antwort oder bis zum Timeout; danach lässt sich die Antwort über
//! `ask_bo_result` nachholen („später beantworten", T0.6).

use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};

use serde_json::{json, Map, Value};
use speccify_mcp_core::{error_result, text_result, ToolServer};
use tauri::{AppHandle, Emitter, State};

pub const DEFAULT_PORT: u16 = 8768;
const DEFAULT_TIMEOUT_SECONDS: f64 = 300.0;
const KINDS: &[&str] = &["buttons", "multi_select", "form"];

#[derive(Clone)]
pub struct Answer {
    pub selected_options: Vec<String>,
    pub field_values: Vec<String>,
}

struct Entry {
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
        self.0
            .entries
            .lock()
            .unwrap()
            .insert(id.clone(), Entry { answer: None });
        let mut event = payload.clone();
        event["id"] = Value::String(id.clone());
        self.emit("ask-bo", event);
        id
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
        {
            let mut entries = self.0.entries.lock().unwrap();
            let entry = entries
                .get_mut(id)
                .ok_or_else(|| format!("Unbekannte Interaktion: {id}"))?;
            if entry.answer.is_some() {
                return Err(format!("Interaktion {id} ist schon beantwortet."));
            }
            entry.answer = Some(Answer {
                selected_options: selected_options.clone(),
                field_values: field_values.clone(),
            });
        }
        self.0.condvar.notify_all();
        self.emit(
            "ask-bo-answered",
            json!({
                "id": id,
                "selected_options": selected_options,
                "field_values": field_values,
            }),
        );
        Ok(())
    }
}

fn answer_json(answer: &Answer) -> Value {
    json!({
        "answered": true,
        "selected_options": answer.selected_options,
        "field_values": answer.field_values,
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
            Some("ask_bo_result") => self.ask_bo_result(arguments),
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

#[cfg(test)]
mod tests {
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
}
