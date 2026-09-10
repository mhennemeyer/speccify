//! Toolbox-Commands der App (Plan toolkit-discovery-terminal.md, T2):
//! Library-Tab liest die Manifeste nativ (statt `dotagent registry list`),
//! Scaffold legt neue Manifeste im Working Dir an.

use std::path::PathBuf;

use serde::Serialize;
use serde_json::Value;
use speccify_toolbox::{client_config, http_port, load_all, probe_port, scaffold, Manifest};
use tauri::AppHandle;

use crate::engine;
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
    /// Woher das Binary kommt: `bundled` (Sidecar im App-Bundle), `engine`
    /// (Python-Engine der App), `path`, `explicit` (Pfad im Manifest) oder
    /// `missing` (R5.1/R5.2).
    binary_source: BinarySource,
    /// Tatsächlich zu startendes Kommando (aufgelöst) — die UI schickt das an
    /// `spawn_process`, und die Client-Config zeigt denselben Pfad.
    resolved_command: String,
    resolved_args: Vec<String>,
    client_config: Option<Value>,
    /// Supervisor-Prozess-Id für spawn_process/kill_process.
    supervisor_id: String,
}

/// Auflösung eines Manifest-`[run]`-Blocks gegen die konkrete Installation.
///
/// Zusätzlich zur Sidecar-Reihenfolge (mitgeliefert > PATH) kennt sie die
/// Python-Engine der App (R5.2): `speccify-mcp` & Co. liegen dort in
/// `<venv>/bin`. Auch die Repo-Schreibweise `uv run <bin>` wird darauf
/// abgebildet — ohne Repo gäbe es sonst kein startbares Kommando.
fn resolve_run(
    app: &AppHandle,
    run: &speccify_toolbox::RunSpec,
) -> (String, Vec<String>, BinarySource) {
    if let Ok(bin_dir) = engine::venv_dir(app).map(|venv| engine::bin_dir(&venv)) {
        if let Some((command, args)) = engine_run(run, &bin_dir) {
            return (command, args, BinarySource::Engine);
        }
    }
    let (path, source) = sidecar::resolve(&run.command);
    let command = path
        .map(|p| p.display().to_string())
        .unwrap_or_else(|| run.command.clone());
    (command, run.args.clone(), source)
}

/// Bildet einen `[run]`-Block auf die Engine-venv ab, sofern er dort landet:
/// direkt (`speccify-mcp`) oder über die Repo-Schreibweise `uv run <bin>`.
fn engine_run(
    run: &speccify_toolbox::RunSpec,
    bin_dir: &std::path::Path,
) -> Option<(String, Vec<String>)> {
    if let Some(direct) = sidecar::find_in_dir(bin_dir, &run.command) {
        return Some((direct.display().to_string(), run.args.clone()));
    }
    if run.command == "uv" && run.args.first().map(String::as_str) == Some("run") {
        let name = run.args.get(1)?;
        if let Some(engine_bin) = sidecar::find_in_dir(bin_dir, name) {
            return Some((engine_bin.display().to_string(), run.args[2..].to_vec()));
        }
    }
    None
}

/// Server-Tab: alle Toolbox-MCPs mit Laufzeitstatus und Client-Config.
#[tauri::command]
pub fn mcp_status(app: AppHandle) -> Result<Vec<McpServerStatus>, String> {
    let global = global_toolbox_dir();
    let working = working_dir_from_settings();
    let (manifests, _warnings) = load_all(global.as_deref(), working.as_deref());
    Ok(manifests
        .into_iter()
        .filter(|manifest| manifest.kind == "mcp")
        .map(|manifest| {
            let port = http_port(&manifest);
            let running = port.map(probe_port);
            let (resolved_command, resolved_args, binary_source) = match manifest.run.as_ref() {
                Some(run) => resolve_run(&app, run),
                None => (String::new(), Vec::new(), BinarySource::Missing),
            };
            // Client-Config auf das aufgelöste Kommando ziehen: ein MCP-Client
            // startet stdio-Server ohne unseren PATH und braucht absolute Pfade.
            let mut resolved = manifest.clone();
            if let Some(run) = resolved.run.as_mut() {
                run.command = resolved_command.clone();
                run.args = resolved_args.clone();
            }
            McpServerStatus {
                port,
                running,
                binary_found: binary_source != BinarySource::Missing,
                binary_source,
                resolved_command,
                resolved_args,
                client_config: client_config(&resolved),
                supervisor_id: format!("mcp-{}", manifest.slug),
                manifest,
            }
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use speccify_toolbox::RunSpec;

    fn run_spec(command: &str, args: &[&str]) -> RunSpec {
        RunSpec {
            command: command.into(),
            args: args.iter().map(|a| (*a).to_string()).collect(),
            transport: "stdio".into(),
            autostart: false,
        }
    }

    /// Ohne Repo muss `uv run speccify-mcp` auf die Engine-venv zeigen —
    /// sonst hätte ein MCP-Client in der verteilten App kein Kommando (R5.2).
    #[test]
    fn uv_run_is_mapped_onto_the_engine_venv() {
        let bin_dir =
            std::env::temp_dir().join(format!("speccify-engine-bin-{}", std::process::id()));
        std::fs::create_dir_all(&bin_dir).unwrap();
        std::fs::write(bin_dir.join("speccify-mcp"), b"#!/bin/sh\n").unwrap();

        let (command, args) =
            engine_run(&run_spec("uv", &["run", "speccify-mcp"]), &bin_dir).unwrap();
        assert_eq!(command, bin_dir.join("speccify-mcp").display().to_string());
        assert!(args.is_empty());

        // Zusätzliche Argumente hinter dem Binary-Namen bleiben erhalten.
        let (_, args) = engine_run(
            &run_spec("uv", &["run", "speccify-mcp", "--project", "/tmp"]),
            &bin_dir,
        )
        .unwrap();
        assert_eq!(args, vec!["--project".to_string(), "/tmp".to_string()]);

        // Direktes Kommando aus der venv.
        let (command, _) = engine_run(&run_spec("speccify-mcp", &[]), &bin_dir).unwrap();
        assert_eq!(command, bin_dir.join("speccify-mcp").display().to_string());

        // Nicht in der venv ⇒ kein Engine-Treffer (fällt auf Sidecar/PATH).
        assert!(engine_run(&run_spec("uv", &["run", "gibts-nicht"]), &bin_dir).is_none());
        assert!(engine_run(&run_spec("speccify-exec-mcp", &[]), &bin_dir).is_none());

        std::fs::remove_dir_all(&bin_dir).ok();
    }
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
