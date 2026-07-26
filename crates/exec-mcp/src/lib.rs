//! Exec-MCP-Server (Plan toolkit-discovery-terminal.md, T4): Rust-Port der
//! dotagent-Referenz. Wire-Semantik und exakte Fehlertexte:
//! `docs/exec-mcp-contract.md`. Bis der Diff-Harness (28/28) grün ist und
//! die Prozess-Lebensdauer-Tests stehen, bleibt die Python-Referenz auf 8765.

pub mod exec;

use std::path::PathBuf;

use serde_json::{Map, Value, json};
use speccify_mcp_core::allowlist::{Allowlist, agent_dir};
use speccify_mcp_core::{ToolServer, error_result, text_result};

pub const DEFAULT_TIMEOUT_SECONDS: f64 = 600.0;
pub const DEFAULT_PORT: u16 = 8765;

const MULTI_MISSING: &str = "Server läuft im Multi-Projekt-Modus: 'project' (absoluter Pfad des Ziel-Projekts) ist erforderlich.";

pub struct ExecMcp {
    /// `Some` = bound (ein Projekt), `None` = multi (project je Aufruf).
    pub project_root: Option<PathBuf>,
    pub timeout_secs: f64,
}

impl ExecMcp {
    pub fn new(project_root: Option<PathBuf>, timeout_secs: f64) -> Self {
        Self {
            project_root,
            timeout_secs,
        }
    }

    fn expanduser(raw: &str) -> PathBuf {
        if let Some(rest) = raw.strip_prefix("~/")
            && let Ok(home) = std::env::var("HOME")
        {
            return PathBuf::from(home).join(rest);
        }
        PathBuf::from(raw)
    }

    /// Ziel-Projekt eines Aufrufs (→ Pfad oder Fehlertext). Exakt die
    /// Referenz-Semantik/-Texte aus `docs/exec-mcp-contract.md`.
    fn resolve_project(&self, arguments: &Map<String, Value>) -> Result<PathBuf, String> {
        let raw_value = arguments.get("project");
        if let Some(value) = raw_value
            && !value.is_string()
        {
            return Err("'project' muss ein String (absoluter Pfad) sein.".into());
        }
        let raw = raw_value
            .and_then(Value::as_str)
            .filter(|value| !value.is_empty());
        let explicit = raw.map(Self::expanduser);

        if let Some(root) = &self.project_root {
            if let Some(explicit) = &explicit {
                let same = canonical(explicit) == canonical(root);
                if !same {
                    return Err(format!(
                        "Server ist an {} gebunden — 'project' '{}' wird abgelehnt.",
                        root.display(),
                        raw.unwrap_or_default()
                    ));
                }
            }
            return Ok(root.clone());
        }

        match explicit {
            None => Err(MULTI_MISSING.into()),
            Some(path) => {
                if !path.is_absolute() {
                    return Err(format!(
                        "'project' muss absolut sein: '{}'",
                        raw.unwrap_or_default()
                    ));
                }
                if !path.join(".agent").is_dir() {
                    return Err(format!(
                        "Kein dotagent-Projekt (fehlendes .agent/): {}",
                        path.display()
                    ));
                }
                Ok(canonical(&path))
            }
        }
    }

    fn allowlist_for(&self, project: &std::path::Path) -> Allowlist {
        Allowlist::new(agent_dir(project))
    }

    fn load_actions(project: &std::path::Path) -> Vec<Value> {
        let path = project.join(".agent").join("actions.json");
        match std::fs::read_to_string(path) {
            Ok(text) => match serde_json::from_str::<Value>(&text) {
                Ok(Value::Array(actions)) => actions
                    .into_iter()
                    .filter(|action| action.is_object())
                    .collect(),
                _ => Vec::new(),
            },
            Err(_) => Vec::new(),
        }
    }

    // -- Tools ------------------------------------------------------------

