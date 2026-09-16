//! Globale Agent-Konfiguration im Dashboard (Plan projektfenster.md, D23).
//!
//! Bewusst eine **Whitelist** benannter Dateien je Host — read/write gehen
//! nur über die Id, nie über freie Pfade. Claude: `~/.claude/settings.json`
//! und die globale `~/.claude/CLAUDE.md`; Codex: `~/.codex/config.toml`
//! und `~/.codex/AGENTS.md`. Die App legt fehlende Dateien erst beim
//! ersten Speichern an und überschreibt nie ungefragt.

use std::{
    io::Write,
    path::{Path, PathBuf},
    sync::Mutex,
};

use serde::{Deserialize, Serialize};
use serde_json::Value;

static WRITE_LOCK: Mutex<()> = Mutex::new(());

fn schema(id: &str) -> &'static Value {
    static CODEX: std::sync::OnceLock<Value> = std::sync::OnceLock::new();
    static CLAUDE: std::sync::OnceLock<Value> = std::sync::OnceLock::new();
    if id == "codex-config" {
        CODEX.get_or_init(|| {
            serde_json::from_str(include_str!("../../src/lib/schemas/codex.json")).unwrap()
        })
    } else {
        CLAUDE.get_or_init(|| {
            serde_json::from_str(include_str!("../../src/lib/schemas/claude.json")).unwrap()
        })
    }
}

/// Check changed known values; retain extensions and unchanged legacy settings.
/// This is a type/enum/range check, not a replacement for the installed host's validator.
fn validate_changed(
    root: &Value,
    rule: &Value,
    value: &Value,
    previous: Option<&Value>,
    path: &str,
    depth: usize,
) -> Result<(), String> {
    if Some(value) == previous || depth > 64 {
        return Ok(());
    }
    let invalid = || {
        format!("{path}: Wert passt nicht zum dokumentierten Typ, Wertebereich oder zur Auswahl.")
    };
    if let Some(reference) = rule["$ref"].as_str().and_then(|s| s.strip_prefix('#')) {
        if let Some(target) = root.pointer(reference) {
            validate_changed(root, target, value, previous, path, depth + 1)?;
        }
    }
    if let Some(parts) = rule["allOf"].as_array() {
        for part in parts {
            validate_changed(root, part, value, previous, path, depth + 1)?;
        }
    }
    for key in ["oneOf", "anyOf"] {
        if let Some(parts) = rule[key].as_array() {
            if !parts
                .iter()
                .any(|part| validate_changed(root, part, value, None, path, depth + 1).is_ok())
            {
                return Err(invalid());
            }
        }
    }
    let matches_type = |kind: &str| match kind {
        "string" => value.is_string(),
        "boolean" => value.is_boolean(),
        "object" => value.is_object(),
        "array" => value.is_array(),
        "integer" => value.is_i64() || value.is_u64(),
        "number" => value.is_number(),
        "null" => value.is_null(),
        _ => true,
    };
    if rule["type"]
        .as_str()
        .is_some_and(|kind| !matches_type(kind))
        || rule["type"].as_array().is_some_and(|kinds| {
            !kinds
                .iter()
                .any(|kind| kind.as_str().is_some_and(matches_type))
        })
        || rule["enum"]
            .as_array()
            .is_some_and(|options| !options.contains(value))
        || rule.get("const").is_some_and(|expected| expected != value)
    {
        return Err(invalid());
    }
    if let Some(number) = value.as_f64() {
        if rule["minimum"].as_f64().is_some_and(|min| number < min)
            || rule["maximum"].as_f64().is_some_and(|max| number > max)
        {
            return Err(invalid());
        }
    }
    if let Some(object) = value.as_object() {
        if let Some(required) = rule["required"].as_array() {
            if required
                .iter()
                .any(|key| key.as_str().is_some_and(|key| !object.contains_key(key)))
            {
                return Err(invalid());
            }
        }
        for (key, child) in object {
            let child_rule = rule["properties"]
                .get(key)
                .or_else(|| rule.get("additionalProperties").filter(|v| v.is_object()));
            if let Some(child_rule) = child_rule {
                validate_changed(
                    root,
                    child_rule,
                    child,
                    previous.and_then(|v| v.get(key)),
                    &format!("{path}.{key}"),
                    depth + 1,
                )?;
            }
        }
    }
    if let (Some(items), Some(item_rule)) = (
        value.as_array(),
        rule.get("items").filter(|v| v.is_object()),
    ) {
        for (index, item) in items.iter().enumerate() {
            validate_changed(
                root,
                item_rule,
                item,
                previous.and_then(|v| v.get(index)),
                &format!("{path}[{index}]"),
                depth + 1,
            )?;
        }
    }
    Ok(())
}

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
    let variable = if known.host == "codex" {
        "CODEX_HOME"
    } else {
        "CLAUDE_CONFIG_DIR"
    };
    let mut path = match std::env::var_os(variable).filter(|value| !value.is_empty()) {
        Some(value) => PathBuf::from(value),
        None => crate::settings::home_dir()?.join(known.relative[0]),
    };
    path.push(known.relative[1]);
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
    read_content(&path)
}

