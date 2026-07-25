//! App-Settings (`~/.speccify/settings.json`) + Agent-Einweisungs-Dateien
//! im Working Dir (Plan toolkit-discovery-terminal.md, T1).
//!
//! Entscheidungen T0: genau EIN Working Dir global; der Terminal-Agent
//! (Claude Code) wird über `terminal_autostart_command` konfiguriert;
//! Anlegen von Einweisungs-Dateien überschreibt NIEMALS Bestehendes.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub working_dir: Option<String>,
    pub terminal_autostart_command: String,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            working_dir: None,
            terminal_autostart_command: "claude".into(),
        }
    }
}

fn settings_path() -> Result<PathBuf, String> {
    let home = std::env::var("HOME").map_err(|_| "HOME ist nicht gesetzt.".to_string())?;
    Ok(PathBuf::from(home).join(".speccify").join("settings.json"))
}

#[tauri::command]
pub fn get_settings() -> Result<AppSettings, String> {
    let path = settings_path()?;
    match std::fs::read_to_string(&path) {
        Ok(text) => serde_json::from_str(&text)
            .map_err(|e| format!("{} ist kein gültiges Settings-JSON: {e}", path.display())),
        Err(_) => Ok(AppSettings::default()),
    }
}

#[tauri::command]
pub fn save_settings(settings: AppSettings) -> Result<(), String> {
    let path = settings_path()?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let json = serde_json::to_string_pretty(&settings).map_err(|e| e.to_string())?;
    std::fs::write(&path, json + "\n").map_err(|e| format!("{}: {e}", path.display()))
}

// --- Agent-Einweisung ---------------------------------------------------------

/// Eine Einweisungs-Datei im Working Dir. Templates sind ins Binary
/// eingebettet (funktioniert auch in der gebündelten App).
struct BriefingTemplate {
    id: &'static str,
    relative_path: &'static str,
    content: &'static str,
}

const BRIEFINGS: &[BriefingTemplate] = &[
    BriefingTemplate {
        id: "claude-md",
        relative_path: "CLAUDE.md",
        content: include_str!("../templates/CLAUDE.md"),
    },
    BriefingTemplate {
        id: "mcp-json",
        relative_path: ".mcp.json",
        content: include_str!("../templates/mcp.json"),
    },
    BriefingTemplate {
        id: "claude-settings",
        relative_path: ".claude/settings.json",
        content: include_str!("../templates/claude-settings.json"),
    },
];

#[derive(Serialize)]
pub struct BriefingStatus {
    id: String,
    relative_path: String,
    exists: bool,
}

fn resolve_working_dir(raw: &str) -> Result<PathBuf, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err("Kein Working Dir gesetzt (Settings).".into());
    }
    let path = if let Some(rest) = trimmed.strip_prefix("~/") {
        let home = std::env::var("HOME").map_err(|_| "HOME ist nicht gesetzt.".to_string())?;
        PathBuf::from(home).join(rest)
    } else {
        PathBuf::from(trimmed)
    };
    if !path.is_dir() {
        return Err(format!("Working Dir existiert nicht: {}", path.display()));
    }
    Ok(path)
}

#[tauri::command]
pub fn briefing_status(working_dir: String) -> Result<Vec<BriefingStatus>, String> {
    let root = resolve_working_dir(&working_dir)?;
    Ok(BRIEFINGS
        .iter()
        .map(|template| BriefingStatus {
            id: template.id.to_string(),
            relative_path: template.relative_path.to_string(),
            exists: root.join(template.relative_path).is_file(),
        })
        .collect())
}

#[tauri::command]
pub fn create_briefing_file(working_dir: String, id: String) -> Result<String, String> {
    let root = resolve_working_dir(&working_dir)?;
    let template = BRIEFINGS
        .iter()
        .find(|template| template.id == id)
        .ok_or_else(|| format!("Unbekannte Einweisungs-Datei: {id}"))?;
    let target = root.join(template.relative_path);
    if target.exists() {
        return Err(format!(
            "{} existiert bereits — wird nicht überschrieben.",
            target.display()
        ));
    }
    if let Some(parent) = target.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    std::fs::write(&target, template.content).map_err(|e| format!("{}: {e}", target.display()))?;
    Ok(target.display().to_string())
}

#[cfg(test)]
mod tests {
    use std::path::Path;

    use super::*;

    fn temp_dir() -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-settings-test-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn briefing_files_are_created_once_and_never_overwritten() {
        let dir = temp_dir();
        let raw = dir.to_string_lossy().into_owned();

        let before = briefing_status(raw.clone()).unwrap();
        assert!(before.iter().all(|status| !status.exists));

        for template in BRIEFINGS {
            let created = create_briefing_file(raw.clone(), template.id.into()).unwrap();
            assert!(Path::new(&created).is_file());
        }
        let after = briefing_status(raw.clone()).unwrap();
        assert!(after.iter().all(|status| status.exists));

        // Zweiter Versuch: niemals überschreiben.
        let err = create_briefing_file(raw, "claude-md".into()).unwrap_err();
        assert!(err.contains("existiert bereits"));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn templates_are_valid_json_where_expected() {
        for template in BRIEFINGS {
            if template.relative_path.ends_with(".json") {
                serde_json::from_str::<serde_json::Value>(template.content)
                    .unwrap_or_else(|e| panic!("{} invalide: {e}", template.relative_path));
            }
        }
    }
}
