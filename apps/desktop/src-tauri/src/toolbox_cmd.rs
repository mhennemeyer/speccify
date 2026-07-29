//! Toolbox-Commands der App (Plan toolkit-discovery-terminal.md, T2):
//! Library-Tab liest die Manifeste nativ (statt `dotagent registry list`),
//! Scaffold legt neue Manifeste im Working Dir an.

use std::path::PathBuf;

use serde::Serialize;
use serde_json::Value;
use speccify_toolbox::{client_config, http_port, load_all, probe_port, scaffold, Manifest};

use crate::settings;
use crate::sidecar::{self, BinarySource};

#[derive(Serialize)]
pub struct ToolboxList {
    manifests: Vec<Manifest>,
    warnings: Vec<String>,
}

fn global_toolbox_dir() -> Option<PathBuf> {
    std::env::var("HOME")
        .ok()
        .map(|home| PathBuf::from(home).join(".speccify").join("toolbox"))
}

/// Working Dir aus den Settings — nicht gesetzt/ungültig ⇒ None (die
/// Bibliothek zeigt dann builtin + global; Fehler gehören in den Settings-Tab).
fn working_dir_from_settings() -> Option<PathBuf> {
    let settings = settings::get_settings().ok()?;
    let raw = settings.working_dir?;
    settings::resolve_working_dir(&raw).ok()
}

#[tauri::command]
pub fn toolbox_list() -> Result<ToolboxList, String> {
    let global = global_toolbox_dir();
    let working = working_dir_from_settings();
    let (manifests, warnings) = load_all(global.as_deref(), working.as_deref());
    Ok(ToolboxList {
        manifests,
        warnings,
    })
}

#[derive(Serialize)]
pub struct McpServerStatus {
    manifest: Manifest,
    port: Option<u16>,
    /// `Some(true/false)` für http-Server (Port-Probe); `None` für stdio
    /// (die startet der Client selbst).
    running: Option<bool>,
    binary_found: bool,
    /// Woher das Binary kommt: `bundled` (Sidecar im App-Bundle), `path`,
    /// `explicit` (Pfad im Manifest) oder `missing` (R5.1).
    binary_source: BinarySource,
    client_config: Option<Value>,
    /// Supervisor-Prozess-Id für spawn_process/kill_process.
    supervisor_id: String,
}

/// Server-Tab: alle Toolbox-MCPs mit Laufzeitstatus und Client-Config.
#[tauri::command]
pub fn mcp_status() -> Result<Vec<McpServerStatus>, String> {
    let global = global_toolbox_dir();
    let working = working_dir_from_settings();
    let (manifests, _warnings) = load_all(global.as_deref(), working.as_deref());
    Ok(manifests
        .into_iter()
        .filter(|manifest| manifest.kind == "mcp")
        .map(|manifest| {
            let port = http_port(&manifest);
            let running = port.map(probe_port);
            let binary_source = manifest
                .run
                .as_ref()
                .map(|run| sidecar::resolve(&run.command).1)
                .unwrap_or(BinarySource::Missing);
            McpServerStatus {
                port,
                running,
                binary_found: binary_source != BinarySource::Missing,
                binary_source,
                client_config: client_config(&manifest),
                supervisor_id: format!("mcp-{}", manifest.slug),
                manifest,
            }
        })
        .collect())
}

#[tauri::command]
pub fn toolbox_scaffold(slug: String, kind: String, name: String) -> Result<String, String> {
    let settings = settings::get_settings()?;
    let raw = settings
        .working_dir
        .ok_or("Kein Working Dir gesetzt — zuerst im Settings-Tab wählen.")?;
    let root = settings::resolve_working_dir(&raw)?;
    scaffold(
        &root.join(".speccify").join("toolbox"),
        slug.trim(),
        kind.trim(),
        name.trim(),
    )
    .map(|path| path.display().to_string())
}
