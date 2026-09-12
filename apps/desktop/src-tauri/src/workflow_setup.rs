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
mod diagnostics;
use diagnostics::{collect_issues, file_state, policy_state, protected_path};

/// Version des Policy-Textes — Bump ⇒ Banner zeigt „veraltet".
/// v1 = Board/Ticket-Workflow (2026-08-31), v2 = Spec-Workflow
/// (Plan spec-workflow.md, 2026-09-09): der Block in agent.md wird beim
/// Einrichten ersetzt, angepasste Texte außerhalb der Marker bleiben.
pub const WORKFLOW_VERSION: u32 = 7; // v7: owner and branch per spec (Spec 029)

const POLICY: &str = include_str!("../templates/workflow-policy.md");
const BEGIN_PREFIX: &str = "<!-- speccify:workflow:begin v";
const BEGIN_SUFFIX: &str = " -->";
const END_MARKER: &str = "<!-- speccify:workflow:end -->";

/// Kopf einer frisch angelegten `.agent/agent.md` (Projekte ohne Briefing).
const AGENT_MD_HEADER: &str = "# Project agent guidance\n\nThis file is the \
agent-independent source of truth for this project. Host files like \
`CLAUDE.md` and `AGENTS.md` only point here.\n";

const TICKET_SKILLS: &[(&str, &str)] = &[
    ("spec-next", include_str!("../templates/skill-spec-next.md")),
    ("spec-ask", include_str!("../templates/skill-spec-ask.md")),
];

const PREVIOUS_POLICY: &[(u32, &str)] = &[
    (
        6,
        include_str!("../templates/history/workflow-policy-v6.md"),
    ),
    (
        5,
        include_str!("../templates/history/workflow-policy-v5.md"),
    ),
    (
        4,
        include_str!("../templates/history/workflow-policy-v4.md"),
    ),
    (
        1,
        include_str!("../templates/history/workflow-policy-v1.md"),
    ),
    (
        2,
        include_str!("../templates/history/workflow-policy-v2.md"),
    ),
    (
        3,
        include_str!("../templates/history/workflow-policy-v3.md"),
    ),
];
const PREVIOUS_SPEC_SKILLS: &[(&str, &str)] = &[
    (
        "spec-next",
        include_str!("../templates/history/skill-spec-next-v1.md"),
    ),
    (
        "spec-ask",
        include_str!("../templates/history/skill-spec-ask-v1.md"),
    ),
];

