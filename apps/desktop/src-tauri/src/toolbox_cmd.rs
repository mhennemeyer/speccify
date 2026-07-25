//! Toolbox-Commands der App (Plan toolkit-discovery-terminal.md, T2):
//! Library-Tab liest die Manifeste nativ (statt `dotagent registry list`),
//! Scaffold legt neue Manifeste im Working Dir an.

use std::path::PathBuf;

use serde::Serialize;
use speccify_toolbox::{load_all, scaffold, Manifest};

use crate::settings;

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
