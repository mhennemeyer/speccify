//! Skill-Quellen pro Projekt + Browser (Plan projektfenster.md, D21/D24).
//!
//! Eine Quelle ist ein Repo/Verzeichnis, in dem Skills definiert werden.
//! Default kommt aus den Dashboard-Settings (`skill_library`), Projekte
//! überschreiben/ergänzen über `.agent/settings.json` → `speccify.sources`
//! (D21, Kundenprojekte mit eigenem Skill-Repo). Der Browser liest nativ
//! (D14): rekursiv alle `SKILL.md`, die **Ordnerstruktur ist die
//! Organisation** und wandert als Kategorie in die Anzeige (D24). Der
//! Import selbst ist ein Agent-/CLI-Schritt — die App baut nur das
//! `speccify add/expand`-Kommando und tippt es ins Projekt-Terminal
//! (dieselbe Haltung wie D14: Aktionen laufen über den Agenten).

use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::project_cmd::resolve_project_root;

fn expand_source(raw: &str) -> Result<PathBuf, String> {
    let trimmed = raw.trim();
    let path = if let Some(rest) = trimmed.strip_prefix("~/") {
        crate::settings::home_dir()?.join(rest)
    } else {
        PathBuf::from(trimmed)
    };
    if !path.is_dir() {
        return Err(format!("Keine Quelle: {}", path.display()));
    }
    Ok(path)
}

#[derive(Serialize)]
pub struct SkillSources {
    /// Dashboard-Default (`skill_library` in den App-Settings).
    default: Option<String>,
    /// Projekt-Quellen aus `.agent/settings.json` → `speccify.sources`.
    sources: Vec<String>,
}

#[tauri::command]
pub fn project_skill_sources(project: String) -> Result<SkillSources, String> {
    let settings = crate::workflow_setup::project_settings_get(project)?;
    let sources = settings
        .get("speccify")
        .and_then(|s| s.get("sources"))
        .and_then(|s| s.as_array())
        .map(|entries| {
            entries
                .iter()
                .filter_map(|entry| entry.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default();
    let default = crate::settings::get_settings()?.skill_library;
    Ok(SkillSources { default, sources })
}

#[derive(Serialize)]
pub struct BrowseSkill {
    name: String,
    /// Ordner-Kategorie relativ zur Quelle ("" = Wurzel) — die Organisation.
    category: String,
    /// SKILL.md relativ zur Quelle (für die Vorschau).
    file: String,
    description: Option<String>,
    /// `@<scope>/<name>` wenn `metadata.speccify.scope` gesetzt ist.
    id: Option<String>,
}

fn frontmatter_of(text: &str) -> Option<serde_yaml::Value> {
    let rest = text.strip_prefix("---\n")?;
    let end = rest.find("\n---")?;
    serde_yaml::from_str(&rest[..end]).ok()
}

fn collect_skills(root: &Path, dir: &Path, depth: u8, out: &mut Vec<BrowseSkill>) {
    if depth > 6 {
        return;
    }
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    let mut paths: Vec<PathBuf> = entries.filter_map(Result::ok).map(|e| e.path()).collect();
    paths.sort();
    for path in paths {
        if !path.is_dir() {
            continue;
        }
        let name = path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default();
        if name.starts_with('.') || name == "node_modules" || name == "target" {
            continue;
        }
        let skill_md = path.join("SKILL.md");
        if skill_md.is_file() {
            let frontmatter = std::fs::read_to_string(&skill_md)
                .ok()
                .as_deref()
                .and_then(frontmatter_of);
            let description = frontmatter
                .as_ref()
                .and_then(|fm| fm.get("description"))
                .and_then(|d| d.as_str())
                .map(str::to_string);
            let scope = frontmatter
                .as_ref()
                .and_then(|fm| fm.get("metadata"))
                .and_then(|m| m.get("speccify.scope"))
                .and_then(|s| s.as_str())
                .map(str::to_string);
            let category = path
                .parent()
                .and_then(|parent| parent.strip_prefix(root).ok())
                .map(|rel| rel.to_string_lossy().replace('\\', "/"))
                .unwrap_or_default();
            out.push(BrowseSkill {
                id: scope.map(|scope| format!("@{scope}/{name}")),
                file: skill_md
                    .strip_prefix(root)
                    .unwrap_or(&skill_md)
                    .to_string_lossy()
                    .replace('\\', "/"),
                description,
                category,
                name,
            });
            continue; // in Skill-Bundles nicht weiter absteigen
        }
        collect_skills(root, &path, depth + 1, out);
    }
}

/// Alle Skills einer Quelle, Ordnerstruktur als Kategorie.
#[tauri::command]
pub fn source_browse(source: String) -> Result<Vec<BrowseSkill>, String> {
    let root = expand_source(&source)?;
    let mut skills = Vec::new();
    collect_skills(&root, &root, 0, &mut skills);
    skills.sort_by(|a, b| (&a.category, &a.name).cmp(&(&b.category, &b.name)));
    Ok(skills)
}

/// SKILL.md aus einer Quelle lesen (Guard: relativ, unterhalb der Quelle).
#[tauri::command]
pub fn source_skill_read(source: String, file: String) -> Result<String, String> {
    let root = expand_source(&source)?;
    let path = crate::project_cmd::safe_project_path(&root, &file)?;
    std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))
}

/// Nur Validierung + Normalisierung — gespeichert wird über den
/// Settings-Store (`speccify.sources`), das macht das Frontend.
#[tauri::command]
pub fn source_validate(source: String) -> Result<String, String> {
    Ok(expand_source(&source)?.display().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn browse_uses_folder_structure_as_category() {
        let dir =
            std::env::temp_dir().join(format!("speccify-sources-test-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        // Wurzel-Skill + verschachtelte Skills + Rauschen.
        std::fs::create_dir_all(dir.join("alpha")).unwrap();
        std::fs::write(
            dir.join("alpha/SKILL.md"),
            "---\nname: alpha\ndescription: Wurzel-Skill.\nmetadata:\n  speccify.scope: acme\n---\n# Alpha\n",
        )
        .unwrap();
        std::fs::create_dir_all(dir.join("mobil/ios/push-setup")).unwrap();
        std::fs::write(
            dir.join("mobil/ios/push-setup/SKILL.md"),
            "---\nname: push-setup\ndescription: Push einrichten.\n---\n# Push\n",
        )
        .unwrap();
        std::fs::create_dir_all(dir.join("node_modules/junk")).unwrap();
        std::fs::write(dir.join("node_modules/junk/SKILL.md"), "kein skill").unwrap();

        let skills = source_browse(dir.display().to_string()).unwrap();
        assert_eq!(skills.len(), 2);
        assert_eq!(skills[0].name, "alpha");
        assert_eq!(skills[0].category, "");
        assert_eq!(skills[0].id.as_deref(), Some("@acme/alpha"));
        assert_eq!(skills[1].name, "push-setup");
        assert_eq!(skills[1].category, "mobil/ios");
        assert_eq!(skills[1].id, None);

        let text = source_skill_read(
            dir.display().to_string(),
            "mobil/ios/push-setup/SKILL.md".into(),
        )
        .unwrap();
        assert!(text.contains("# Push"));
        let evil = source_skill_read(dir.display().to_string(), "../raus.md".into()).unwrap_err();
        assert!(evil.contains("aus dem Projekt heraus"));

        let _ = std::fs::remove_dir_all(&dir);
    }
}
