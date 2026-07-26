//! Parallels-MCP (Plan toolkit-discovery-terminal.md, T5): Rust-Port der
//! dotagent-Referenz. Baut/testet Mac-seitigen .NET-Code in einer
//! Windows-VM via `prlctl exec`. P0.2-Leitplanken fest eingebaut:
//! `prlctl exec` läuft als SYSTEM → `dotnet` mit vollem Pfad; Pfad-Mapping
//! `~/…` → `\\Mac\Home\…`; `chcp 65001` vor jedem Befehl. Sicherheitsmodell
//! wie Exec: Token-Präfix-Allowlist (`.agent/parallels-allowlist.json`,
//! Default nur `dotnet build/test/run`).

use std::path::{Path, PathBuf};

use serde_json::{Map, Value, json};
use speccify_mcp_core::allowlist::Allowlist;
use speccify_mcp_core::{ToolServer, error_result, text_result};

pub const DEFAULT_PORT: u16 = 8766;
pub const DEFAULT_VM_TIMEOUT_SECONDS: f64 = 300.0;
pub const DEFAULT_DOTNET_PATH: &str = "C:\\Program Files\\dotnet\\dotnet.exe";
pub const MAX_OUTPUT_CHARS: usize = 20_000;
const ALLOWLIST_FILE: &str = "parallels-allowlist.json";
const PENDING_FILE: &str = "parallels-pending.json";
pub const DEFAULT_ALLOWLIST: &[&str] = &[
    "dotnet build",
    "dotnet test",
    "dotnet run",
    "dotnet --info",
    "dotnet --version",
];

/// Ergebnis eines Prozessaufrufs (der Runner ist injizierbar für Tests).
pub struct RunOutput {
    pub code: Option<i32>,
    pub stdout: String,
    pub stderr: String,
}

pub enum RunError {
    NotFound,
    Timeout { stdout: String, stderr: String },
}

pub type Runner = dyn Fn(&[String], f64) -> Result<RunOutput, RunError> + Send + Sync;

/// Mac-Pfad → UNC-Pfad im Parallels-Home-Share (`\\Mac\Home\…`).
pub fn mac_to_vm_path(path: &Path, home: &Path) -> Result<String, String> {
    let base = home.canonicalize().unwrap_or_else(|_| home.to_path_buf());
    let resolved = path.canonicalize().unwrap_or_else(|_| path.to_path_buf());
    let relative = resolved.strip_prefix(&base).map_err(|_| {
        format!(
            "Pfad liegt außerhalb des Home-Shares (~): {}",
            path.display()
        )
    })?;
    Ok(format!(
        "\\\\Mac\\Home\\{}",
        relative.to_string_lossy().replace('/', "\\")
    ))
}

/// Windows-Quoting (analog `subprocess.list2cmdline`) — nur wo nötig.
fn quote_win(token: &str) -> String {
    if !token.is_empty() && !token.contains([' ', '\t', '"']) {
        return token.to_string();
    }
    let mut out = String::from("\"");
    let mut backslashes = 0;
    for ch in token.chars() {
        match ch {
            '\\' => {
                backslashes += 1;
                out.push('\\');
            }
            '"' => {
                for _ in 0..=backslashes {
                    out.push('\\');
                }
                backslashes = 0;
                out.push('"');
            }
            _ => {
                backslashes = 0;
                out.push(ch);
            }
        }
    }
    for _ in 0..backslashes {
        out.push('\\');
    }
    out.push('"');
    out
}

/// prlctl-Aufruf für einen VM-Befehl inkl. aller P0.2-Leitplanken.
pub fn build_exec_argv(vm: &str, command: &str, vm_cwd: &str, dotnet_path: &str) -> Vec<String> {
    let mut tokens = shlex::split(command).unwrap_or_default();
    if tokens.first().map(String::as_str) == Some("dotnet") {
        tokens[0] = dotnet_path.to_string();
    }
    let win_command = tokens
        .iter()
        .map(|token| quote_win(token))
        .collect::<Vec<_>>()
        .join(" ");
    let script = format!("chcp 65001 >nul && pushd {vm_cwd} && {win_command}");
    vec![
        "prlctl".into(),
        "exec".into(),
        vm.to_string(),
        "cmd".into(),
        "/c".into(),
        script,
    ]
}

