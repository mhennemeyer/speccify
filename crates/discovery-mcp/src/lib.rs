//! Discovery-MCP (Plan toolkit-discovery-terminal.md, T3/D2): Agents
//! entdecken hierüber alle MCPs (inkl. fertiger Client-Config) und
//! Tools/Aktionen. Erster externer Client: iKanbanAi.
//!
//! Tools: `mcp_list`, `tools_list`, `actions_propose`, `scaffold`.
//! Aktionen-Format: `schema/actions.schema.json` (iKanbanAi-kompatibel).

use std::path::{Path, PathBuf};

use serde_json::{Map, Value, json};
use speccify_mcp_core::{ToolServer, error_result, text_result};
use speccify_toolbox::{
    Manifest, client_config, http_port, load_all, probe_port, scaffold as scaffold_manifest,
};

pub const DEFAULT_PORT: u16 = 8767;

pub struct DiscoveryMcp {
    /// Working Dir (Settings der Desktop-App bzw. `--working-dir`).
    pub working_dir: Option<PathBuf>,
    /// `~/.speccify` (überschreibbar für Tests).
    pub speccify_home: Option<PathBuf>,
}

impl DiscoveryMcp {
    pub fn from_env() -> Self {
        let home = std::env::var("HOME").ok().map(PathBuf::from);
        let speccify_home = home.map(|home| home.join(".speccify"));
        let working_dir = speccify_home
            .as_ref()
            .and_then(|dir| read_settings_working_dir(&dir.join("settings.json")));
        Self {
            working_dir,
            speccify_home,
        }
    }

    fn global_toolbox_dir(&self) -> Option<PathBuf> {
        self.speccify_home.as_ref().map(|dir| dir.join("toolbox"))
    }

    fn global_actions_path(&self) -> Option<PathBuf> {
        self.speccify_home
            .as_ref()
            .map(|dir| dir.join("actions.json"))
    }

    fn manifests(&self) -> (Vec<Manifest>, Vec<String>) {
        load_all(
            self.global_toolbox_dir().as_deref(),
            self.working_dir.as_deref(),
        )
    }

    /// Ziel-Verzeichnis eines Aufrufs: explizites `project` (absoluter
    /// Pfad) oder das Working Dir.
    fn resolve_project(&self, arguments: &Map<String, Value>) -> Result<PathBuf, String> {
        if let Some(raw) = arguments.get("project") {
            let raw = raw
                .as_str()
                .ok_or("'project' muss ein String (absoluter Pfad) sein.")?;
            let path = PathBuf::from(raw);
            if !path.is_absolute() {
                return Err(format!("'project' muss absolut sein: '{raw}'"));
            }
            if !path.is_dir() {
                return Err(format!("'project' existiert nicht: {raw}"));
            }
            return Ok(path);
        }
        self.working_dir.clone().ok_or_else(|| {
            "Kein Working Dir gesetzt (Settings) und kein 'project' übergeben.".into()
        })
    }

    // -- Tools ------------------------------------------------------------

    fn mcp_list(&self) -> Value {
        let (manifests, warnings) = self.manifests();
        let servers: Vec<Value> = manifests
            .iter()
            .filter(|manifest| manifest.kind == "mcp")
            .map(|manifest| {
                let port = http_port(manifest);
                let running = port.map(probe_port);
                let url = port.map(|port| format!("http://127.0.0.1:{port}"));
                json!({
                    "slug": manifest.slug,
                    "name": manifest.name,
                    "description": manifest.description,
                    "tags": manifest.tags,
                    "source": manifest.source,
                    "transport": manifest.run.as_ref().map(|run| run.transport.clone()),
                    "run": manifest.run,
                    "requires_binaries": manifest.requires_binaries,
                    "url": url,
                    "running": running,
                    "client_config": client_config(manifest),
                })
            })
            .collect();
        text_result(
            json!({"servers": servers, "warnings": warnings}).to_string(),
            false,
        )
    }

    fn tools_list(&self, arguments: &Map<String, Value>) -> Value {
        let (manifests, warnings) = self.manifests();
        let tools: Vec<&Manifest> = manifests
            .iter()
            .filter(|manifest| manifest.kind == "tool")
            .collect();
        let global_actions = self
            .global_actions_path()
            .map(|path| read_actions(&path))
            .unwrap_or_default();
        // `project` ist hier optional UND darf fehlen, auch ohne Working
        // Dir — dann gibt es einfach keine Projekt-Aktionen.
        let project_actions = match self.resolve_project(arguments) {
            Ok(root) => read_actions(&root.join(".agent").join("actions.json")),
            Err(_) => Vec::new(),
        };
        text_result(
            json!({
                "tools": tools,
                "actions": {"global": global_actions, "project": project_actions},
                "warnings": warnings,
            })
            .to_string(),
            false,
        )
    }

