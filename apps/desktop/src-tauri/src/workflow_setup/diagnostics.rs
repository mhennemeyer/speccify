use super::*;

fn normalized(text: &str) -> String {
    text.replace("\r\n", "\n")
        .trim_end_matches('\n')
        .to_string()
}

/// Managed writes never follow a project-owned symlink into another location.
pub(super) fn protected_path(root: &Path, path: &Path) -> bool {
    path.ancestors()
        .take_while(|p| *p != root)
        .any(|p| p.is_symlink())
}

pub(super) fn file_state(
    root: &Path,
    path: &Path,
    current: &str,
    previous: &[&str],
) -> &'static str {
    if protected_path(root, path) {
        return "customized";
    }
    match std::fs::read_to_string(path) {
        Ok(text) => text_state(&text, current, previous),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => "missing",
        Err(_) => "unreadable",
    }
}

pub(super) fn text_state(text: &str, current: &str, previous: &[&str]) -> &'static str {
    if normalized(text) == normalized(current) {
        "current"
    } else if previous
        .iter()
        .any(|old| normalized(text) == normalized(old))
    {
        "outdated"
    } else {
        "customized"
    }
}

pub(super) fn policy_state(root: &Path) -> (Option<u32>, &'static str) {
    let path = root.join(".agent/agent.md");
    if protected_path(root, &path) {
        return (None, "customized");
    }
    let text = match std::fs::read_to_string(path) {
        Ok(text) => text,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return (None, "missing"),
        Err(_) => return (None, "unreadable"),
    };
    policy_text_state(&text)
}

pub(super) fn policy_text_state(text: &str) -> (Option<u32>, &'static str) {
    let version = installed_version(text);
    let starts = text.matches(BEGIN_PREFIX).count();
    let ends = text.matches(END_MARKER).count();
    if starts == 0 && ends == 0 {
        return (None, "missing");
    }
    if starts != 1 || ends != 1 {
        return (version, "malformed");
    }
    let start = text.find(BEGIN_PREFIX).unwrap();
    let end = text.find(END_MARKER).unwrap();
    let Some(line_end) = text[start..].find('\n').map(|n| start + n) else {
        return (version, "malformed");
    };
    if line_end >= end
        || (start > 0 && text.as_bytes()[start - 1] != b'\n')
        || (end > 0 && text.as_bytes()[end - 1] != b'\n')
        || !matches!(
            text[end + END_MARKER.len()..].chars().next(),
            None | Some('\n') | Some('\r')
        )
    {
        return (version, "malformed");
    }
    let Some(version) = version else {
        return (None, "malformed");
    };
    if text[start..line_end].trim_end_matches('\r')
        != format!("{BEGIN_PREFIX}{version}{BEGIN_SUFFIX}")
    {
        return (Some(version), "malformed");
    }
    if version > WORKFLOW_VERSION {
        return (Some(version), "newer");
    }
    let content = &text[line_end + 1..end];
    let state = if version == WORKFLOW_VERSION && normalized(content) == normalized(POLICY) {
        "current"
    } else if PREVIOUS_POLICY
        .iter()
        .any(|(v, old)| *v == version && normalized(content) == normalized(old))
    {
        "outdated"
    } else {
        "customized"
    };
    (Some(version), state)
}

fn issue(issues: &mut Vec<WorkflowIssue>, path: &str, kind: &str, repair: bool, detail: &str) {
    if kind == "current" {
        return;
    }
    issues.push(WorkflowIssue {
        path: path.into(),
        kind: kind.into(),
        action: if repair { "install" } else { "manual" }.into(),
        message: format!(
            "{path}: {detail}{}",
            if repair {
                ""
            } else {
                " (manuell prüfen; bleibt erhalten)"
            }
        ),
    });
}

fn describe(kind: &str) -> &'static str {
    match kind {
        "missing" => "fehlt",
        "outdated" => "bekannte ältere Vorlage aktualisieren",
        "newer" => "neuere unbekannte Version",
        "malformed" => "unvollständige oder mehrdeutige Workflow-Marker",
        "unreadable" => "nicht lesbar oder kein reguläres Dokument",
        _ => "individuell angepasst oder verlinkt",
    }
}

pub(super) fn collect_issues(root: &Path) -> (Option<u32>, Vec<WorkflowIssue>) {
    let mut issues = Vec::new();
    let (version, state) = policy_state(root);
    issue(
        &mut issues,
        ".agent/agent.md",
        state,
        matches!(state, "missing" | "outdated"),
        describe(state),
    );
    for dir in [".agent/specs", ".agent/playbooks", ".agent/skills"] {
        let path = root.join(dir);
        if protected_path(root, &path) || (path.exists() && !path.is_dir()) {
            issue(
                &mut issues,
                dir,
                "customized",
                false,
                "kein verwaltbares Projektverzeichnis",
            );
        } else if !path.is_dir() {
            issue(&mut issues, dir, "missing", true, "Verzeichnis anlegen");
        }
    }
    for (name, current) in TICKET_SKILLS {
        let path = format!(".agent/skills/{name}/SKILL.md");
        let previous: Vec<_> = PREVIOUS_SPEC_SKILLS
            .iter()
            .filter(|(id, _)| id == name)
            .map(|(_, text)| *text)
            .collect();
        let state = file_state(root, &root.join(&path), current, &previous);
        issue(
            &mut issues,
            &path,
            state,
            matches!(state, "missing" | "outdated"),
            describe(state),
        );
    }
    for file in ["CLAUDE.md", "AGENTS.md"] {
        let path = root.join(file);
        if protected_path(root, &path) || (path.exists() && !path.is_file()) {
            issue(
                &mut issues,
                file,
                "customized",
                false,
                "vorhandener Link oder fremder Inhalt",
            );
        } else if !path.exists() {
            issue(&mut issues, file, "missing", true, "Verweis anlegen");
        } else if !mentions_agent_source(&path) {
            issue(
                &mut issues,
                file,
                "customized",
                false,
                "verweist nicht auf .agent/agent.md",
            );
        }
    }
    for host in [".claude", ".agents"] {
        let relative = format!("{host}/skills");
        let path = root.join(&relative);
        if protected_path(root, &root.join(host)) {
            issue(
                &mut issues,
                &relative,
                "wrong_target",
                false,
                "Host-Verzeichnis selbst verlinkt",
            );
        } else if skills_link_present(root, host) {
            continue;
        } else if path.is_symlink() {
            let target = std::fs::read_link(&path)
                .map(|p| p.display().to_string())
                .unwrap_or_default();
            let kind = if path.exists() {
                "wrong_target"
            } else {
                "broken_link"
            };
            issue(
                &mut issues,
                &relative,
                kind,
                false,
                &format!("Linkziel {target} ist nicht das gültige .agent/skills-Verzeichnis"),
            );
        } else if is_symlink_stub(&path) {
            issue(
                &mut issues,
                &relative,
                "outdated",
                true,
                "Git-Link-Hülse durch Skill-Link ersetzen",
            );
        } else if !path.exists() {
            issue(
                &mut issues,
                &relative,
                "missing",
                true,
                "Skill-Link anlegen",
            );
        } else {
            issue(
                &mut issues,
                &relative,
                "wrong_target",
                false,
                "eigenes Verzeichnis/Datei statt Link auf .agent/skills",
            );
        }
    }
    (version, issues)
}
