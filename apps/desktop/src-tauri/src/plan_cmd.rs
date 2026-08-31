//! Plan-Lifecycle (Plan projektfenster.md, P5/W6): `draft | active | onHold |
//! done | research` mit der Invariante **höchstens ein aktiver Plan** —
//! `activate` setzt den bisher aktiven automatisch auf `onHold`. Dazu die
//! Eskalation: `escalation:` im Frontmatter (einzeilig oder Block mit
//! `reason`/`raisedBy`/`at`) zeigt ein rotes Banner; „Auflösen" entfernt
//! nur diese Zeilen. Es wird ausschließlich Frontmatter angefasst — der
//! Body bleibt Byte für Byte.

use std::path::Path;

use crate::board_cmd::update_ticket_text;
use crate::project_cmd::{resolve_project_root, safe_project_path};

fn plans_dir(root: &Path) -> std::path::PathBuf {
    root.join(".agent/plans")
}

fn is_plan_file(root: &Path, path: &Path) -> bool {
    path.starts_with(plans_dir(root)) && path.extension().is_some_and(|ext| ext == "md")
}

fn lifecycle_of(text: &str) -> Option<String> {
    text.lines()
        .find_map(|line| line.strip_prefix("lifecycle:"))
        .map(|value| value.trim().to_string())
}

/// Aktiviert einen Plan; jeder andere **aktive** Plan im Top-Level (nicht
/// `archive/`) geht auf `onHold`. Rückgabe: die Dateien, die dabei auf
/// onHold gewechselt sind (fürs UI-Feedback).
#[tauri::command]
pub fn project_plan_activate(project: String, file: String) -> Result<Vec<String>, String> {
    let root = resolve_project_root(&project)?;
    let target = safe_project_path(&root, &file)?;
    if !is_plan_file(&root, &target) {
        return Err(format!("Kein Plan: {file}"));
    }

    let mut parked = Vec::new();
    if let Ok(entries) = std::fs::read_dir(plans_dir(&root)) {
        for entry in entries.filter_map(Result::ok) {
            let path = entry.path();
            if path == target || path.extension().is_none_or(|ext| ext != "md") {
                continue;
            }
            let Ok(text) = std::fs::read_to_string(&path) else {
                continue;
            };
            if lifecycle_of(&text).as_deref() == Some("active") {
                let updated =
                    update_ticket_text(&text, &[("lifecycle", Some("onHold".into()))], None)?;
                std::fs::write(&path, updated).map_err(|e| format!("{}: {e}", path.display()))?;
                parked.push(
                    path.strip_prefix(&root)
                        .unwrap_or(&path)
                        .to_string_lossy()
                        .replace('\\', "/"), // Windows-Trenner normalisieren
                );
            }
        }
    }

    let text =
        std::fs::read_to_string(&target).map_err(|e| format!("{}: {e}", target.display()))?;
    let updated = update_ticket_text(&text, &[("lifecycle", Some("active".into()))], None)?;
    std::fs::write(&target, updated).map_err(|e| format!("{}: {e}", target.display()))?;
    Ok(parked)
}

/// Entfernt den `escalation:`-Eintrag — die einzelne Zeile oder den ganzen
/// Block (Folgezeilen mit Einzug). Alles andere bleibt wörtlich.
pub(crate) fn clear_escalation(text: &str) -> String {
    if !text.starts_with("---") {
        return text.to_string();
    }
    let mut out = String::with_capacity(text.len());
    // 0 = erste ---, 1 = im Frontmatter, 2 = Body (unangetastet).
    let mut state = 0u8;
    let mut skipping_block = false;
    for line in text.split_inclusive('\n') {
        match state {
            0 => {
                out.push_str(line);
                state = 1;
            }
            1 => {
                if skipping_block {
                    if line.starts_with(' ') || line.starts_with('\t') {
                        continue; // eingerückte Blockzeile überspringen
                    }
                    skipping_block = false;
                }
                if line.trim_end() == "---" {
                    state = 2;
                    out.push_str(line);
                } else if line.trim_start().starts_with("escalation:") {
                    skipping_block = true;
                } else {
                    out.push_str(line);
                }
            }
            _ => out.push_str(line),
        }
    }
    out
}

#[tauri::command]
pub fn project_plan_resolve_escalation(project: String, file: String) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    if !is_plan_file(&root, &path) {
        return Err(format!("Kein Plan: {file}"));
    }
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    std::fs::write(&path, clear_escalation(&text)).map_err(|e| format!("{}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(test: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!("speccify-plan-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join(".agent/plans/archive")).unwrap();
        dir
    }

    #[test]
    fn activate_parks_the_previous_active_plan() {
        let dir = fixture("activate");
        let project = dir.to_string_lossy().into_owned();
        std::fs::write(
            dir.join(".agent/plans/alt.md"),
            "---\nlifecycle: active\nstatus: läuft\n---\n# Alt\n",
        )
        .unwrap();
        std::fs::write(
            dir.join(".agent/plans/neu.md"),
            "---\nlifecycle: draft\nstatus: bereit\nsessionId: neu\n---\n# Neu\n",
        )
        .unwrap();
        // Archivierte Pläne bleiben unangetastet, auch wenn aktiv markiert.
        std::fs::write(
            dir.join(".agent/plans/archive/uralt.md"),
            "---\nlifecycle: active\n---\n# Uralt\n",
        )
        .unwrap();

        let parked = project_plan_activate(project, ".agent/plans/neu.md".into()).unwrap();
        assert_eq!(parked, vec![".agent/plans/alt.md".to_string()]);

        let alt = std::fs::read_to_string(dir.join(".agent/plans/alt.md")).unwrap();
        assert!(alt.contains("lifecycle: onHold"));
        assert!(alt.contains("status: läuft")); // Rest unangetastet
        let neu = std::fs::read_to_string(dir.join(".agent/plans/neu.md")).unwrap();
        assert!(neu.contains("lifecycle: active"));
        assert!(neu.contains("sessionId: neu"));
        let uralt = std::fs::read_to_string(dir.join(".agent/plans/archive/uralt.md")).unwrap();
        assert!(uralt.contains("lifecycle: active"));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn escalation_line_and_block_are_cleared() {
        let line = "---\nlifecycle: active\nescalation: Bitte draufsehen\nstatus: x\n---\nBody.\n";
        let cleared = clear_escalation(line);
        assert_eq!(cleared, "---\nlifecycle: active\nstatus: x\n---\nBody.\n");

        let block = "---\nlifecycle: active\nescalation:\n  reason: Klemmt\n  raisedBy: agent\nstatus: x\n---\nBody mit escalation: im Text.\n";
        let cleared = clear_escalation(block);
        assert_eq!(
            cleared,
            "---\nlifecycle: active\nstatus: x\n---\nBody mit escalation: im Text.\n"
        );
    }
}
