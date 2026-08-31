//! Projekt-Aktionen (Plan projektfenster.md, P5/W5, D27/D28).
//!
//! `.agent/actions.json` ist ein JSON-Array benannter Kommandos; die
//! `command`-Zeile ist zugleich die Id (Dedupe-Schlüssel). Befehle sind
//! **argv ohne Shell** — Verkettungen gehören in ein Script. Abgelehnte
//! Agent-Befehle liegen in `.agent/exec-pending.json` und erscheinen als
//! Vorschläge; **ein** Bestätigen macht daraus eine Aktion **und** einen
//! permanenten Allowlist-Eintrag (`.agent/exec-allowlist.json`,
//! wire-kompatibel zum exec-MCP). Ausführung nativ (D28): die App spawnt
//! selbst, streamt Zeilen als Events und killt beim Stop.

use std::collections::HashMap;
use std::io::BufRead;
use std::path::Path;
use std::sync::Mutex;

use serde::{Deserialize, Serialize};
use tauri::{Emitter, Manager, State};

use crate::project_cmd::resolve_project_root;

#[derive(Serialize, Deserialize, Clone)]
pub struct ActionInput {
    pub name: String,
    #[serde(default)]
    pub kind: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub label: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub options: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub default: Option<String>,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct ProjectAction {
    pub name: String,
    pub command: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(default = "default_source")]
    pub source: String,
    #[serde(default)]
    pub confirmed: bool,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub toolbar: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub shortcut: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub inputs: Vec<ActionInput>,
    #[serde(default = "default_target")]
    pub target: String,
}

fn default_source() -> String {
    "bo".into()
}
fn default_target() -> String {
    "local".into()
}

#[derive(Serialize, Deserialize, Clone)]
pub struct PendingCommand {
    pub command: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub requested_at: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct AllowlistEntry {
    pattern: String,
    permanent: bool,
}

fn read_json_array<T: serde::de::DeserializeOwned>(path: &Path) -> Vec<T> {
    std::fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_default()
}

fn write_json_array<T: Serialize>(path: &Path, entries: &[T]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let text = serde_json::to_string_pretty(entries).map_err(|e| e.to_string())?;
    std::fs::write(path, text + "\n").map_err(|e| format!("{}: {e}", path.display()))
}

fn actions_path(root: &Path) -> std::path::PathBuf {
    root.join(".agent/actions.json")
}

#[derive(Serialize)]
pub struct ActionsSnapshot {
    actions: Vec<ProjectAction>,
    pending: Vec<PendingCommand>,
}

#[tauri::command]
pub fn project_actions(project: String) -> Result<ActionsSnapshot, String> {
    let root = resolve_project_root(&project)?;
    let actions: Vec<ProjectAction> = read_json_array(&actions_path(&root));
    let known: std::collections::HashSet<&str> = actions
        .iter()
        .map(|action| action.command.as_str())
        .collect();
    // Pending-Einträge, die es schon als Aktion gibt, nicht doppelt zeigen.
    let pending: Vec<PendingCommand> = read_json_array(&root.join(".agent/exec-pending.json"))
        .into_iter()
        .filter(|entry: &PendingCommand| !known.contains(entry.command.as_str()))
        .collect();
    Ok(ActionsSnapshot { actions, pending })
}

/// Anlegen oder Ändern — die `command`-Id entscheidet.
#[tauri::command]
pub fn project_action_upsert(project: String, action: ProjectAction) -> Result<(), String> {
    if action.name.trim().is_empty() || action.command.trim().is_empty() {
        return Err("Name und Kommando dürfen nicht leer sein.".into());
    }
    let root = resolve_project_root(&project)?;
    let mut actions: Vec<ProjectAction> = read_json_array(&actions_path(&root));
    match actions
        .iter_mut()
        .find(|existing| existing.command == action.command)
    {
        Some(existing) => *existing = action,
        None => actions.push(action),
    }
    write_json_array(&actions_path(&root), &actions)
}

#[tauri::command]
pub fn project_action_delete(project: String, command: String) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let mut actions: Vec<ProjectAction> = read_json_array(&actions_path(&root));
    actions.retain(|action| action.command != command);
    write_json_array(&actions_path(&root), &actions)
}

