//! Workflow-Einweisung (Plan projektfenster.md, P5/W1, D26/D27): der
//! Board-Workflow ist **Policy als Text** — ein versionierter Block in
//! `.agent/agent.md` (Marker-Merge, fremder Inhalt bleibt wörtlich),
//! zwei mitgelieferte Ticket-Skills als Griffe, Scaffold für
//! `.agent/{board,plans}` und der Projekt-Settings-Store
//! (`.agent/settings.json`, Punkt-Notation, unbekannte Schlüssel
//! überleben — D21). Die App steuert den Agenten nie; sie richtet nur
//! die Dateien ein, die er liest.

use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::project_cmd::resolve_project_root;

/// Version des Policy-Textes — Bump ⇒ Banner zeigt „veraltet".
pub const WORKFLOW_VERSION: u32 = 1;

const POLICY: &str = include_str!("../templates/workflow-policy.md");
const BEGIN_PREFIX: &str = "<!-- speccify:workflow:begin v";
const BEGIN_SUFFIX: &str = " -->";
const END_MARKER: &str = "<!-- speccify:workflow:end -->";

/// Kopf einer frisch angelegten `.agent/agent.md` (Projekte ohne Briefing).
const AGENT_MD_HEADER: &str = "# Project agent guidance\n\nThis file is the \
agent-independent source of truth for this project. Host files like \
`CLAUDE.md` and `AGENTS.md` only point here.\n";

const TICKET_SKILLS: &[(&str, &str)] = &[
    (
        "ticket-next",
        include_str!("../templates/skill-ticket-next.md"),
    ),
    (
        "ticket-ask",
        include_str!("../templates/skill-ticket-ask.md"),
    ),
];

const CLAUDE_POINTER: &str = include_str!("../templates/CLAUDE.md");
const AGENTS_POINTER: &str = include_str!("../templates/AGENTS.md");

fn policy_block() -> String {
    format!("{BEGIN_PREFIX}{WORKFLOW_VERSION}{BEGIN_SUFFIX}\n{POLICY}{END_MARKER}\n")
}

/// Version aus einem vorhandenen Marker-Block (None = kein Block).
fn installed_version(text: &str) -> Option<u32> {
    let start = text.find(BEGIN_PREFIX)? + BEGIN_PREFIX.len();
    let rest = &text[start..];
    let end = rest.find(BEGIN_SUFFIX)?;
    rest[..end].trim().parse().ok()
}

/// Ersetzt den Marker-Block (oder hängt ihn an); alles außerhalb bleibt Byte
/// für Byte erhalten — die Datei gehört dem Projekt, nicht uns.
fn merge_policy(text: &str) -> String {
    if let (Some(start), Some(end)) = (text.find(BEGIN_PREFIX), text.find(END_MARKER)) {
        if start < end {
            let mut tail_start = end + END_MARKER.len();
            if text[tail_start..].starts_with('\n') {
                tail_start += 1;
            }
            return format!(
                "{}{}{}",
                &text[..start],
                policy_block(),
                &text[tail_start..]
            );
        }
    }
    let mut out = text.to_string();
    if !out.is_empty() && !out.ends_with('\n') {
        out.push('\n');
    }
    if !out.is_empty() {
        out.push('\n');
    }
    out.push_str(&policy_block());
    out
}