/// Skills des v1-Workflows: werden beim Einrichten entfernt, wenn sie noch
/// unverändert die alte Vorlage sind (angepasste bleiben).
const LEGACY_SKILLS: &[(&str, &str)] = &[
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

fn read_optional(path: &Path) -> Result<Option<String>, String> {
    match std::fs::read_to_string(path) {
        Ok(text) => Ok(Some(text)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(format!("{}: {e}", path.display())),
    }
}

fn write_unchanged(path: &Path, before: Option<&str>, content: &str) -> Result<(), String> {
    if read_optional(path)?.as_deref() != before {
        return Err(format!(
            "WORKFLOW_CHANGED: {} wurde zwischenzeitlich geändert; bitte erneut prüfen.",
            path.display()
        ));
    }
    write_atomic(path, content)
}

/// Verweist eine vorhandene Host-Datei auf `.agent/agent.md`?
fn mentions_agent_source(path: &Path) -> bool {
    std::fs::read_to_string(path)
        .map(|text| text.contains(".agent/agent.md"))
        .unwrap_or(false)
}

fn skills_link_present(root: &Path, host_dir: &str) -> bool {
    let link = root.join(host_dir).join("skills");
    link.is_dir()
        && link
            .canonicalize()
            .ok()
            .zip(root.join(".agent/skills").canonicalize().ok())
            .is_some_and(|(actual, expected)| actual == expected)
}

/// Gits Symlink-Hülse: mit `core.symlinks=false` (Windows-Standard) checkt
/// Git einen committeten Symlink als kleine Textdatei aus, deren Inhalt der
/// Zielpfad ist. Die App darf sie ersetzen — sie *meint* den Link ja schon.
/// Ohne diese Erkennung war der Einrichten-Knopf auf Windows wirkungslos:
/// der Status meldete den Link als fehlend, Install sah `exists()` und
/// ließ die Datei stehen (Kollegen-Fund, 2026-09-03).
fn is_symlink_stub(link: &Path) -> bool {
    if !link.is_file() {
        return false;
    }
    match std::fs::read_to_string(link) {
        Ok(content) => {
            let content = content.trim();
            content.replace('\\', "/") == "../.agent/skills"
        }
        Err(_) => false,
    }
}

/// `.claude/skills` bzw. `.agents/skills` → `../.agent/skills`. Konservativ:
/// existiert dort irgendetwas (außer einer Symlink-Hülse), bleibt es
/// unangetastet.
fn ensure_skills_link(root: &Path, host_dir: &str) -> Result<(), String> {
    let link = root.join(host_dir).join("skills");
    if protected_path(root, &root.join(host_dir))
        || protected_path(root, &root.join(".agent/skills"))
    {
        return Ok(());
    }
    if !link.is_symlink() && is_symlink_stub(&link) {
        std::fs::remove_file(&link).map_err(|e| format!("{}: {e}", link.display()))?;
    } else if link.exists() || link.is_symlink() {
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
    issues: Vec<WorkflowIssue>,
}

#[derive(Serialize)]
pub struct WorkflowIssue {
    path: String,
    kind: String,
    action: String,
    message: String,
}

#[tauri::command]
pub async fn project_workflow_status(project: String) -> Result<WorkflowStatus, String> {
    tauri::async_runtime::spawn_blocking(move || workflow_status(project))
        .await
        .map_err(|e| e.to_string())?
}

fn workflow_status(project: String) -> Result<WorkflowStatus, String> {
    let root = resolve_project_root(&project)?;
    let (installed, issues) = collect_issues(&root);
    let pending: Vec<_> = issues.iter().map(|issue| issue.message.clone()).collect();
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
        issues,
    })
}

/// Richtet den Workflow ein (bewusst per Knopf, nie automatisch — es wird in
/// Projektdateien geschrieben). Idempotent; Bestehendes außerhalb der Marker
/// und angepasste Skills bleiben unangetastet.
#[tauri::command]
pub fn project_workflow_install(project: String) -> Result<WorkflowStatus, String> {
    static SETUP_WRITES: std::sync::Mutex<()> = std::sync::Mutex::new(());
    let _guard = SETUP_WRITES.lock().map_err(|e| e.to_string())?;
    let root = resolve_project_root(&project)?;

    for dir in [".agent/specs", ".agent/playbooks", ".agent/skills"] {
        if !protected_path(&root, &root.join(dir)) && !root.join(dir).exists() {
            std::fs::create_dir_all(root.join(dir)).map_err(|e| format!("{dir}: {e}"))?;
        }
    }

    let agent_md = root.join(".agent/agent.md");
    if matches!(policy_state(&root).1, "missing" | "outdated") {
        let before = read_optional(&agent_md)?;
        let existing = before.as_deref().unwrap_or(AGENT_MD_HEADER);
        if matches!(
            diagnostics::policy_text_state(existing).1,
            "missing" | "outdated"
        ) {
            write_unchanged(&agent_md, before.as_deref(), &merge_policy(existing))?;
        }
    }

    for (name, content) in TICKET_SKILLS {
        let skill = root.join(".agent/skills").join(name).join("SKILL.md");
        let previous: Vec<_> = PREVIOUS_SPEC_SKILLS
            .iter()
            .filter(|(id, _)| id == name)
            .map(|(_, text)| *text)
            .collect();
        if matches!(
            file_state(&root, &skill, content, &previous),
            "missing" | "outdated"
        ) {
            let before = read_optional(&skill)?;
            if before
                .as_deref()
                .is_none_or(|text| diagnostics::text_state(text, content, &previous) == "outdated")
            {
                write_unchanged(&skill, before.as_deref(), content)?;
            }
        }
    }
    // v1-Skills nur entfernen, wenn sie noch die unveränderte Vorlage sind.
    for (name, template) in LEGACY_SKILLS {
        let dir = root.join(".agent/skills").join(name);
        let skill = dir.join("SKILL.md");
        if !protected_path(&root, &skill)
            && std::fs::read_to_string(&skill).ok().as_deref() == Some(*template)
        {
            let _ = std::fs::remove_file(&skill);
            let _ = std::fs::remove_dir(&dir);
        }
    }

    for (file, content) in [("CLAUDE.md", CLAUDE_POINTER), ("AGENTS.md", AGENTS_POINTER)] {
        let path = root.join(file);
        if !protected_path(&root, &path) && !path.exists() {
            write_unchanged(&path, None, content)?;
        }
    }

    ensure_skills_link(&root, ".claude")?;
    ensure_skills_link(&root, ".agents")?;

    workflow_status(root.display().to_string())
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

    #[test]
    fn asynchronous_status_preserves_diagnostics_without_writes() {
        let root = tempfile::tempdir().unwrap();
        let project = root.path().display().to_string();
        let expected = workflow_status(project.clone()).unwrap();
        let actual = tauri::async_runtime::block_on(project_workflow_status(project)).unwrap();
        assert_eq!(
            serde_json::to_value(actual).unwrap(),
            serde_json::to_value(expected).unwrap()
        );
        assert!(!root.path().join(".agent").exists());
    }

    #[test]
    fn known_policy_and_skill_upgrades_preserve_project_rules() {
        for (version, policy) in PREVIOUS_POLICY {
            let dir = fixture(&format!("upgrade-{version}"));
            let project = dir.display().to_string();
            std::fs::create_dir_all(dir.join(".agent")).unwrap();
            let prefix = "# Project\r\n\r\nCommits and pushes are authorized. No provenance attribution.\r\n\r\n";
            let suffix = "\n## Local tail\nKeep me unchanged.\n";
            std::fs::write(
                dir.join(".agent/agent.md"),
                format!(
                    "{prefix}{BEGIN_PREFIX}{version}{BEGIN_SUFFIX}\n{policy}{END_MARKER}\n{suffix}"
                ),
            )
            .unwrap();
            for (name, old) in PREVIOUS_SPEC_SKILLS {
                let folder = dir.join(".agent/skills").join(name);
                std::fs::create_dir_all(&folder).unwrap();
                std::fs::write(folder.join("SKILL.md"), old).unwrap();
            }
            let before = workflow_status(project.clone()).unwrap();
            assert!(before
                .issues
                .iter()
                .any(|i| i.path.ends_with("spec-next/SKILL.md") && i.kind == "outdated"));
            let after = project_workflow_install(project.clone()).unwrap();
            assert_eq!(after.state, "current", "{:?}", after.pending);
            let text = std::fs::read_to_string(dir.join(".agent/agent.md")).unwrap();
            assert!(text.starts_with(prefix) && text.ends_with(suffix));
            for (name, template) in TICKET_SKILLS {
                assert_eq!(
                    std::fs::read_to_string(dir.join(".agent/skills").join(name).join("SKILL.md"))
                        .unwrap(),
                    *template
                );
            }
            project_workflow_install(project).unwrap();
            assert_eq!(
                std::fs::read_to_string(dir.join(".agent/agent.md")).unwrap(),
                text
            );
            std::fs::remove_dir_all(dir).unwrap();
        }
    }

    #[test]
    fn custom_future_and_broken_policy_blocks_are_never_replaced() {
        let dir = fixture("custom-policy");
        let project = dir.display().to_string();
        project_workflow_install(project.clone()).unwrap();
        for (text, kind) in [
            (
                policy_block().replace("## Spec workflow", "## Custom workflow"),
                "customized",
            ),
            (policy_block().replace("begin v7", "begin v99"), "newer"),
            (policy_block().replace(END_MARKER, ""), "malformed"),
            (format!("{}{}", policy_block(), policy_block()), "malformed"),
        ] {
            std::fs::write(dir.join(".agent/agent.md"), &text).unwrap();
            let status = project_workflow_install(project.clone()).unwrap();
            assert!(status
                .issues
                .iter()
                .any(|i| i.path == ".agent/agent.md" && i.kind == kind && i.action == "manual"));
            assert_eq!(
                std::fs::read_to_string(dir.join(".agent/agent.md")).unwrap(),
                text
            );
        }
        let skill = dir.join(".agent/skills/spec-next/SKILL.md");
        std::fs::write(
            &skill,
            "---\nname: spec-next\ndescription: Custom workflow\n---\nKeep this variant.\n",
        )
        .unwrap();
        let status = project_workflow_install(project).unwrap();
        assert!(status
            .issues
            .iter()
            .any(|i| i.path.ends_with("spec-next/SKILL.md") && i.kind == "customized"));
        assert!(std::fs::read_to_string(skill)
            .unwrap()
            .contains("Keep this variant."));
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn broken_and_wrong_links_are_reported_without_touching_targets() {
        let dir = fixture("wrong-links");
        let project = dir.display().to_string();
        project_workflow_install(project.clone()).unwrap();
        let link = dir.join(".claude/skills");
        std::fs::remove_file(&link).unwrap();
        std::os::unix::fs::symlink("../missing-skills", &link).unwrap();
        let status = project_workflow_install(project.clone()).unwrap();
        assert!(status
            .issues
            .iter()
            .any(|i| i.path == ".claude/skills" && i.kind == "broken_link"));
        assert_eq!(
            std::fs::read_link(&link).unwrap(),
            PathBuf::from("../missing-skills")
        );
        std::fs::remove_file(&link).unwrap();
        std::fs::create_dir(dir.join("other-skills")).unwrap();
        std::fs::write(dir.join("other-skills/keep.txt"), "keep").unwrap();
        std::os::unix::fs::symlink("../other-skills", &link).unwrap();
        let status = project_workflow_install(project.clone()).unwrap();
        assert!(status
            .issues
            .iter()
            .any(|i| i.path == ".claude/skills" && i.kind == "wrong_target"));
        assert_eq!(
            std::fs::read_to_string(dir.join("other-skills/keep.txt")).unwrap(),
            "keep"
        );
        std::fs::remove_file(&link).unwrap();
        std::fs::write(&link, "../../another-project/.agent/skills").unwrap();
        assert!(!is_symlink_stub(&link));
        project_workflow_install(project).unwrap();
        assert_eq!(
            std::fs::read_to_string(link).unwrap(),
            "../../another-project/.agent/skills"
        );
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn setup_does_not_write_through_skill_folder_symlinks() {
        let dir = fixture("skill-folder-link");
        let project = dir.display().to_string();
        project_workflow_install(project.clone()).unwrap();
        let skill_dir = dir.join(".agent/skills/spec-next");
        std::fs::rename(&skill_dir, dir.join("foreign-skill")).unwrap();
        let old = PREVIOUS_SPEC_SKILLS[0].1;
        std::fs::write(dir.join("foreign-skill/SKILL.md"), old).unwrap();
        std::os::unix::fs::symlink("../../foreign-skill", &skill_dir).unwrap();
        let status = project_workflow_install(project).unwrap();
        assert!(status
            .issues
            .iter()
            .any(|i| i.path.ends_with("spec-next/SKILL.md") && i.action == "manual"));
        assert_eq!(
            std::fs::read_to_string(dir.join("foreign-skill/SKILL.md")).unwrap(),
            old
        );
        std::fs::remove_dir_all(dir).unwrap();
    }

    /// Explicit read-only diagnostic for a real checkout; never installs anything.
    #[test]
    #[ignore = "Set SPECCIFY_CHECK_PROJECT to explicitly inspect a real checkout"]
    fn check_project_from_env() {
        let project = std::env::var("SPECCIFY_CHECK_PROJECT").expect("explicit project required");
        let status = workflow_status(project).unwrap();
        println!("{}", serde_json::to_string_pretty(&status).unwrap());
        assert_eq!(status.state, "current");
    }

    fn fixture(test: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-workflow-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn skills_link_stub_is_replaced_real_content_is_kept() {
        let dir = fixture("stub");
        std::fs::create_dir_all(dir.join(".agent/skills")).unwrap();
        std::fs::create_dir_all(dir.join(".claude")).unwrap();
        std::fs::create_dir_all(dir.join(".agents")).unwrap();

        // Gits Symlink-Hülse (Windows-Checkout ohne core.symlinks).
        std::fs::write(dir.join(".claude/skills"), "../.agent/skills").unwrap();
        assert!(is_symlink_stub(&dir.join(".claude/skills")));
        ensure_skills_link(&dir, ".claude").unwrap();
        assert!(skills_link_present(&dir, ".claude"));
        assert!(dir.join(".claude/skills").join("..").exists());

        // Eine echte Datei mit anderem Inhalt bleibt unangetastet.
        std::fs::write(dir.join(".agents/skills"), "hier stehen notizen").unwrap();
        assert!(!is_symlink_stub(&dir.join(".agents/skills")));
        ensure_skills_link(&dir, ".agents").unwrap();
        assert_eq!(
            std::fs::read_to_string(dir.join(".agents/skills")).unwrap(),
            "hier stehen notizen"
        );

        let _ = std::fs::remove_dir_all(&dir);
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

        let before = workflow_status(project.clone()).unwrap();
        assert_eq!(before.state, "missing");
        assert!(!before.pending.is_empty());

        let after = project_workflow_install(project.clone()).unwrap();
        assert_eq!(after.state, "current", "pending: {:?}", after.pending);
        assert!(dir.join(".agent/specs").is_dir());
        assert!(dir.join(".agent/playbooks").is_dir());
        assert!(dir.join(".agent/skills/spec-next/SKILL.md").is_file());
        assert!(dir.join(".agent/skills/spec-ask/SKILL.md").is_file());
        assert!(dir.join("CLAUDE.md").is_file());
        assert!(dir.join("AGENTS.md").is_file());
        let agent_md = std::fs::read_to_string(dir.join(".agent/agent.md")).unwrap();
        assert!(agent_md.contains("## Spec workflow"));
        assert!(agent_md.contains("speccify:workflow:begin v7"));

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
        // Unveränderter v1-Skill daneben: der wird beim Einrichten aufgeräumt.
        std::fs::create_dir_all(dir.join(".agent/skills/ticket-ask")).unwrap();
        std::fs::write(
            dir.join(".agent/skills/ticket-ask/SKILL.md"),
            include_str!("../templates/skill-ticket-ask.md"),
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
        assert!(!dir.join(".agent/skills/ticket-ask").exists());
        assert!(dir.join(".agent/skills/spec-ask/SKILL.md").is_file());
        let claude = std::fs::read_to_string(dir.join("CLAUDE.md")).unwrap();
        assert_eq!(claude, "# Eigenes CLAUDE.md ohne Verweis\n");
        let agent_md = std::fs::read_to_string(dir.join(".agent/agent.md")).unwrap();
        assert!(agent_md.starts_with("# Bestand\n"));
        assert!(agent_md.contains("## Spec workflow"));
        // Host-Datei ohne Verweis wird gemeldet, nicht angefasst.
        assert_eq!(status.state, "outdated");
        assert!(status
            .pending
            .iter()
            .any(|entry| entry.contains("verweist nicht auf .agent/agent.md")));

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