#[derive(Clone)]
pub struct VmInfo {
    pub name: String,
    pub status: String,
    pub uuid: String,
}

/// Parst `prlctl list -a --json`.
pub fn parse_vm_list(text: &str) -> Vec<VmInfo> {
    match serde_json::from_str::<Value>(text) {
        Ok(Value::Array(items)) => items
            .into_iter()
            .filter_map(|item| {
                let object = item.as_object()?;
                Some(VmInfo {
                    name: string_field(object, "name"),
                    status: string_field(object, "status"),
                    uuid: string_field(object, "uuid"),
                })
            })
            .collect(),
        _ => Vec::new(),
    }
}

fn string_field(object: &Map<String, Value>, key: &str) -> String {
    object
        .get(key)
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string()
}

fn cap(text: &str, max: usize) -> (String, bool) {
    if text.chars().count() <= max {
        return (text.to_string(), false);
    }
    let truncated: String = text.chars().take(max).collect();
    (format!("{truncated}\n… [gekappt nach {max} Zeichen]"), true)
}

/// Führt prlctl aus (via Runner) und liefert ein agentenlesbares
/// Ergebnis-Objekt.
pub fn run_prlctl(argv: &[String], timeout: f64, runner: &Runner) -> Value {
    let started = std::time::Instant::now();
    match runner(argv, timeout) {
        Err(RunError::NotFound) => json!({
            "error": "prlctl nicht gefunden — Parallels Desktop Pro/Business nötig.",
            "exit_code": Value::Null,
        }),
        Err(RunError::Timeout { stdout, stderr }) => json!({
            "error": format!("Timeout nach {timeout:.0}s."),
            "exit_code": Value::Null,
            "stdout": cap(&stdout, MAX_OUTPUT_CHARS).0,
            "stderr": cap(&stderr, MAX_OUTPUT_CHARS).0,
        }),
        Ok(output) => {
            let (stdout, out_truncated) = cap(&output.stdout, MAX_OUTPUT_CHARS);
            let (stderr, err_truncated) = cap(&output.stderr, MAX_OUTPUT_CHARS);
            json!({
                "exit_code": output.code.map(Value::from).unwrap_or(Value::Null),
                "stdout": stdout,
                "stderr": stderr,
                "truncated": out_truncated || err_truncated,
                "duration_ms": started.elapsed().as_millis() as u64,
            })
        }
    }
}

pub struct ParallelsMcp {
    pub project_root: PathBuf,
    pub vm: Option<String>,
    pub dotnet_path: String,
    pub timeout: f64,
    pub home: PathBuf,
    runner: Box<Runner>,
}

impl ParallelsMcp {
    pub fn new(
        project_root: PathBuf,
        vm: Option<String>,
        home: PathBuf,
        runner: Box<Runner>,
    ) -> Self {
        let allowlist =
            Allowlist::with_files(project_root.join(".agent"), ALLOWLIST_FILE, PENDING_FILE);
        allowlist.seed_if_absent(DEFAULT_ALLOWLIST);
        Self {
            project_root,
            vm,
            dotnet_path: DEFAULT_DOTNET_PATH.to_string(),
            timeout: DEFAULT_VM_TIMEOUT_SECONDS,
            home,
            runner,
        }
    }

    fn allowlist(&self) -> Allowlist {
        Allowlist::with_files(
            self.project_root.join(".agent"),
            ALLOWLIST_FILE,
            PENDING_FILE,
        )
    }

    fn vms(&self) -> Vec<VmInfo> {
        let result = run_prlctl(
            &["prlctl".into(), "list".into(), "-a".into(), "--json".into()],
            self.timeout,
            &self.runner,
        );
        parse_vm_list(result.get("stdout").and_then(Value::as_str).unwrap_or(""))
    }

    /// Explizites Argument > Server-Config > erste laufende VM.
    fn resolve_vm(&self, arguments: &Map<String, Value>) -> Option<String> {
        if let Some(explicit) = arguments.get("vm").and_then(Value::as_str) {
            let explicit = explicit.trim();
            if !explicit.is_empty() {
                return Some(explicit.to_string());
            }
        }
        if let Some(vm) = &self.vm {
            return Some(vm.clone());
        }
        self.vms()
            .into_iter()
            .find(|vm| vm.status == "running")
            .map(|vm| vm.name)
    }