fn read_content(path: &Path) -> Result<String, String> {
    match std::fs::read_to_string(path) {
        Ok(content) => Ok(content),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(String::new()),
        Err(error) => Err(format!("{}: {error}", path.display())),
    }
}

#[tauri::command]
pub fn agent_config_parse(id: String, content: String) -> Result<Value, String> {
    match id.as_str() {
        "codex-config" => {
            let value = content.parse::<toml::Table>().map_err(|e| e.to_string())?;
            serde_json::to_value(value).map_err(|e| e.to_string())
        }
        "claude-settings" => {
            let value: Value = serde_json::from_str(if content.trim().is_empty() {
                "{}"
            } else {
                &content
            })
            .map_err(|e| e.to_string())?;
            if !value.is_object() {
                return Err("Die Einstellungen müssen ein JSON-Objekt sein.".into());
            }
            Ok(value)
        }
        _ => Err("Diese Datei enthält Anweisungen, keine Einstellungen.".into()),
    }
}

#[derive(Deserialize)]
pub struct ConfigChange {
    path: Vec<String>,
    value: Option<Value>,
}

fn patch_json(target: &mut Value, path: &[String], value: &Option<Value>) -> Result<(), String> {
    let object = target
        .as_object_mut()
        .ok_or("Ein übergeordneter Wert ist kein Objekt. Bitte im Quelltext bearbeiten.")?;
    if path.len() == 1 {
        if let Some(value) = value {
            object.insert(path[0].clone(), value.clone());
        } else {
            object.remove(&path[0]);
        }
    } else {
        if !object.contains_key(&path[0]) && value.is_none() {
            return Ok(());
        }
        patch_json(
            object
                .entry(path[0].clone())
                .or_insert_with(|| serde_json::json!({})),
            &path[1..],
            value,
        )?;
    }
    Ok(())
}

fn patch_toml(
    target: &mut toml_edit::Item,
    path: &[String],
    value: &Option<Value>,
) -> Result<(), String> {
    if target.is_none() {
        *target = toml_edit::Item::Table(toml_edit::Table::new());
    }
    let table = target
        .as_table_like_mut()
        .ok_or("Ein übergeordneter Wert ist keine Tabelle. Bitte im Quelltext bearbeiten.")?;
    if path.len() == 1 {
        if let Some(value) = value {
            let text = toml::to_string(&serde_json::json!({ "value": value }))
                .map_err(|e| e.to_string())?;
            let mut parsed = text
                .parse::<toml_edit::Document>()
                .map_err(|e| e.to_string())?;
            let mut item = parsed.remove("value").ok_or("Wert fehlt")?;
            if let (Some(old), Some(new)) = (
                table.get(&path[0]).and_then(|v| v.as_value()),
                item.as_value_mut(),
            ) {
                *new.decor_mut() = old.decor().clone();
            }
            if let Some(existing) = table.get_mut(&path[0]) {
                *existing = item;
            } else {
                table.insert(&path[0], item);
            }
        } else {
            table.remove(&path[0]);
        }
    } else {
        if !table.contains_key(&path[0]) && value.is_none() {
            return Ok(());
        }
        if !table.contains_key(&path[0]) {
            table.insert(&path[0], toml_edit::Item::Table(toml_edit::Table::new()));
        }
        patch_toml(table.get_mut(&path[0]).unwrap(), &path[1..], value)?;
    }
    Ok(())
}

