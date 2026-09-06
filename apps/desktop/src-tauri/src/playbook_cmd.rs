//! Playbooks (Plan projektfenster.md, D30): stehende Anleitungen unter
//! `.agent/playbooks/` — im Gegensatz zu Plänen ohne Lifecycle. Ein Plan
//! wird wie ein Projekt abgearbeitet und ist dann fertig; ein Playbook
//! beschreibt einen wiederkehrenden Ablauf (Release, Deploy, Onboarding)
//! und bleibt bestehen. Format: optionales flaches Frontmatter
//! (`description:`) plus Markdown-Body; der Titel ist die erste
//! `# `-Überschrift, sonst der Dateiname. Gelesen/geschrieben wird der
//! Inhalt über `project_read_file`/`project_write_file` — hier leben nur
//! Liste, Anlegen und Löschen.

use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::project_cmd::{resolve_project_root, safe_project_path};

fn playbooks_dir(root: &Path) -> PathBuf {
    root.join(".agent/playbooks")
}

fn is_playbook_file(root: &Path, path: &Path) -> bool {
    path.starts_with(playbooks_dir(root)) && path.extension().is_some_and(|ext| ext == "md")
}

/// Zeilen zwischen den `---`-Markern (flach; kein Frontmatter ⇒ leer).
fn frontmatter_lines(text: &str) -> Vec<&str> {
    let Some(rest) = text.strip_prefix("---\n") else {
        return Vec::new();
    };
    match rest.find("\n---") {
        Some(end) => rest[..end].lines().collect(),
        None => Vec::new(),
    }
}

fn frontmatter_value(text: &str, key: &str) -> Option<String> {
    frontmatter_lines(text).into_iter().find_map(|line| {
        let (k, value) = line.split_once(':')?;
        (k.trim() == key).then(|| value.trim().to_string())
    })
}

#[derive(Serialize)]
pub struct PlaybookEntry {
    /// Relativ zur Projektwurzel — zugleich der Schlüssel für
    /// `project_read_file`/`project_write_file`/`project_playbook_delete`.
    file: String,
    title: String,
    description: Option<String>,
}

/// Playbooks aus `.agent/playbooks/`. Fehlender Ordner ⇒ leere Liste.
#[tauri::command]
pub fn project_playbooks(project: String) -> Result<Vec<PlaybookEntry>, String> {
    let root = resolve_project_root(&project)?;
    let mut out = Vec::new();
    let Ok(entries) = std::fs::read_dir(playbooks_dir(&root)) else {
        return Ok(out);
    };
    let mut paths: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "md"))
        .collect();
    paths.sort();
    for path in paths {
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        let fallback = path
            .file_stem()
            .map(|stem| stem.to_string_lossy().into_owned())
            .unwrap_or_default();
        out.push(PlaybookEntry {
            file: path
                .strip_prefix(&root)
                .unwrap_or(&path)
                .to_string_lossy()
                .replace('\\', "/"),
            title: text
                .lines()
                .find_map(|line| line.strip_prefix("# "))
                .map(|title| title.trim().to_string())
                .unwrap_or(fallback),
            description: frontmatter_value(&text, "description").filter(|d| !d.is_empty()),
        });
    }
    Ok(out)
}

/// Dateiname aus dem Anzeigenamen: ASCII-alnum bleibt, Umlaute werden
/// transliteriert, alles andere wird `-` (zusammengefasst).
pub(crate) fn slugify(name: &str) -> String {
    let mut slug = String::new();
    for ch in name.to_lowercase().chars() {
        match ch {
            'a'..='z' | '0'..='9' => slug.push(ch),
            'ä' => slug.push_str("ae"),
            'ö' => slug.push_str("oe"),
            'ü' => slug.push_str("ue"),
            'ß' => slug.push_str("ss"),
            _ => {
                if !slug.ends_with('-') {
                    slug.push('-');
                }
            }
        }
    }
    slug.trim_matches('-').to_string()
}

/// Legt ein Playbook als `# <Name>`-Gerüst an. Rückgabe: der Pfad relativ
/// zur Projektwurzel. Existierendes wird nie überschrieben.
#[tauri::command]
pub fn project_playbook_create(project: String, name: String) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    let slug = slugify(&name);
    if slug.is_empty() {
        return Err("Name ergibt keinen Dateinamen.".into());
    }
    let dir = playbooks_dir(&root);
    std::fs::create_dir_all(&dir).map_err(|e| format!("{}: {e}", dir.display()))?;
    let path = dir.join(format!("{slug}.md"));
    if path.exists() {
        return Err(format!("Gibt es schon: .agent/playbooks/{slug}.md"));
    }
    std::fs::write(&path, format!("# {}\n\n", name.trim()))
        .map_err(|e| format!("{}: {e}", path.display()))?;
    Ok(format!(".agent/playbooks/{slug}.md"))
}

#[tauri::command]
pub fn project_playbook_delete(project: String, file: String) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    if !is_playbook_file(&root, &path) {
        return Err(format!("Kein Playbook: {file}"));
    }
    std::fs::remove_file(&path).map_err(|e| format!("{}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(test: &str) -> std::path::PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-playbook-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join(".agent")).unwrap();
        dir
    }

    #[test]
    fn create_list_delete_roundtrip() {
        let dir = fixture("roundtrip");
        let project = dir.to_string_lossy().into_owned();

        // Ordner fehlt noch ⇒ leere Liste, kein Fehler.
        assert!(project_playbooks(project.clone()).unwrap().is_empty());

        let file = project_playbook_create(project.clone(), "Release fährt raus".into()).unwrap();
        assert_eq!(file, ".agent/playbooks/release-faehrt-raus.md");
        assert!(project_playbook_create(project.clone(), "Release fährt raus".into()).is_err());

        // Beschreibung kommt aus dem Frontmatter, Titel aus der Überschrift.
        std::fs::write(
            dir.join(".agent/playbooks/release-faehrt-raus.md"),
            "---\ndescription: Vom Tag zum veröffentlichten Release\n---\n# Release\n\n1. Taggen\n",
        )
        .unwrap();
        let list = project_playbooks(project.clone()).unwrap();
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].title, "Release");
        assert_eq!(
            list[0].description.as_deref(),
            Some("Vom Tag zum veröffentlichten Release")
        );

        project_playbook_delete(project.clone(), file).unwrap();
        assert!(project_playbooks(project).unwrap().is_empty());

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn delete_refuses_paths_outside_playbooks() {
        let dir = fixture("guard");
        let project = dir.to_string_lossy().into_owned();
        std::fs::create_dir_all(dir.join(".agent/plans")).unwrap();
        std::fs::write(dir.join(".agent/plans/plan.md"), "# Plan\n").unwrap();

        assert!(project_playbook_delete(project.clone(), ".agent/plans/plan.md".into()).is_err());
        assert!(project_playbook_delete(project, "../auswaerts.md".into()).is_err());
        assert!(dir.join(".agent/plans/plan.md").exists());

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn slugify_handles_umlauts_and_noise() {
        assert_eq!(slugify("Übergabe an QA!"), "uebergabe-an-qa");
        assert_eq!(slugify("  Deploy → Prod  "), "deploy-prod");
        assert_eq!(slugify("///"), "");
    }
}