    fn run_command(&self, arguments: &Map<String, Value>) -> Value {
        let command = match trimmed_string(arguments, "command") {
            Some(command) => command,
            None => return error_result("run_command benötigt 'command' (String)."),
        };
        let project = match self.resolve_project(arguments) {
            Ok(project) => project,
            Err(error) => return error_result(error),
        };
        let allowlist = self.allowlist_for(&project);
        if !allowlist.is_allowed(&command) {
            allowlist.record_pending(&command);
            return error_result(format!(
                "Command not allowlisted: \"{command}\". It was recorded for approval — ask the \
                 project owner to approve it (pending list in the app), then try again."
            ));
        }
        let result = exec::run_command_result(
            &command,
            &project,
            self.timeout_secs,
            exec::MAX_OUTPUT_CHARS,
        );
        allowlist.consume(&command);
        let is_error = result.get("exit_code").and_then(Value::as_i64) != Some(0);
        text_result(result.to_string(), is_error)
    }

    fn run_action(&self, arguments: &Map<String, Value>) -> Value {
        let name = match trimmed_string(arguments, "name") {
            Some(name) => name,
            None => return error_result("run_action benötigt 'name' (String)."),
        };
        let project = match self.resolve_project(arguments) {
            Ok(project) => project,
            Err(error) => return error_result(error),
        };
        let actions = Self::load_actions(&project);
        let action = actions
            .iter()
            .find(|action| action.get("name").and_then(Value::as_str) == Some(name.as_str()));
        let Some(action) = action else {
            let mut known: Vec<&str> = actions
                .iter()
                .filter_map(|action| action.get("name").and_then(Value::as_str))
                .collect();
            known.sort_unstable();
            let known = if known.is_empty() {
                "(none)".to_string()
            } else {
                known.join(", ")
            };
            return error_result(format!(
                "Unknown action \"{name}\". Known actions: {known}. Use list_actions for details."
            ));
        };
        if !action
            .get("confirmed")
            .and_then(Value::as_bool)
            .unwrap_or(true)
        {
            return error_result(format!(
                "Action \"{name}\" is not confirmed yet — ask the project owner to confirm it in \
                 the Actions tab, then try again."
            ));
        }
        let command = action.get("command").and_then(Value::as_str).unwrap_or("");
        if command.trim().is_empty() {
            return error_result(format!("Action \"{name}\" has no command."));
        }
        // Über den run_command-Pfad (gleiche Allowlist); project weiterreichen.
        let mut forwarded = Map::new();
        forwarded.insert("command".into(), Value::String(command.into()));
        if let Some(project) = arguments.get("project") {
            forwarded.insert("project".into(), project.clone());
        }
        self.run_command(&forwarded)
    }

    fn list_actions(&self, arguments: &Map<String, Value>) -> Value {
        let project = match self.resolve_project(arguments) {
            Ok(project) => project,
            Err(error) => return error_result(error),
        };
        let path = project.join(".agent").join("actions.json");
        match std::fs::read_to_string(path) {
            Ok(text) => text_result(text, false),
            Err(_) => text_result("[]", false),
        }
    }

    /// `/stream`-Endpoint: ruft `emit` je Event; gleiche Allowlist-/Projekt-
    /// Prüfung wie `run_command`, aber Events statt End-Resultat.
    pub fn stream_run(
        &self,
        arguments: &Map<String, Value>,
        emit: &mut dyn FnMut(&Value) -> std::io::Result<()>,
    ) {
        let Some(command) = trimmed_string(arguments, "command") else {
            let _ = emit(&json!({
                "type": "exit", "exit_code": Value::Null,
                "error": "run_command benötigt 'command' (String).",
            }));
            return;
        };
        let project = match self.resolve_project(arguments) {
            Ok(project) => project,
            Err(error) => {
                let _ = emit(&json!({"type": "exit", "exit_code": Value::Null, "error": error}));
                return;
            }
        };
        let allowlist = self.allowlist_for(&project);
        if !allowlist.is_allowed(&command) {
            allowlist.record_pending(&command);
            let _ = emit(&json!({
                "type": "exit", "exit_code": Value::Null,
                "error": format!(
                    "Command not allowlisted: \"{command}\". It was recorded for approval — ask \
                     the project owner to approve it, then try again."
                ),
            }));
            return;
        }
        exec::stream_command(&command, &project, self.timeout_secs, emit);
        allowlist.consume(&command);
    }