/// Bestätigt einen Vorschlag (unbestätigte Aktion **oder** Pending-Eintrag):
/// Aktion wird `confirmed`, der Befehl wandert **permanent** in die
/// Exec-Allowlist, ein Pending-Eintrag verschwindet — ein Approval genügt.
#[tauri::command]
pub fn project_action_confirm(project: String, command: String) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let mut actions: Vec<ProjectAction> = read_json_array(&actions_path(&root));
    match actions.iter_mut().find(|action| action.command == command) {
        Some(action) => action.confirmed = true,
        None => actions.push(ProjectAction {
            name: suggested_name(&command),
            command: command.clone(),
            description: None,
            source: "agent".into(),
            confirmed: true,
            toolbar: false,
            shortcut: None,
            inputs: Vec::new(),
            target: "local".into(),
        }),
    }
    write_json_array(&actions_path(&root), &actions)?;

    let allowlist_path = root.join(".agent/exec-allowlist.json");
    let mut allowlist: Vec<AllowlistEntry> = read_json_array(&allowlist_path);
    if !allowlist.iter().any(|entry| entry.pattern == command) {
        allowlist.push(AllowlistEntry {
            pattern: command.clone(),
            permanent: true,
        });
        write_json_array(&allowlist_path, &allowlist)?;
    }

    let pending_path = root.join(".agent/exec-pending.json");
    let mut pending: Vec<PendingCommand> = read_json_array(&pending_path);
    let before = pending.len();
    pending.retain(|entry| entry.command != command);
    if pending.len() != before {
        if pending.is_empty() {
            let _ = std::fs::remove_file(&pending_path);
        } else {
            write_json_array(&pending_path, &pending)?;
        }
    }
    Ok(())
}

/// Kurzname für importierte Agent-Befehle („npm test" → „npm test", lange
/// Kommandos aufs Wesentliche gekürzt).
fn suggested_name(command: &str) -> String {
    let words: Vec<&str> = command.split_whitespace().take(3).collect();
    if words.is_empty() {
        "Aktion".into()
    } else {
        words.join(" ")
    }
}

// --- Ausführung (D28: nativ spawnen, streamen, Stop killt) --------------------

/// Lauf-Id (= command) → Kind. Drop killt Reste beim App-Ende.
pub struct ActionRuns(Mutex<HashMap<String, std::process::Child>>);

impl Default for ActionRuns {
    fn default() -> Self {
        Self(Mutex::new(HashMap::new()))
    }
}

impl Drop for ActionRuns {
    fn drop(&mut self) {
        if let Ok(mut runs) = self.0.lock() {
            for child in runs.values_mut() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

#[derive(Clone, Serialize)]
struct ActionLine {
    run_id: String,
    line: String,
}

#[derive(Clone, Serialize)]
struct ActionExit {
    run_id: String,
    exit_code: Option<i32>,
    duration_ms: u64,
    error: Option<String>,
}

/// Startet die (bereits platzhalter-substituierte) Kommandozeile als argv
/// ohne Shell im Projekt-cwd. Zeilen kommen als `action-output`-Events,
/// das Ende als `action-exit`; `run_id` ist die command-Id der Aktion.
#[tauri::command]
pub fn project_action_run(
    window: tauri::WebviewWindow,
    state: State<ActionRuns>,
    project: String,
    run_id: String,
    command_line: String,
) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let argv = shell_words::split(&command_line).map_err(|e| format!("Kommandozeile: {e}"))?;
    let Some((program, args)) = argv.split_first() else {
        return Err("Leeres Kommando.".into());
    };
    {
        let runs = state.0.lock().unwrap();
        if runs.contains_key(&run_id) {
            return Err("Diese Aktion läuft schon.".into());
        }
    }

    let mut child = std::process::Command::new(program)
        .args(args)
        .current_dir(&root)
        .env("PATH", crate::augmented_path())
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| format!("{program}: {e}"))?;

    let started = std::time::Instant::now();
    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    state.0.lock().unwrap().insert(run_id.clone(), child);

    let spawn_reader =
        |window: tauri::WebviewWindow, run_id: String, reader: Box<dyn std::io::Read + Send>| {
            std::thread::spawn(move || {
                let buffered = std::io::BufReader::new(reader);
                for line in buffered.lines().map_while(Result::ok) {
                    let _ = window.emit(
                        "action-output",
                        ActionLine {
                            run_id: run_id.clone(),
                            line,
                        },
                    );
                }
            })
        };
    let out_handle = stdout.map(|out| spawn_reader(window.clone(), run_id.clone(), Box::new(out)));
    let err_handle = stderr.map(|err| spawn_reader(window.clone(), run_id.clone(), Box::new(err)));

    // Warte-Thread: Reader auslaufen lassen, Exit melden, Registry räumen.
    let app = window.app_handle().clone();
    let label = window.label().to_string();
    std::thread::spawn(move || {
        if let Some(handle) = out_handle {
            let _ = handle.join();
        }
        if let Some(handle) = err_handle {
            let _ = handle.join();
        }
        let state: State<ActionRuns> = app.state();
        let child = state.0.lock().unwrap().remove(&run_id);
        let (exit_code, error) = match child {
            Some(mut child) => match child.wait() {
                Ok(status) => (status.code(), None),
                Err(e) => (None, Some(e.to_string())),
            },
            None => (None, Some("Gestoppt.".into())),
        };
        if let Some(window) = app.get_webview_window(&label) {
            let _ = window.emit(
                "action-exit",
                ActionExit {
                    run_id,
                    exit_code,
                    duration_ms: started.elapsed().as_millis() as u64,
                    error,
                },
            );
        }
    });
    Ok(())
}

/// Stop = Prozess killen; der Warte-Thread meldet danach den Exit.
#[tauri::command]
pub fn project_action_stop(state: State<ActionRuns>, run_id: String) -> Result<bool, String> {
    let mut runs = state.0.lock().unwrap();
    match runs.get_mut(&run_id) {
        Some(child) => {
            let _ = child.kill();
            Ok(true)
        }
        None => Ok(false),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(test: &str) -> std::path::PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-actions-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join(".agent")).unwrap();
        dir
    }