#[tauri::command]
pub fn agent_config_patch(
    id: String,
    content: String,
    changes: Vec<ConfigChange>,
) -> Result<String, String> {
    let mut value = agent_config_parse(id.clone(), content.clone())?;
    let previous = value.clone();
    for change in &changes {
        if change.path.is_empty() || change.path.iter().any(|part| part.is_empty()) {
            return Err("Leerer Einstellungspfad.".into());
        }
        patch_json(&mut value, &change.path, &change.value)?;
    }
    validate_changed(
        schema(&id),
        schema(&id),
        &value,
        Some(&previous),
        "config",
        0,
    )?;
    if id == "codex-config" {
        let mut doc = content
            .parse::<toml_edit::Document>()
            .map_err(|e| e.to_string())?;
        for change in changes {
            patch_toml(doc.as_item_mut(), &change.path, &change.value)?;
        }
        Ok(doc.to_string())
    } else {
        serde_json::to_string_pretty(&value)
            .map(|s| s + "\n")
            .map_err(|e| e.to_string())
    }
}

fn write_checked(path: &Path, content: &str, expected: &str) -> Result<(), String> {
    // Keep a user's symlink to a shared configuration intact.
    let resolved = if path.exists() {
        std::fs::canonicalize(path).map_err(|e| e.to_string())?
    } else {
        path.to_owned()
    };
    let path = resolved.as_path();
    if read_content(path)? != expected {
        return Err("Die Datei wurde außerhalb dieses Editors geändert. Änderungen kopieren und die Datei neu laden.".into());
    }
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let mut tmp =
        tempfile::NamedTempFile::new_in(path.parent().ok_or("Übergeordneter Ordner fehlt")?)
            .map_err(|e| e.to_string())?;
    if let Ok(metadata) = std::fs::metadata(path) {
        tmp.as_file()
            .set_permissions(metadata.permissions())
            .map_err(|e| e.to_string())?;
    }
    tmp.write_all(content.as_bytes())
        .map_err(|e| e.to_string())?;
    tmp.as_file().sync_all().map_err(|e| e.to_string())?;
    if read_content(path)? != expected {
        return Err("Datei zwischenzeitlich geändert; bitte neu laden.".into());
    }
    tmp.persist(path).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn agent_config_write(
    id: String,
    content: String,
    expected_content: String,
) -> Result<(), String> {
    let _guard = WRITE_LOCK.lock().map_err(|e| e.to_string())?;
    let path = path_for(&id)?;
    if id == "codex-config" || id == "claude-settings" {
        let value = agent_config_parse(id.clone(), content.clone())?;
        let previous =
            agent_config_parse(id.clone(), expected_content.clone()).unwrap_or(Value::Null);
        validate_changed(
            schema(&id),
            schema(&id),
            &value,
            Some(&previous),
            "config",
            0,
        )?;
    }
    write_checked(&path, &content, &expected_content)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn change(path: &[&str], value: Value) -> ConfigChange {
        ConfigChange {
            path: path.iter().map(|s| s.to_string()).collect(),
            value: if value.is_null() { None } else { Some(value) },
        }
    }

    #[test]
    fn codex_roundtrip_keeps_comments_unknown_keys_and_permission_rules() {
        let original = "# local policy\napproval_policy = 'on-request' # keep this note\ncustom_key = 'keep'\n[mcp_servers.example]\ncommand = 'example'\n[tui]\nnotifications = false\n";
        let next = agent_config_patch(
            "codex-config".into(),
            original.into(),
            vec![
                change(&["approval_policy"], serde_json::json!("never")),
                change(&["approvals_reviewer"], serde_json::json!("auto_review")),
                change(&["tui", "notifications"], serde_json::json!(true)),
            ],
        )
        .unwrap();
        assert!(next.contains("# local policy"));
        assert!(next.contains("# keep this note"));
        let parsed = agent_config_parse("codex-config".into(), next).unwrap();
        assert_eq!(parsed["custom_key"], "keep");
        assert_eq!(parsed["mcp_servers"]["example"]["command"], "example");
        assert_eq!(parsed["tui"]["notifications"], true);
        assert_eq!(parsed["approval_policy"], "never");
    }

    #[test]
    fn claude_patch_preserves_rules_and_deletes_only_requested_key() {
        let original = r#"{"permissions":{"allow":["Bash(npm test)"],"defaultMode":"default"},"extra":{"keep":7}}"#;
        let next = agent_config_patch(
            "claude-settings".into(),
            original.into(),
            vec![change(
                &["permissions", "defaultMode"],
                serde_json::json!("auto"),
            )],
        )
        .unwrap();
        let parsed = agent_config_parse("claude-settings".into(), next.clone()).unwrap();
        assert_eq!(parsed["permissions"]["allow"][0], "Bash(npm test)");
        assert_eq!(parsed["extra"]["keep"], 7);
        let removed = agent_config_patch(
            "claude-settings".into(),
            next,
            vec![change(&["permissions", "defaultMode"], Value::Null)],
        )
        .unwrap();
        let parsed = agent_config_parse("claude-settings".into(), removed).unwrap();
        assert!(parsed["permissions"].get("defaultMode").is_none());
        assert!(parsed["permissions"]["allow"].is_array());
    }

    #[test]
    fn rejects_bad_syntax_types_enums_and_scalar_parent_without_saving() {
        assert!(agent_config_parse("codex-config".into(), "[broken".into()).is_err());
        assert!(agent_config_parse("claude-settings".into(), "[]".into()).is_err());
        for value in [serde_json::json!(true), serde_json::json!("unlimited")] {
            assert!(agent_config_patch(
                "codex-config".into(),
                String::new(),
                vec![change(&["sandbox_mode"], value)]
            )
            .is_err());
        }
        assert!(agent_config_patch(
            "claude-settings".into(),
            "{}".into(),
            vec![change(
                &["permissions", "defaultMode"],
                serde_json::json!("invented")
            )]
        )
        .is_err());
        assert!(agent_config_patch(
            "claude-settings".into(),
            r#"{"permissions":false}"#.into(),
            vec![change(
                &["permissions", "defaultMode"],
                serde_json::json!("auto")
            )]
        )
        .is_err());
    }

    #[test]
    fn stale_editor_cannot_overwrite_external_change() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("settings.json");
        write_checked(&path, "original", "").unwrap();
        std::fs::write(&path, "external edit").unwrap();
        assert!(write_checked(&path, "my edit", "original").is_err());
        assert_eq!(read_content(&path).unwrap(), "external edit");
        write_checked(&path, "new", "external edit").unwrap();
        assert_eq!(read_content(&path).unwrap(), "new");
    }

    #[test]
    fn explicit_null_is_checked_but_unchanged_legacy_value_is_preserved() {
        let root = schema("claude-settings");
        let value = serde_json::json!({"model": null});
        assert!(validate_changed(
            root,
            root,
            &value,
            Some(&serde_json::json!({})),
            "config",
            0
        )
        .is_err());
        assert!(validate_changed(root, root, &value, Some(&value), "config", 0).is_ok());
    }

    #[cfg(unix)]
    #[test]
    fn saving_linked_configuration_preserves_the_link() {
        let dir = tempfile::tempdir().unwrap();
        let target = dir.path().join("shared.json");
        let link = dir.path().join("settings.json");
        std::fs::write(&target, "original").unwrap();
        std::os::unix::fs::symlink(&target, &link).unwrap();
        write_checked(&link, "changed", "original").unwrap();
        assert!(std::fs::symlink_metadata(&link)
            .unwrap()
            .file_type()
            .is_symlink());
        assert_eq!(read_content(&target).unwrap(), "changed");
    }

    #[test]
    fn presets_validate_and_unchanged_legacy_values_survive() {
        let next = agent_config_patch(
            "codex-config".into(),
            "approval_policy = 'untrusted'\n".into(),
            vec![change(&["model"], serde_json::json!("example"))],
        )
        .unwrap();
        assert!(next.contains("untrusted"));
        let preset = agent_config_patch(
            "codex-config".into(),
            String::new(),
            vec![
                change(&["approval_policy"], serde_json::json!("on-request")),
                change(&["approvals_reviewer"], serde_json::json!("auto_review")),
                change(&["sandbox_mode"], serde_json::json!("workspace-write")),
                change(&["tui", "notifications"], serde_json::json!(true)),
                change(&["tui", "notification_method"], serde_json::json!("osc9")),
                change(
                    &["tui", "notification_condition"],
                    serde_json::json!("always"),
                ),
            ],
        )
        .unwrap();
        assert_eq!(
            agent_config_parse("codex-config".into(), preset).unwrap()["approvals_reviewer"],
            "auto_review"
        );
    }

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