fn write_atomic(path: &Path, content: &str) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let tmp = path.with_extension("tmp-speccify");
    std::fs::write(&tmp, content).map_err(|e| format!("{}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, path).map_err(|e| format!("{}: {e}", path.display()))
}

/// Verweist eine vorhandene Host-Datei auf `.agent/agent.md`?
fn mentions_agent_source(path: &Path) -> bool {
    std::fs::read_to_string(path)
        .map(|text| text.contains(".agent/agent.md"))
        .unwrap_or(false)
}

fn skills_link_present(root: &Path, host_dir: &str) -> bool {
    let link = root.join(host_dir).join("skills");
    link.is_dir() || link.is_symlink()
}

/// `.claude/skills` bzw. `.agents/skills` → `../.agent/skills`. Konservativ:
/// existiert dort irgendetwas, bleibt es unangetastet (`speccify link`
/// repariert Sonderfälle wie Gits Symlink-Hülsen).
fn ensure_skills_link(root: &Path, host_dir: &str) -> Result<(), String> {
    let link = root.join(host_dir).join("skills");
    if link.exists() || link.is_symlink() {
        return Ok(());
    }
    std::fs::create_dir_all(root.join(".agent/skills"))
        .map_err(|e| format!(".agent/skills: {e}"))?;
    if let Some(parent) = link.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let relative = Path::new("..").join(".agent").join("skills");
    #[cfg(unix)]
    {
        std::os::unix::fs::symlink(&relative, &link).map_err(|e| format!("{}: {e}", link.display()))
    }
    #[cfg(windows)]
    {
        // Symlink braucht Developer Mode — Junction-Fallback wie in
        // `speccify link` (D17), hier über mklink statt _winapi.
        if std::os::windows::fs::symlink_dir(&relative, &link).is_ok() {
            return Ok(());
        }
        let target = root.join(".agent").join("skills");
        let output = std::process::Command::new("cmd")
            .args([
                "/c",
                "mklink",
                "/J",
                &link.display().to_string(),
                &target.display().to_string(),
            ])
            .output()
            .map_err(|e| format!("mklink: {e}"))?;
        if output.status.success() {
            Ok(())
        } else {
            Err(format!(
                "mklink /J {}: {}",
                link.display(),
                String::from_utf8_lossy(&output.stderr)
            ))
        }
    }
}

#[derive(Serialize)]
pub struct WorkflowStatus {
    /// "missing" | "outdated" | "current"
    state: String,
    installed_version: Option<u32>,
    current_version: u32,
    /// Was `install` konkret anfassen würde (fürs Banner-Detail).
    pending: Vec<String>,
}

fn collect_pending(root: &Path) -> (Option<u32>, Vec<String>) {
    let mut pending = Vec::new();
    let agent_md = root.join(".agent/agent.md");
    let installed = std::fs::read_to_string(&agent_md)
        .ok()
        .as_deref()
        .and_then(installed_version);
    match installed {
        None => pending.push("Workflow-Regeln in .agent/agent.md".into()),
        Some(version) if version < WORKFLOW_VERSION => {
            pending.push(format!("Workflow-Regeln v{version} → v{WORKFLOW_VERSION}"))
        }
        Some(_) => {}
    }
    for dir in [".agent/board", ".agent/plans"] {
        if !root.join(dir).is_dir() {
            pending.push(format!("{dir}/ anlegen"));
        }
    }
    for (name, _) in TICKET_SKILLS {
        if !root
            .join(".agent/skills")
            .join(name)
            .join("SKILL.md")
            .is_file()
        {
            pending.push(format!("Skill {name}"));
        }
    }
    for (file, label) in [
        ("CLAUDE.md", "CLAUDE.md-Verweis"),
        ("AGENTS.md", "AGENTS.md-Verweis"),
    ] {
        let path = root.join(file);
        if !path.is_file() {
            pending.push(label.into());
        } else if !mentions_agent_source(&path) {
            // Vorhandene Host-Datei ohne Verweis: nur melden, nie anfassen.
            pending.push(format!(
                "{file} verweist nicht auf .agent/agent.md (manuell prüfen)"
            ));
        }
    }
    for (host, label) in [
        (".claude", ".claude/skills-Link"),
        (".agents", ".agents/skills-Link"),
    ] {
        if !skills_link_present(root, host) {
            pending.push(label.into());
        }
    }
    (installed, pending)
}

#[tauri::command]
pub fn project_workflow_status(project: String) -> Result<WorkflowStatus, String> {
    let root = resolve_project_root(&project)?;
    let (installed, pending) = collect_pending(&root);
    let state = if installed.is_none() {
        "missing"
    } else if pending.is_empty() {
        "current"
    } else {
        "outdated"
    };
    Ok(WorkflowStatus {
        state: state.into(),
        installed_version: installed,
        current_version: WORKFLOW_VERSION,
        pending,
    })
}

/// Richtet den Workflow ein (bewusst per Knopf, nie automatisch — es wird in
/// Projektdateien geschrieben). Idempotent; Bestehendes außerhalb der Marker
/// und angepasste Skills bleiben unangetastet.
#[tauri::command]
pub fn project_workflow_install(project: String) -> Result<WorkflowStatus, String> {
    let root = resolve_project_root(&project)?;

    for dir in [".agent/board", ".agent/plans", ".agent/skills"] {
        std::fs::create_dir_all(root.join(dir)).map_err(|e| format!("{dir}: {e}"))?;
    }

    let agent_md = root.join(".agent/agent.md");
    let existing = std::fs::read_to_string(&agent_md).unwrap_or_else(|_| AGENT_MD_HEADER.into());
    write_atomic(&agent_md, &merge_policy(&existing))?;

    for (name, content) in TICKET_SKILLS {
        let skill = root.join(".agent/skills").join(name).join("SKILL.md");
        if !skill.is_file() {
            write_atomic(&skill, content)?;
        }
    }

    for (file, content) in [("CLAUDE.md", CLAUDE_POINTER), ("AGENTS.md", AGENTS_POINTER)] {
        let path = root.join(file);
        if !path.is_file() {
            write_atomic(&path, content)?;
        }
    }

    ensure_skills_link(&root, ".claude")?;
    ensure_skills_link(&root, ".agents")?;

    project_workflow_status(root.display().to_string())
}

// --- Projekt-Settings (`.agent/settings.json`, D21/D27) -----------------------
// Punkt-Notation wie in iKanbanAis ProjectSettingsFile: unbekannte Schlüssel
// überleben jede Schreiboperation, `null` löscht, leere Objekte werden
// hochgeräumt, ein leeres Wurzelobjekt löscht die Datei. Keine Secrets —
// die Datei liegt im Git.

fn settings_path(root: &Path) -> PathBuf {
    root.join(".agent/settings.json")
}

#[tauri::command]
pub fn project_settings_get(project: String) -> Result<serde_json::Value, String> {
    let root = resolve_project_root(&project)?;
    Ok(std::fs::read_to_string(settings_path(&root))
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_else(|| serde_json::json!({})))
}

fn prune_empty(value: &mut serde_json::Value) {
    if let serde_json::Value::Object(map) = value {
        let keys: Vec<String> = map.keys().cloned().collect();
        for key in keys {
            if let Some(child) = map.get_mut(&key) {
                prune_empty(child);
                if child.as_object().is_some_and(|object| object.is_empty()) {
                    map.remove(&key);
                }
            }
        }
    }
}

#[tauri::command]
pub fn project_settings_set(
    project: String,
    key: String,
    value: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let segments: Vec<&str> = key.split('.').filter(|part| !part.is_empty()).collect();
    if segments.is_empty() {
        return Err("Leerer Settings-Schlüssel.".into());
    }
    let root = resolve_project_root(&project)?;
    let mut settings = project_settings_get(root.display().to_string())?;
    if !settings.is_object() {
        settings = serde_json::json!({});
    }

    {
        let mut cursor = &mut settings;
        for segment in &segments[..segments.len() - 1] {
            let map = cursor.as_object_mut().expect("Wurzel ist Objekt");
            let entry = map
                .entry(segment.to_string())
                .or_insert_with(|| serde_json::json!({}));
            if !entry.is_object() {
                *entry = serde_json::json!({});
            }
            cursor = entry;
        }
        let map = cursor.as_object_mut().expect("Pfad ist Objekt");
        let last = segments[segments.len() - 1].to_string();
        if value.is_null() {
            map.remove(&last);
        } else {
            map.insert(last, value);
        }
    }

    prune_empty(&mut settings);
    let path = settings_path(&root);
    if settings.as_object().is_some_and(|map| map.is_empty()) {
        let _ = std::fs::remove_file(&path);
    } else {
        let text = serde_json::to_string_pretty(&settings).map_err(|e| e.to_string())?;
        write_atomic(&path, &(text + "\n"))?;
    }
    Ok(settings)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(test: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-workflow-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn merge_appends_replaces_and_keeps_foreign_text() {
        let fresh = merge_policy("");
        assert!(fresh.starts_with(BEGIN_PREFIX));
        assert_eq!(installed_version(&fresh), Some(WORKFLOW_VERSION));

        let own = "# Mein Projekt\n\nEigene Regeln.\n";
        let merged = merge_policy(own);
        assert!(merged.starts_with(own));
        assert!(merged.contains(END_MARKER));

        // Alten Block ersetzen, Text davor und danach bleibt wörtlich.
        let old = format!(
            "Davor.\n\n{BEGIN_PREFIX}0{BEGIN_SUFFIX}\nalter inhalt\n{END_MARKER}\nDanach.\n"
        );
        let updated = merge_policy(&old);
        assert!(updated.starts_with("Davor.\n\n"));
        assert!(updated.ends_with("Danach.\n"));
        assert!(!updated.contains("alter inhalt"));
        assert_eq!(installed_version(&updated), Some(WORKFLOW_VERSION));
        // Idempotent: nochmal mergen ändert nichts.
        assert_eq!(merge_policy(&updated), updated);
    }

    #[test]
    fn install_scaffolds_and_status_reaches_current() {
        let dir = fixture("install");
        let project = dir.to_string_lossy().into_owned();

        let before = project_workflow_status(project.clone()).unwrap();
        assert_eq!(before.state, "missing");
        assert!(!before.pending.is_empty());

        let after = project_workflow_install(project.clone()).unwrap();
        assert_eq!(after.state, "current", "pending: {:?}", after.pending);
        assert!(dir.join(".agent/board").is_dir());
        assert!(dir.join(".agent/plans").is_dir());
        assert!(dir.join(".agent/skills/ticket-next/SKILL.md").is_file());
        assert!(dir.join(".agent/skills/ticket-ask/SKILL.md").is_file());
        assert!(dir.join("CLAUDE.md").is_file());
        assert!(dir.join("AGENTS.md").is_file());
        let agent_md = std::fs::read_to_string(dir.join(".agent/agent.md")).unwrap();
        assert!(agent_md.contains("## Board workflow"));

        // Zweiter Lauf ist ein No-op auf Byte-Ebene.
        let first = std::fs::read_to_string(dir.join(".agent/agent.md")).unwrap();
        project_workflow_install(project.clone()).unwrap();
        assert_eq!(
            std::fs::read_to_string(dir.join(".agent/agent.md")).unwrap(),
            first
        );

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn install_respects_existing_files() {
        let dir = fixture("respect");
        let project = dir.to_string_lossy().into_owned();
        std::fs::create_dir_all(dir.join(".agent/skills/ticket-next")).unwrap();
        std::fs::write(
            dir.join(".agent/skills/ticket-next/SKILL.md"),
            "---\nname: ticket-next\ndescription: Angepasst.\n---\nEigene Variante.\n",
        )
        .unwrap();
        std::fs::write(dir.join("CLAUDE.md"), "# Eigenes CLAUDE.md ohne Verweis\n").unwrap();
        std::fs::write(
            dir.join(".agent/agent.md"),
            "# Bestand\n\nDarf nicht verschwinden.\n",
        )
        .unwrap();

        let status = project_workflow_install(project.clone()).unwrap();

        let skill =
            std::fs::read_to_string(dir.join(".agent/skills/ticket-next/SKILL.md")).unwrap();
        assert!(skill.contains("Eigene Variante"));
        let claude = std::fs::read_to_string(dir.join("CLAUDE.md")).unwrap();
        assert_eq!(claude, "# Eigenes CLAUDE.md ohne Verweis\n");
        let agent_md = std::fs::read_to_string(dir.join(".agent/agent.md")).unwrap();
        assert!(agent_md.starts_with("# Bestand\n"));
        assert!(agent_md.contains("## Board workflow"));
        // Host-Datei ohne Verweis wird gemeldet, nicht angefasst.
        assert_eq!(status.state, "outdated");
        assert!(status
            .pending
            .iter()
            .any(|entry| entry.contains("CLAUDE.md verweist nicht")));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn settings_survive_unknown_keys_and_prune_empties() {
        let dir = fixture("settings");
        let project = dir.to_string_lossy().into_owned();
        std::fs::create_dir_all(dir.join(".agent")).unwrap();
        std::fs::write(
            dir.join(".agent/settings.json"),
            r#"{"exec":{"port":8765},"agentNotes":{"foo":"bar"}}"#,
        )
        .unwrap();

        project_settings_set(
            project.clone(),
            "speccify.library".into(),
            serde_json::json!("~/Desktop/Work/speccify"),
        )
        .unwrap();
        let settings = project_settings_get(project.clone()).unwrap();
        assert_eq!(settings["exec"]["port"], 8765);
        assert_eq!(settings["agentNotes"]["foo"], "bar");
        assert_eq!(settings["speccify"]["library"], "~/Desktop/Work/speccify");

        // null löscht; leere Zweige verschwinden.
        project_settings_set(
            project.clone(),
            "speccify.library".into(),
            serde_json::Value::Null,
        )
        .unwrap();
        let pruned = project_settings_get(project.clone()).unwrap();
        assert!(pruned.get("speccify").is_none());
        assert_eq!(pruned["exec"]["port"], 8765);

        // Alles weg ⇒ Datei weg.
        project_settings_set(project.clone(), "exec.port".into(), serde_json::Value::Null).unwrap();
        project_settings_set(
            project.clone(),
            "agentNotes.foo".into(),
            serde_json::Value::Null,
        )
        .unwrap();
        assert!(!dir.join(".agent/settings.json").exists());

        let _ = std::fs::remove_dir_all(&dir);
    }
}