    fn vm_list(&self) -> Value {
        let vms: Vec<Value> = self
            .vms()
            .into_iter()
            .map(|vm| json!({"name": vm.name, "status": vm.status, "uuid": vm.uuid}))
            .collect();
        text_result(Value::Array(vms).to_string(), false)
    }

    fn vm_status(&self, arguments: &Map<String, Value>) -> Value {
        let Some(vm_name) = self.resolve_vm(arguments) else {
            return error_result("Keine VM gefunden (weder konfiguriert noch laufend).");
        };
        match self.vms().into_iter().find(|vm| vm.name == vm_name) {
            Some(vm) => text_result(
                json!({"name": vm.name, "status": vm.status, "uuid": vm.uuid}).to_string(),
                false,
            ),
            None => error_result(format!("VM nicht gefunden: {vm_name}")),
        }
    }

    fn vm_power(&self, arguments: &Map<String, Value>, action: &str) -> Value {
        let Some(vm_name) = self.resolve_vm(arguments) else {
            return error_result("Keine VM gefunden (weder konfiguriert noch laufend).");
        };
        let result = run_prlctl(
            &["prlctl".into(), action.into(), vm_name],
            self.timeout,
            &self.runner,
        );
        let is_error = result.get("exit_code").and_then(Value::as_i64) != Some(0);
        text_result(result.to_string(), is_error)
    }

    fn vm_exec(&self, arguments: &Map<String, Value>) -> Value {
        let command = arguments
            .get("command")
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|value| !value.is_empty());
        let Some(command) = command else {
            return error_result("vm_exec benötigt 'command' (String).");
        };

        let allowlist = self.allowlist();
        if !allowlist.is_allowed(command) {
            allowlist.record_pending(command);
            return error_result(format!(
                "Command not allowlisted: \"{command}\". It was recorded for approval — ask the \
                 project owner to approve it (.agent/parallels-pending.json), then try again."
            ));
        }

        let Some(vm_name) = self.resolve_vm(arguments) else {
            return error_result("Keine VM gefunden (weder konfiguriert noch laufend).");
        };

        let cwd = arguments
            .get("cwd")
            .and_then(Value::as_str)
            .filter(|value| !value.is_empty())
            .map(PathBuf::from)
            .unwrap_or_else(|| self.project_root.clone());
        let vm_cwd = match mac_to_vm_path(&cwd, &self.home) {
            Ok(vm_cwd) => vm_cwd,
            Err(error) => return error_result(error),
        };

        let argv = build_exec_argv(&vm_name, command, &vm_cwd, &self.dotnet_path);
        let result = run_prlctl(&argv, self.timeout, &self.runner);
        allowlist.consume(command);
        let is_error = result.get("exit_code").and_then(Value::as_i64) != Some(0);
        text_result(result.to_string(), is_error)
    }
}

impl ToolServer for ParallelsMcp {
    fn server_info(&self) -> Value {
        json!({"name": "speccify-parallels-mcp", "version": env!("CARGO_PKG_VERSION")})
    }

