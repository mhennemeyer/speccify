//! Local, app-wide terminal preferences; separate from host configuration.
use serde::{Deserialize, Serialize};
use std::{io::Write, sync::Mutex};
use tauri::{AppHandle, Emitter};

static LOCK: Mutex<()> = Mutex::new(());

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(default)]
pub struct Preferences {
    pub font_size: u16,
    pub popups: bool,
    pub system_notifications: bool,
    /// Spec 070: Terminals laufen im PTY-Host und überleben App-Neustarts.
    pub persist_sessions: bool,
}

impl Default for Preferences {
    fn default() -> Self {
        Self {
            font_size: 14,
            popups: true,
            system_notifications: true,
            persist_sessions: false,
        }
    }
}

fn path() -> Result<std::path::PathBuf, String> {
    Ok(crate::settings::home_dir()?.join(".speccify/terminal-preferences.json"))
}

fn read(path: &std::path::Path) -> Result<Preferences, String> {
    match std::fs::read(path) {
        Ok(bytes) => {
            let prefs: Preferences = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
            if !(8..=32).contains(&prefs.font_size) {
                return Err(
                    "Gespeicherte Terminal-Schriftgröße muss zwischen 8 und 32 px liegen.".into(),
                );
            }
            Ok(prefs)
        }
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(Preferences::default()),
        Err(e) => Err(e.to_string()),
    }
}

fn patched(
    mut prefs: Preferences,
    font_size: Option<u16>,
    popups: Option<bool>,
    system_notifications: Option<bool>,
    persist_sessions: Option<bool>,
) -> Result<Preferences, String> {
    if let Some(value) = persist_sessions {
        prefs.persist_sessions = value;
    }
    if let Some(size) = font_size {
        if !(8..=32).contains(&size) {
            return Err("Terminal-Schriftgröße muss zwischen 8 und 32 px liegen.".into());
        }
        prefs.font_size = size;
    }
    if let Some(value) = popups {
        prefs.popups = value;
    }
    if let Some(value) = system_notifications {
        prefs.system_notifications = value;
    }
    Ok(prefs)
}

#[tauri::command]
pub fn terminal_preferences() -> Result<Preferences, String> {
    let _guard = LOCK.lock().map_err(|e| e.to_string())?;
    read(&path()?)
}

#[tauri::command]
pub fn terminal_preferences_update(
    app: AppHandle,
    font_size: Option<u16>,
    popups: Option<bool>,
    system_notifications: Option<bool>,
    persist_sessions: Option<bool>,
) -> Result<Preferences, String> {
    let _guard = LOCK.lock().map_err(|e| e.to_string())?;
    let path = path()?;
    let prefs = patched(
        read(&path)?,
        font_size,
        popups,
        system_notifications,
        persist_sessions,
    )?;
    let parent = path.parent().unwrap();
    std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let mut file = tempfile::NamedTempFile::new_in(parent).map_err(|e| e.to_string())?;
    file.write_all(
        serde_json::to_string_pretty(&prefs)
            .map_err(|e| e.to_string())?
            .as_bytes(),
    )
    .map_err(|e| e.to_string())?;
    file.persist(path).map_err(|e| e.to_string())?;
    app.emit("terminal-preferences", &prefs)
        .map_err(|e| e.to_string())?;
    Ok(prefs)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn patch_preserves_other_preferences_and_rejects_invalid_sizes() {
        let existing = Preferences {
            font_size: 20,
            popups: false,
            system_notifications: false,
            persist_sessions: true,
        };
        let changed = patched(existing.clone(), Some(24), None, None, None).unwrap();
        assert_eq!(
            changed,
            Preferences {
                font_size: 24,
                ..existing.clone()
            }
        );
        for size in [0, 7, 33, u16::MAX] {
            assert!(patched(existing.clone(), Some(size), None, None, None).is_err());
        }
        assert_eq!(
            serde_json::from_str::<Preferences>("{}").unwrap(),
            Preferences::default()
        );
    }
}