    fn actions_propose(&self, arguments: &Map<String, Value>) -> Value {
        let name = match required_string(arguments, "name") {
            Ok(name) => name,
            Err(error) => return error_result(error),
        };
        let command = match required_string(arguments, "command") {
            Ok(command) => command,
            Err(error) => return error_result(error),
        };
        let root = match self.resolve_project(arguments) {
            Ok(root) => root,
            Err(error) => return error_result(error),
        };
        let path = root.join(".agent").join("actions.json");
        let mut actions = read_actions(&path);
        if actions
            .iter()
            .any(|action| action.get("command").and_then(Value::as_str) == Some(command.as_str()))
        {
            return text_result(
                json!({"created": false, "reason": "duplicate"}).to_string(),
                false,
            );
        }
        let mut entry = Map::new();
        entry.insert("name".into(), Value::String(name));
        entry.insert("command".into(), Value::String(command));
        if let Some(description) = arguments.get("description").and_then(Value::as_str) {
            entry.insert("description".into(), Value::String(description.into()));
        }
        entry.insert("source".into(), Value::String("agent".into()));
        entry.insert("confirmed".into(), Value::Bool(false));
        entry.insert("toolbar".into(), Value::Bool(false));
        actions.push(Value::Object(entry));
        if let Err(error) = write_actions(&path, &actions) {
            return error_result(error);
        }
        text_result(
            json!({"created": true, "path": path.display().to_string()}).to_string(),
            false,
        )
    }

    fn scaffold(&self, arguments: &Map<String, Value>) -> Value {
        let slug = match required_string(arguments, "slug") {
            Ok(slug) => slug,
            Err(error) => return error_result(error),
        };
        let kind = arguments
            .get("kind")
            .and_then(Value::as_str)
            .unwrap_or("tool");
        let name = arguments.get("name").and_then(Value::as_str).unwrap_or("");
        let root = match self.resolve_project(arguments) {
            Ok(root) => root,
            Err(error) => return error_result(error),
        };
        match scaffold_manifest(&root.join(".speccify").join("toolbox"), &slug, kind, name) {
            Ok(path) => text_result(
                json!({"created": true, "path": path.display().to_string()}).to_string(),
                false,
            ),
            Err(error) => error_result(error),
        }
    }
}

impl ToolServer for DiscoveryMcp {
    fn server_info(&self) -> Value {
        json!({
            "name": "speccify-discovery-mcp",
            "version": env!("CARGO_PKG_VERSION"),
            "mode": "discovery",
        })
    }

    fn tool_descriptors(&self) -> Vec<Value> {
        let project_property = json!({
            "type": "string",
            "description": "Absolute path of the target project. Optional — defaults to the configured working dir.",
        });
        vec![
            json!({
                "name": "mcp_list",
                "description": "List all known MCP servers (toolbox manifests) with run spec, live status and a ready-to-use client_config snippet for .mcp.json.",
                "inputSchema": {"type": "object", "properties": {}},
            }),
            json!({
                "name": "tools_list",
                "description": "List toolbox tools plus the action lists (global + project .agent/actions.json). Prefer running actions via the exec MCP's run_action.",
                "inputSchema": {"type": "object", "properties": {"project": project_property}},
            }),
            json!({
                "name": "actions_propose",
                "description": "Propose a named CLI action for the project (source=agent, confirmed=false); the owner confirms it in the app. Deduplicated by command.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Display name, e.g. \"Tests\"."},
                        "command": {"type": "string", "description": "The command line, e.g. \"npm test\"."},
                        "description": {"type": "string"},
                        "project": project_property,
                    },
                    "required": ["name", "command"],
                },
            }),
            json!({
                "name": "scaffold",
                "description": "Create a new toolbox manifest (.speccify/toolbox/<slug>.toml) in the project/working dir. Never overwrites.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "a-z, 0-9 and '-'"},
                        "kind": {"type": "string", "enum": ["tool", "mcp", "kb"]},
                        "name": {"type": "string"},
                        "project": project_property,
                    },
                    "required": ["slug"],
                },
            }),
        ]
    }

    fn call_tool(&self, name: Option<&str>, arguments: &Map<String, Value>) -> Value {
        match name {
            Some("mcp_list") => self.mcp_list(),
            Some("tools_list") => self.tools_list(arguments),
            Some("actions_propose") => self.actions_propose(arguments),
            Some("scaffold") => self.scaffold(arguments),
            other => error_result(format!("Unbekanntes Tool: {}", other.unwrap_or("(none)"))),
        }
    }
}

// --- Helpers -------------------------------------------------------------------

fn required_string(arguments: &Map<String, Value>, key: &str) -> Result<String, String> {
    arguments
        .get(key)
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(String::from)
        .ok_or_else(|| format!("'{key}' (String) ist erforderlich."))
}

fn read_settings_working_dir(path: &Path) -> Option<PathBuf> {
    let text = std::fs::read_to_string(path).ok()?;
    let value: Value = serde_json::from_str(&text).ok()?;
    let raw = value.get("working_dir")?.as_str()?;
    let expanded = if let Some(rest) = raw.strip_prefix("~/") {
        PathBuf::from(std::env::var("HOME").ok()?).join(rest)
    } else {
        PathBuf::from(raw)
    };
    expanded.is_dir().then_some(expanded)
}