    fn tool_descriptors(&self) -> Vec<Value> {
        let vm_property = json!({
            "vm": {
                "type": "string",
                "description": "VM name; omitted = the server's configured/first running VM.",
            }
        });
        vec![
            json!({
                "name": "vm_list",
                "description": "List all Parallels VMs with status (running/stopped).",
                "inputSchema": {"type": "object", "properties": {}},
            }),
            json!({
                "name": "vm_status",
                "description": "Status of one Parallels VM.",
                "inputSchema": {"type": "object", "properties": vm_property},
            }),
            json!({
                "name": "vm_start",
                "description": "Start a Parallels VM.",
                "inputSchema": {"type": "object", "properties": vm_property},
            }),
            json!({
                "name": "vm_stop",
                "description": "Stop a Parallels VM.",
                "inputSchema": {"type": "object", "properties": vm_property},
            }),
            json!({
                "name": "vm_exec",
                "description": "Run an allowlisted command (e.g. \"dotnet build\", \"dotnet test\") inside the Windows VM, in a Mac directory mapped via the Parallels home share. Use this to build and test .NET code that lives on the Mac. Commands not on the allowlist are recorded for owner approval — mention that and continue; do not retry immediately.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command line, e.g. \"dotnet test\"."},
                        "cwd": {"type": "string", "description": "Mac working directory (absolute, inside ~). Default: the server's project root."},
                        "vm": {"type": "string", "description": "VM name; omitted = the server's configured/first running VM."},
                    },
                    "required": ["command"],
                },
            }),
        ]
    }

    fn call_tool(&self, name: Option<&str>, arguments: &Map<String, Value>) -> Value {
        match name {
            Some("vm_list") => self.vm_list(),
            Some("vm_status") => self.vm_status(arguments),
            Some("vm_start") => self.vm_power(arguments, "start"),
            Some("vm_stop") => self.vm_power(arguments, "stop"),
            Some("vm_exec") => self.vm_exec(arguments),
            other => error_result(format!("Unbekanntes Tool: {}", other.unwrap_or("(none)"))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Mutex};

    fn project(label: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-parallels-{label}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join(".agent")).unwrap();
        dir
    }

    /// Runner, der prlctl-Argv aufzeichnet und kanned-Output liefert.
    fn recording_runner(
        calls: Arc<Mutex<Vec<Vec<String>>>>,
        vm_list_json: &'static str,
    ) -> Box<Runner> {
        Box::new(move |argv: &[String], _timeout: f64| {
            calls.lock().unwrap().push(argv.to_vec());
            let stdout = if argv.contains(&"--json".to_string()) {
                vm_list_json.to_string()
            } else {
                String::new()
            };
            Ok(RunOutput {
                code: Some(0),
                stdout,
                stderr: String::new(),
            })
        })
    }

    #[test]
    fn seeds_default_allowlist_on_first_use() {
        let dir = project("seed");
        let calls = Arc::new(Mutex::new(Vec::new()));
        let _server = ParallelsMcp::new(
            dir.clone(),
            Some("Win11".into()),
            dir.clone(),
            recording_runner(calls, "[]"),
        );
        let text = std::fs::read_to_string(dir.join(".agent/parallels-allowlist.json")).unwrap();
        assert!(text.contains("dotnet build"));
        assert!(text.contains("dotnet test"));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn vm_exec_maps_path_and_uses_full_dotnet() {
        let dir = project("exec");
        let calls = Arc::new(Mutex::new(Vec::new()));
        let server = ParallelsMcp::new(
            dir.clone(),
            Some("Win11".into()),
            dir.clone(),
            recording_runner(Arc::clone(&calls), "[]"),
        );
        let mut args = Map::new();
        args.insert("command".into(), json!("dotnet build"));
        let result = server.vm_exec(&args);
        assert_eq!(result["isError"], false);
        let recorded = calls.lock().unwrap();
        let exec_call = recorded.last().unwrap();
        let script = exec_call.last().unwrap();
        assert!(script.contains("chcp 65001"));
        assert!(script.contains("\\\\Mac\\Home\\")); // cwd = project_root unter home
        assert!(script.contains("C:\\Program Files\\dotnet\\dotnet.exe"));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn vm_exec_denies_and_records_pending() {
        let dir = project("deny");
        let calls = Arc::new(Mutex::new(Vec::new()));
        let server = ParallelsMcp::new(
            dir.clone(),
            Some("Win11".into()),
            dir.clone(),
            recording_runner(calls, "[]"),
        );
        let mut args = Map::new();
        args.insert("command".into(), json!("del /s C:\\Windows"));
        let result = server.vm_exec(&args);
        assert_eq!(result["isError"], true);
        assert!(
            result["content"][0]["text"]
                .as_str()
                .unwrap()
                .contains("parallels-pending.json")
        );
        assert!(
            std::fs::read_to_string(dir.join(".agent/parallels-pending.json"))
                .unwrap()
                .contains("del /s")
        );
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn vm_status_resolves_and_reports() {
        let dir = project("status");
        let calls = Arc::new(Mutex::new(Vec::new()));
        let server = ParallelsMcp::new(
            dir.clone(),
            None,
            dir.clone(),
            recording_runner(
                calls,
                r#"[{"name":"Win11","status":"running","uuid":"u-1"}]"#,
            ),
        );
        let result = server.vm_status(&Map::new());
        let payload: Value =
            serde_json::from_str(result["content"][0]["text"].as_str().unwrap()).unwrap();
        assert_eq!(payload["name"], "Win11");
        assert_eq!(payload["status"], "running");
        let _ = std::fs::remove_dir_all(&dir);
    }
}
