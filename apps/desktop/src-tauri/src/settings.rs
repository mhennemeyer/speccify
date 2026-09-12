//! App-Settings (`~/.speccify/settings.json`) + hostneutrale Agent-Einweisung
//! im Working Dir. Agent-spezifische Dateien sind kleine Adapter auf
//! `.agent/`; bestehende Dateien werden niemals überschrieben.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub working_dir: Option<String>,
    pub terminal_autostart_command: String,
    /// Default-Skill-Quelle (Work-Repo) — Projekte können sie überschreiben
    /// (Plan projektfenster.md, D21).
    #[serde(default)]
    pub skill_library: Option<String>,
    /// Erscheinungsbild aller Fenster: `system` | `light` | `dark`
    /// (Plan projektfenster.md, W7c). Die Auswertung macht das Frontend.
    #[serde(default = "default_theme")]
    pub theme: String,
    /// Globale Skill-Quellen (Plan skill-quellen-und-export.md, D2):
    /// Git-URLs oder Ordner. `skill_library` wird beim Lesen zum ersten
    /// Eintrag migriert und bleibt als Feld für ältere Stände.
    #[serde(default)]
    pub skill_sources: Vec<String>,
    /// Spec 030: ausgehender Webhook (Slack/Teams/Mattermost). Nur hier oder
    /// in `SPECCIFY_WEBHOOK_URL` — nie in getrackten Projektdateien.
    #[serde(default)]
    pub webhook_url: Option<String>,
}

fn default_theme() -> String {
    "system".into()
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            working_dir: None,
            skill_library: None,
            theme: default_theme(),
            skill_sources: Vec::new(),
            webhook_url: None,
            terminal_autostart_command: if cfg!(windows) {
                "claude.cmd".into()
            } else {
                "claude".into()
            },
        }
    }
}

/// Home-Verzeichnis plattformneutral (Windows kennt kein `HOME`).
pub(crate) fn home_dir() -> Result<PathBuf, String> {
    std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .map(PathBuf::from)
        .map_err(|_| "Weder HOME noch USERPROFILE ist gesetzt.".to_string())
}

fn settings_path() -> Result<PathBuf, String> {
    Ok(home_dir()?.join(".speccify").join("settings.json"))
}

#[tauri::command]
pub fn get_settings() -> Result<AppSettings, String> {
    let path = settings_path()?;
    match std::fs::read_to_string(&path) {
        Ok(text) => serde_json::from_str::<AppSettings>(&text)
            .map(migrate_skill_library)
            .map_err(|e| format!("{} ist kein gültiges Settings-JSON: {e}", path.display())),
        Err(_) => Ok(AppSettings::default()),
    }
}

/// `skill_library` (ein Pfad) → erster Eintrag von `skill_sources`.
pub(crate) fn migrate_skill_library(mut settings: AppSettings) -> AppSettings {
    if let Some(library) = settings.skill_library.as_deref().map(str::trim) {
        if !library.is_empty() && !settings.skill_sources.iter().any(|s| s.trim() == library) {
            settings.skill_sources.insert(0, library.to_string());
        }
    }
    settings
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
        id: "agent-source",
        relative_path: ".agent/agent.md",
        content: include_str!("../templates/agent-briefing.md"),
    },
    BriefingTemplate {
        id: "claude-md",
        relative_path: "CLAUDE.md",
        content: include_str!("../templates/CLAUDE.md"),
    },
    BriefingTemplate {
        id: "agents-md",
        relative_path: "AGENTS.md",
        content: include_str!("../templates/AGENTS.md"),
    },
    BriefingTemplate {
        id: "mcp-json",
        relative_path: ".mcp.json",
        content: include_str!("../templates/mcp.json"),
    },
    BriefingTemplate {
        id: "codex-config",
        relative_path: ".codex/config.toml",
        content: include_str!("../templates/codex-config.toml"),
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

pub(crate) fn resolve_working_dir(raw: &str) -> Result<PathBuf, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err("Kein Working Dir gesetzt (Settings).".into());
    }
    let path = if let Some(rest) = trimmed.strip_prefix("~/") {
        home_dir()?.join(rest)
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
    let content =
        crate::desktop_ui::render_endpoint(template.content, crate::desktop_ui::configured_port()?);
    std::fs::write(&target, content).map_err(|e| format!("{}: {e}", target.display()))?;
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

    #[test]
    fn codex_template_is_valid_toml() {
        let template = BRIEFINGS
            .iter()
            .find(|template| template.id == "codex-config")
            .unwrap();
        toml::from_str::<toml::Value>(template.content).unwrap();
    }
}