    fn target_phrase(&self) -> String {
        match &self.project_root {
            Some(root) => format!(
                "the project root ({})",
                root.file_name()
                    .map(|name| name.to_string_lossy().into_owned())
                    .unwrap_or_default()
            ),
            None => "the given project root".into(),
        }
    }

    fn project_property(&self) -> Value {
        let suffix = if self.project_root.is_some() {
            "Optional — this server is bound to one project."
        } else {
            "REQUIRED — this server runs in multi-project mode."
        };
        json!({
            "project": {
                "type": "string",
                "description": format!("Absolute path of the target project (must contain .agent/). {suffix}"),
            }
        })
    }
}

impl ToolServer for ExecMcp {
    fn server_info(&self) -> Value {
        let mut info = json!({
            "name": "speccify-exec-mcp",
            "version": env!("CARGO_PKG_VERSION"),
            "mode": if self.project_root.is_some() { "bound" } else { "multi" },
        });
        if let Some(root) = &self.project_root {
            info["projectRoot"] = Value::String(root.display().to_string());
        }
        info
    }

    fn tool_descriptors(&self) -> Vec<Value> {
        let target = self.target_phrase();
        let project_property = self.project_property();
        let project_field = project_property.get("project").cloned().unwrap();
        let bound = self.project_root.is_some();

        let mut run_command_props = Map::new();
        run_command_props.insert(
            "command".into(),
            json!({"type": "string", "description": "The command line, e.g. \"npm test\" or \"swift test\"."}),
        );
        run_command_props.insert("project".into(), project_field.clone());

        let mut run_action_props = Map::new();
        run_action_props.insert(
            "name".into(),
            json!({"type": "string", "description": "Action name as shown by list_actions, e.g. \"Tests\"."}),
        );
        run_action_props.insert("project".into(), project_field.clone());

        vec![
            json!({
                "name": "run_command",
                "description": format!(
                    "Run an allowlisted CLI command in {target} and return exit code, stdout and \
                     stderr. Use this to run tests, builds and linters yourself instead of \
                     accepting work by inspection. Prefer run_action when the project already \
                     defines a matching named action (see list_actions). Commands not on the \
                     allowlist are recorded for approval by the project owner and show up as \
                     proposed actions in the app — mention that and continue; do not retry \
                     immediately."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": run_command_props,
                    "required": if bound { json!(["command"]) } else { json!(["command", "project"]) },
                },
            }),
            json!({
                "name": "run_action",
                "description": "Run a named, owner-confirmed action from the project's action list (.agent/actions.json) — the preferred way to run tests/builds/linters that exist as actions. Same allowlist rules as run_command.",
                "inputSchema": {
                    "type": "object",
                    "properties": run_action_props,
                    "required": if bound { json!(["name"]) } else { json!(["name", "project"]) },
                },
            }),
            json!({
                "name": "list_actions",
                "description": "List the project's action list (.agent/actions.json): named, owner-approved commands for this project.",
                "inputSchema": {"type": "object", "properties": project_property},
            }),
        ]
    }

    fn call_tool(&self, name: Option<&str>, arguments: &Map<String, Value>) -> Value {
        match name {
            Some("run_command") => self.run_command(arguments),
            Some("run_action") => self.run_action(arguments),
            Some("list_actions") => self.list_actions(arguments),
            other => error_result(format!("Unbekanntes Tool: {}", other.unwrap_or("(none)"))),
        }
    }
}

