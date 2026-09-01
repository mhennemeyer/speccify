//! Globale Agent-Konfiguration im Dashboard (Plan projektfenster.md, D23).
//!
//! Bewusst eine **Whitelist** benannter Dateien je Host — read/write gehen
//! nur über die Id, nie über freie Pfade. Claude: `~/.claude/settings.json`
//! und die globale `~/.claude/CLAUDE.md`; Codex: `~/.codex/config.toml`
//! und `~/.codex/AGENTS.md`. Die App legt fehlende Dateien erst beim
//! ersten Speichern an und überschreibt nie ungefragt.

use std::path::PathBuf;

use serde::Serialize;

struct KnownFile {
    id: &'static str,
    host: &'static str,
    /// Relativ zum Home-Verzeichnis.
    relative: &'static [&'static str],
    hint: &'static str,
}

const KNOWN_FILES: &[KnownFile] = &[
    KnownFile {
        id: "claude-settings",
        host: "claude",
        relative: &[".claude", "settings.json"],
        hint: "Globale Claude-Code-Einstellungen (Permissions, Modell, Hooks).",
    },
    KnownFile {
        id: "claude-md",
        host: "claude",
        relative: &[".claude", "CLAUDE.md"],
        hint: "Globale Anweisungen — gelten in jedem Projekt.",
    },
    KnownFile {
        id: "codex-config",
        host: "codex",
        relative: &[".codex", "config.toml"],
        hint: "Globale Codex-Konfiguration (Modell, Approval-Policy, MCPs).",
    },
    KnownFile {
        id: "codex-agents-md",
        host: "codex",
        relative: &[".codex", "AGENTS.md"],
        hint: "Globale Anweisungen — gelten in jedem Projekt.",
    },
];

fn path_for(id: &str) -> Result<PathBuf, String> {
    let known = KNOWN_FILES
        .iter()
        .find(|file| file.id == id)
        .ok_or_else(|| format!("Unbekannte Agent-Config: {id}"))?;
    let mut path = crate::settings::home_dir()?;
    for part in known.relative {
        path.push(part);
    }
    Ok(path)
}

#[derive(Serialize)]
pub struct AgentConfigFile {
    id: String,
    host: String,
    path: String,
    hint: String,
    exists: bool,
}

#[tauri::command]
pub fn agent_config_list() -> Result<Vec<AgentConfigFile>, String> {
    KNOWN_FILES
        .iter()
        .map(|file| {
            let path = path_for(file.id)?;
            Ok(AgentConfigFile {
                id: file.id.into(),
                host: file.host.into(),
                path: path.display().to_string(),
                hint: file.hint.into(),
                exists: path.is_file(),
            })
        })
        .collect()
}

#[tauri::command]
pub fn agent_config_read(id: String) -> Result<String, String> {
    let path = path_for(&id)?;
    if !path.is_file() {
        return Ok(String::new());
    }
    std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))
}

#[tauri::command]
pub fn agent_config_write(id: String, content: String) -> Result<(), String> {
    let path = path_for(&id)?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let tmp = path.with_extension("tmp-speccify");
    std::fs::write(&tmp, content).map_err(|e| format!("{}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, &path).map_err(|e| format!("{}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ids_resolve_and_unknown_ids_are_rejected() {
        // HOME zeigt in Tests auf das echte Home — nur Pfad-Logik prüfen.
        let path = path_for("claude-settings").unwrap();
        assert!(
            path.ends_with(".claude/settings.json") || path.ends_with(".claude\\settings.json")
        );
        let error = path_for("frei/../gewaehlt").unwrap_err();
        assert!(error.contains("Unbekannte Agent-Config"));
        assert_eq!(agent_config_list().unwrap().len(), 4);
    }
}