    #[test]
    fn actions_roundtrip_and_unknown_fields_survive_reading() {
        let dir = fixture("roundtrip");
        let project = dir.to_string_lossy().into_owned();
        // Datei mit unbekanntem Input-Kind und Parallels-Target (tolerant).
        std::fs::write(
            dir.join(".agent/actions.json"),
            r#"[{"name":"SPM tests","command":"swift test","description":"…","source":"agent","confirmed":true,"shortcut":"cmd-u","inputs":[{"name":"file","kind":"hologram"}],"target":"parallels"}]"#,
        )
        .unwrap();
        let snapshot = project_actions(project.clone()).unwrap();
        assert_eq!(snapshot.actions.len(), 1);
        assert_eq!(snapshot.actions[0].inputs[0].kind, "hologram");
        assert_eq!(snapshot.actions[0].target, "parallels");

        project_action_upsert(
            project.clone(),
            ProjectAction {
                name: "Echo".into(),
                command: "echo hallo".into(),
                description: Some("Sagt hallo.".into()),
                source: "bo".into(),
                confirmed: true,
                toolbar: false,
                shortcut: None,
                inputs: vec![],
                target: "local".into(),
            },
        )
        .unwrap();
        let snapshot = project_actions(project.clone()).unwrap();
        assert_eq!(snapshot.actions.len(), 2);

        project_action_delete(project.clone(), "swift test".into()).unwrap();
        let snapshot = project_actions(project).unwrap();
        assert_eq!(snapshot.actions.len(), 1);
        assert_eq!(snapshot.actions[0].command, "echo hallo");

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn confirming_a_pending_command_creates_action_allowlist_and_clears_pending() {
        let dir = fixture("confirm");
        let project = dir.to_string_lossy().into_owned();
        std::fs::write(
            dir.join(".agent/exec-pending.json"),
            r#"[{"command":"npm test","requested_at":"2026-08-31T10:00:00Z"},{"command":"cargo build","requested_at":"2026-08-31T10:01:00Z"}]"#,
        )
        .unwrap();

        let snapshot = project_actions(project.clone()).unwrap();
        assert_eq!(snapshot.pending.len(), 2);

        project_action_confirm(project.clone(), "npm test".into()).unwrap();

        let snapshot = project_actions(project.clone()).unwrap();
        assert_eq!(snapshot.pending.len(), 1); // cargo build bleibt
        let action = &snapshot.actions[0];
        assert_eq!(action.command, "npm test");
        assert!(action.confirmed);
        assert_eq!(action.source, "agent");

        let allowlist: Vec<AllowlistEntry> =
            read_json_array(&dir.join(".agent/exec-allowlist.json"));
        assert!(allowlist
            .iter()
            .any(|entry| entry.pattern == "npm test" && entry.permanent));

        // Nochmal bestätigen ist idempotent (kein Allowlist-Duplikat).
        project_action_confirm(project.clone(), "npm test".into()).unwrap();
        let allowlist: Vec<AllowlistEntry> =
            read_json_array(&dir.join(".agent/exec-allowlist.json"));
        assert_eq!(
            allowlist
                .iter()
                .filter(|entry| entry.pattern == "npm test")
                .count(),
            1
        );

        let _ = std::fs::remove_dir_all(&dir);
    }
}