fn trimmed_string(arguments: &Map<String, Value>, key: &str) -> Option<String> {
    arguments
        .get(key)
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(String::from)
}

fn canonical(path: &std::path::Path) -> PathBuf {
    path.canonicalize().unwrap_or_else(|_| path.to_path_buf())
}

#[cfg(test)]
mod tests {
    use super::*;
    use speccify_mcp_core::handle;

    fn project(label: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-exec-{label}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join(".agent")).unwrap();
        std::fs::write(
            dir.join(".agent/exec-allowlist.json"),
            r#"[{"pattern":"echo","permanent":true}]"#,
        )
        .unwrap();
        dir
    }

    fn call(server: &ExecMcp, name: &str, args: Value) -> Value {
        server.call_tool(Some(name), args.as_object().unwrap())
    }

    #[test]
    fn multi_initialize_and_tools_list() {
        let server = ExecMcp::new(None, 5.0);
        let init = handle(
            &server,
            &json!({"jsonrpc":"2.0","id":1,"method":"initialize"}),
        )
        .unwrap();
        assert_eq!(init["result"]["serverInfo"]["mode"], "multi");
        assert!(init["result"]["serverInfo"].get("projectRoot").is_none());
        let tools = handle(
            &server,
            &json!({"jsonrpc":"2.0","id":2,"method":"tools/list"}),
        )
        .unwrap();
        let names: Vec<&str> = tools["result"]["tools"]
            .as_array()
            .unwrap()
            .iter()
            .map(|tool| tool["name"].as_str().unwrap())
            .collect();
        assert_eq!(names, vec!["run_command", "run_action", "list_actions"]);
        assert_eq!(
            tools["result"]["tools"][0]["inputSchema"]["required"],
            json!(["command", "project"])
        );
    }

    #[test]
    fn allowed_denied_and_missing() {
        let dir = project("run");
        let server = ExecMcp::new(None, 10.0);
        let ok = call(
            &server,
            "run_command",
            json!({"command":"echo hi","project": dir}),
        );
        assert_eq!(ok["isError"], false);
        let payload: Value =
            serde_json::from_str(ok["content"][0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(payload["exit_code"], 0);
        assert_eq!(payload["stdout"], "hi\n");

        let denied = call(
            &server,
            "run_command",
            json!({"command":"git status","project": dir}),
        );
        assert_eq!(denied["isError"], true);
        assert!(
            denied["content"][0]["text"]
                .as_str()
                .unwrap()
                .contains("pending list in the app")
        );
        // Pending wurde notiert.
        let pending = std::fs::read_to_string(dir.join(".agent/exec-pending.json")).unwrap();
        assert!(pending.contains("git status"));

        let missing = call(&server, "run_command", json!({"command":"echo hi"}));
        assert_eq!(missing["content"][0]["text"], MULTI_MISSING);
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn run_action_paths() {
        let dir = project("action");
        std::fs::write(
            dir.join(".agent/actions.json"),
            r#"[{"name":"Echo","command":"echo a","confirmed":true},{"name":"Nope","command":"echo b","confirmed":false}]"#,
        )
        .unwrap();
        let server = ExecMcp::new(None, 10.0);
        let ok = call(&server, "run_action", json!({"name":"Echo","project": dir}));
        assert_eq!(ok["isError"], false);
        let unknown = call(&server, "run_action", json!({"name":"Zzz","project": dir}));
        assert!(
            unknown["content"][0]["text"]
                .as_str()
                .unwrap()
                .contains("Known actions: Echo, Nope")
        );
        let unconfirmed = call(&server, "run_action", json!({"name":"Nope","project": dir}));
        assert!(
            unconfirmed["content"][0]["text"]
                .as_str()
                .unwrap()
                .contains("not confirmed yet")
        );
        let _ = std::fs::remove_dir_all(&dir);
    }
}