fn read_actions(path: &Path) -> Vec<Value> {
    let Ok(text) = std::fs::read_to_string(path) else {
        return Vec::new();
    };
    match serde_json::from_str::<Value>(&text) {
        Ok(Value::Array(actions)) => actions,
        _ => Vec::new(),
    }
}

fn write_actions(path: &Path, actions: &[Value]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let json =
        serde_json::to_string_pretty(&Value::Array(actions.to_vec())).map_err(|e| e.to_string())?;
    std::fs::write(path, json + "\n").map_err(|e| format!("{}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use speccify_mcp_core::handle;

    fn temp_dir(label: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-discovery-{label}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn server_with(working: &Path) -> DiscoveryMcp {
        DiscoveryMcp {
            working_dir: Some(working.to_path_buf()),
            speccify_home: None,
        }
    }

    fn content_json(result: &Value) -> Value {
        let text = result["content"][0]["text"].as_str().unwrap();
        serde_json::from_str(text).unwrap()
    }

    #[test]
    fn initialize_and_tools_list_shape() {
        let server = DiscoveryMcp {
            working_dir: None,
            speccify_home: None,
        };
        let init = handle(
            &server,
            &json!({"jsonrpc":"2.0","id":1,"method":"initialize"}),
        )
        .unwrap();
        assert_eq!(init["result"]["serverInfo"]["mode"], "discovery");
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
        assert_eq!(
            names,
            vec!["mcp_list", "tools_list", "actions_propose", "scaffold"]
        );
    }

    #[test]
    fn mcp_list_contains_builtins_with_client_config() {
        let working = temp_dir("mcplist");
        let result = server_with(&working).mcp_list();
        let body = content_json(&result);
        let servers = body["servers"].as_array().unwrap();
        let discovery = servers
            .iter()
            .find(|server| server["slug"] == "speccify-discovery")
            .unwrap();
        assert_eq!(
            discovery["client_config"],
            json!({"type": "http", "url": "http://127.0.0.1:8767"})
        );
        let playwright = servers
            .iter()
            .find(|server| server["slug"] == "playwright")
            .unwrap();
        assert_eq!(playwright["client_config"]["command"], "npx");
        assert_eq!(playwright["running"], Value::Null);
        let _ = std::fs::remove_dir_all(&working);
    }

    #[test]
    fn tools_list_merges_project_actions() {
        let working = temp_dir("toolslist");
        let agent = working.join(".agent");
        std::fs::create_dir_all(&agent).unwrap();
        std::fs::write(
            agent.join("actions.json"),
            r#"[{"name": "Tests", "command": "npm test", "confirmed": true}]"#,
        )
        .unwrap();
        let result = server_with(&working).tools_list(&Map::new());
        let body = content_json(&result);
        assert_eq!(body["actions"]["project"][0]["command"], "npm test");
        let _ = std::fs::remove_dir_all(&working);
    }

    #[test]
    fn actions_propose_writes_and_dedupes() {
        let working = temp_dir("propose");
        let server = server_with(&working);
        let mut arguments = Map::new();
        arguments.insert("name".into(), json!("Tests"));
        arguments.insert("command".into(), json!("npm test"));

        let first = content_json(&server.actions_propose(&arguments));
        assert_eq!(first["created"], true);
        let second = content_json(&server.actions_propose(&arguments));
        assert_eq!(second["created"], false);

        let actions = read_actions(&working.join(".agent/actions.json"));
        assert_eq!(actions.len(), 1);
        assert_eq!(actions[0]["source"], "agent");
        assert_eq!(actions[0]["confirmed"], false);
        let _ = std::fs::remove_dir_all(&working);
    }

    #[test]
    fn scaffold_creates_manifest_in_working_dir() {
        let working = temp_dir("scaffold");
        let server = server_with(&working);
        let mut arguments = Map::new();
        arguments.insert("slug".into(), json!("mein-tool"));
        arguments.insert("kind".into(), json!("tool"));
        let result = content_json(&server.scaffold(&arguments));
        assert_eq!(result["created"], true);
        assert!(working.join(".speccify/toolbox/mein-tool.toml").is_file());
        // Danach taucht es in tools_list auf (Quelle workingdir).
        let tools = content_json(&server.tools_list(&Map::new()));
        assert!(
            tools["tools"]
                .as_array()
                .unwrap()
                .iter()
                .any(|tool| tool["slug"] == "mein-tool")
        );
        let _ = std::fs::remove_dir_all(&working);
    }

    #[test]
    fn propose_requires_fields_and_project_when_no_working_dir() {
        let server = DiscoveryMcp {
            working_dir: None,
            speccify_home: None,
        };
        let missing = server.actions_propose(&Map::new());
        assert_eq!(missing["isError"], true);
        let mut arguments = Map::new();
        arguments.insert("name".into(), json!("X"));
        arguments.insert("command".into(), json!("echo x"));
        let no_project = server.actions_propose(&arguments);
        assert_eq!(no_project["isError"], true);
    }
}
