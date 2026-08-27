//! Projektfenster (Plan projektfenster.md, P1): Projekte in eigenen
//! Fenstern öffnen und ihre Bestände **nativ lesen** (D14) — Pläne aus
//! `.agent/plans/`, Skills aus `.agent/skills/` samt Herkunft aus
//! `.agent/speccify/expansions.yaml`. Gehandelt (expand, tool check, …)
//! wird im Agent-Terminal des Fensters, nicht hier.

use std::collections::HashMap;
use std::path::{Component, Path, PathBuf};
use std::sync::Mutex;

use serde::Serialize;
use tauri::{AppHandle, Manager, State};

/// Fenster-Label → Projektwurzel. Das Fenster fragt nach dem Laden mit
/// `project_current`, welche Wurzel zu ihm gehört — kein Zustand in der
/// URL, damit Reload und Plattformunterschiede keine Rolle spielen.
pub struct ProjectWindows(Mutex<HashMap<String, String>>);

impl Default for ProjectWindows {
    fn default() -> Self {
        Self(Mutex::new(HashMap::new()))
    }
}

fn window_label(root: &Path) -> String {
    use std::hash::{Hash, Hasher};
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    root.hash(&mut hasher);
    format!("project-{:016x}", hasher.finish())
}

/// Pfad aus der UI → existierende, kanonische Projektwurzel.
fn resolve_project_root(raw: &str) -> Result<PathBuf, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err("Kein Projektpfad angegeben.".into());
    }
    let path = if let Some(rest) = trimmed.strip_prefix("~/") {
        crate::settings::home_dir()?.join(rest)
    } else {
        PathBuf::from(trimmed)
    };
    if !path.is_dir() {
        return Err(format!("Kein Verzeichnis: {}", path.display()));
    }
    path.canonicalize()
        .map_err(|e| format!("{}: {e}", path.display()))
}

// --- Zuletzt geöffnete Projekte ---------------------------------------------
// Eigene Datei statt AppSettings: die SettingsView schreibt das ganze
// Settings-Objekt zurück — ein Feld dort würde bei jedem Save geleert.

fn recent_path() -> Result<PathBuf, String> {
    Ok(crate::settings::home_dir()?
        .join(".speccify")
        .join("recent-projects.json"))
}

fn load_recent() -> Vec<String> {
    recent_path()
        .ok()
        .and_then(|path| std::fs::read_to_string(path).ok())
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_default()
}

fn remember_recent(root: &Path) {
    let entry = root.display().to_string();
    let mut recent = load_recent();
    recent.retain(|known| known != &entry);
    recent.insert(0, entry);
    recent.truncate(10);
    if let Ok(path) = recent_path() {
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        if let Ok(json) = serde_json::to_string_pretty(&recent) {
            let _ = std::fs::write(path, json + "\n");
        }
    }
}

/// Zuletzt geöffnete Projekte, verschwundene Verzeichnisse ausgefiltert.
#[tauri::command]
pub fn project_recent() -> Vec<String> {
    load_recent()
        .into_iter()
        .filter(|path| Path::new(path).is_dir())
        .collect()
}

// --- Fenster ----------------------------------------------------------------

/// Öffnet das Projektfenster (oder fokussiert das vorhandene). Lädt die
/// eigene SPA; die erkennt am Fenster-Label den Projektmodus und holt die
/// Wurzel über `project_current` (D15). **async**, weil ein synchroner
/// Command auf Windows beim Fenster-Bau den Main-Thread blockiert
/// (wry#583) — das Fenster blieb dort auf about:blank.
#[tauri::command]
pub async fn project_open(
    app: AppHandle,
    state: State<'_, ProjectWindows>,
    path: String,
) -> Result<String, String> {
    let root = resolve_project_root(&path)?;
    let label = window_label(&root);
    if let Some(existing) = app.get_webview_window(&label) {
        let _ = existing.set_focus();
        return Ok(root.display().to_string());
    }

    let name = root
        .file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_else(|| root.display().to_string());

    // Vor dem Build registrieren: die SPA fragt sofort nach der Wurzel.
    state
        .0
        .lock()
        .unwrap()
        .insert(label.clone(), root.display().to_string());

    let window = tauri::WebviewWindowBuilder::new(
        &app,
        label.clone(),
        tauri::WebviewUrl::App("index.html".into()),
    )
    .title(format!("{name} — Speccify"))
    .inner_size(1360.0, 880.0)
    .min_inner_size(900.0, 600.0)
    .build()
    .map_err(|e| {
        state.0.lock().unwrap().remove(&label);
        format!("Fenster: {e}")
    })?;

    let app_for_close = app.clone();
    let label_for_close = label.clone();
    window.on_window_event(move |event| {
        if matches!(event, tauri::WindowEvent::Destroyed) {
            let windows: State<ProjectWindows> = app_for_close.state();
            windows.0.lock().unwrap().remove(&label_for_close);
        }
    });

    remember_recent(&root);
    Ok(root.display().to_string())
}

/// Die Projektwurzel des aufrufenden Fensters (None im Dashboard).
#[tauri::command]
pub fn project_current(
    window: tauri::WebviewWindow,
    state: State<ProjectWindows>,
) -> Option<String> {
    state.0.lock().unwrap().get(window.label()).cloned()
}

// --- Bestände lesen ---------------------------------------------------------

/// `---`-Frontmatter abtrennen: (YAML-Wert, Body). Kein Frontmatter oder
/// kaputtes YAML ist kein Fehler — dann gibt es eben keine Metadaten
/// (dieselbe Haltung wie `skill.py`).
fn split_frontmatter(text: &str) -> (Option<serde_yaml::Value>, &str) {
    let Some(rest) = text.strip_prefix("---\n") else {
        return (None, text);
    };
    let Some(end) = rest.find("\n---") else {
        return (None, text);
    };
    let body = rest[end + 4..].trim_start_matches('\n');
    (serde_yaml::from_str(&rest[..end]).ok(), body)
}

fn frontmatter_str(value: &Option<serde_yaml::Value>, key: &str) -> Option<String> {
    value
        .as_ref()?
        .get(key)
        .and_then(|entry| match entry {
            serde_yaml::Value::String(text) => Some(text.clone()),
            other => serde_yaml::to_string(other)
                .ok()
                .map(|text| text.trim().to_string()),
        })
        .map(|text| text.trim().to_string())
        .filter(|text| !text.is_empty())
}

/// Erste `# `-Überschrift des Bodys (Titel eines Plans).
fn first_heading(body: &str) -> Option<String> {
    body.lines()
        .find_map(|line| line.strip_prefix("# "))
        .map(|title| title.trim().to_string())
}

#[derive(Serialize)]
pub struct PlanEntry {
    /// Relativ zur Projektwurzel — zugleich der Schlüssel für `project_read_file`.
    file: String,
    title: String,
    lifecycle: Option<String>,
    status: Option<String>,
    archived: bool,
}

fn plans_in(dir: &Path, root: &Path, archived: bool, out: &mut Vec<PlanEntry>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
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
        let (frontmatter, body) = split_frontmatter(&text);
        let fallback = path
            .file_stem()
            .map(|stem| stem.to_string_lossy().into_owned())
            .unwrap_or_default();
        out.push(PlanEntry {
            file: path
                .strip_prefix(root)
                .unwrap_or(&path)
                .to_string_lossy()
                .into_owned(),
            title: first_heading(body).unwrap_or(fallback),
            lifecycle: frontmatter_str(&frontmatter, "lifecycle"),
            status: frontmatter_str(&frontmatter, "status"),
            archived,
        });
    }
}

/// Pläne aus `.agent/plans/` (+ `archive/`). Fehlende Ordner ⇒ leere Liste.
#[tauri::command]
pub fn project_plans(project: String) -> Result<Vec<PlanEntry>, String> {
    let root = resolve_project_root(&project)?;
    let mut plans = Vec::new();
    plans_in(&root.join(".agent/plans"), &root, false, &mut plans);
    plans_in(&root.join(".agent/plans/archive"), &root, true, &mut plans);
    Ok(plans)
}

#[derive(Serialize)]
pub struct SkillOrigin {
    source: String,
    version: Option<String>,
    expanded: Option<String>,
    tools: Vec<String>,
}

#[derive(Serialize)]
pub struct SkillEntry {
    name: String,
    /// Relativ zur Projektwurzel (für `project_read_file`).
    file: String,
    description: Option<String>,
    origin: Option<SkillOrigin>,
}

fn expansion_origins(root: &Path) -> HashMap<String, SkillOrigin> {
    let Ok(text) = std::fs::read_to_string(root.join(".agent/speccify/expansions.yaml")) else {
        return HashMap::new();
    };
    let Ok(value) = serde_yaml::from_str::<serde_yaml::Value>(&text) else {
        return HashMap::new();
    };
    let Some(skills) = value.get("skills").and_then(|skills| skills.as_mapping()) else {
        return HashMap::new();
    };
    skills
        .iter()
        .filter_map(|(name, entry)| {
            let name = name.as_str()?.to_string();
            let source = entry.get("source")?.as_str()?.to_string();
            let tools = entry
                .get("tools")
                .and_then(|tools| tools.as_sequence())
                .map(|tools| {
                    tools
                        .iter()
                        .filter_map(|tool| {
                            // Je nach Nachweis-Stand String oder Mapping mit `name`.
                            tool.as_str()
                                .map(str::to_string)
                                .or_else(|| tool.get("name")?.as_str().map(str::to_string))
                        })
                        .collect()
                })
                .unwrap_or_default();
            Some((
                name,
                SkillOrigin {
                    source,
                    version: entry
                        .get("version")
                        .and_then(|version| version.as_str())
                        .map(str::to_string),
                    expanded: entry
                        .get("expanded")
                        .and_then(|expanded| expanded.as_str())
                        .map(str::to_string),
                    tools,
                },
            ))
        })
        .collect()
}

/// Skills aus `.agent/skills/` mit Herkunft aus `expansions.yaml`.
#[tauri::command]
pub fn project_skills(project: String) -> Result<Vec<SkillEntry>, String> {
    let root = resolve_project_root(&project)?;
    let mut origins = expansion_origins(&root);
    let skills_dir = root.join(".agent/skills");
    let Ok(entries) = std::fs::read_dir(&skills_dir) else {
        return Ok(Vec::new());
    };
    let mut dirs: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.join("SKILL.md").is_file())
        .collect();
    dirs.sort();
    Ok(dirs
        .into_iter()
        .map(|dir| {
            let name = dir
                .file_name()
                .map(|name| name.to_string_lossy().into_owned())
                .unwrap_or_default();
            let skill_md = dir.join("SKILL.md");
            let frontmatter = std::fs::read_to_string(&skill_md)
                .ok()
                .and_then(|text| split_frontmatter(&text).0);
            SkillEntry {
                file: skill_md
                    .strip_prefix(&root)
                    .unwrap_or(&skill_md)
                    .to_string_lossy()
                    .into_owned(),
                description: frontmatter_str(&frontmatter, "description"),
                origin: origins.remove(&name),
                name,
            }
        })
        .collect())
}

/// Eine Datei unterhalb der Projektwurzel lesen (Pläne, SKILL.md, …).
/// Relative Pfade ohne `..` — mehr braucht die Anzeige nicht.
#[tauri::command]
pub fn project_read_file(project: String, file: String) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    let relative = Path::new(&file);
    let escapes = relative.is_absolute()
        || relative
            .components()
            .any(|component| matches!(component, Component::ParentDir | Component::Prefix(_)));
    if escapes {
        return Err(format!("Pfad zeigt aus dem Projekt heraus: {file}"));
    }
    let path = root.join(relative);
    std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Je Test ein eigenes Verzeichnis — die Tests laufen parallel.
    fn project_fixture(test: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("speccify-{test}-test-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        for sub in [
            ".agent/plans/archive",
            ".agent/skills/alpha",
            ".agent/speccify",
        ] {
            std::fs::create_dir_all(dir.join(sub)).unwrap();
        }
        std::fs::write(
            dir.join(".agent/plans/aktuell.md"),
            "---\nlifecycle: active\nstatus: Bauen\n---\n# Plan: Aktuell\n\nInhalt.\n",
        )
        .unwrap();
        std::fs::write(
            dir.join(".agent/plans/archive/alt.md"),
            "# Alter Plan ohne Frontmatter\n",
        )
        .unwrap();
        std::fs::write(
            dir.join(".agent/skills/alpha/SKILL.md"),
            "---\nname: alpha\ndescription: Erster Skill.\n---\n# Alpha\n",
        )
        .unwrap();
        std::fs::write(
            dir.join(".agent/speccify/expansions.yaml"),
            "schema_version: 1\nskills:\n  alpha:\n    source: '@speccify/alpha'\n    version: 1.0.0\n    expanded: '2026-08-21'\n    tools:\n    - verify-something\n",
        )
        .unwrap();
        dir
    }

    #[test]
    fn plans_and_skills_are_read_natively() {
        let dir = project_fixture("read");
        let project = dir.to_string_lossy().into_owned();

        let plans = project_plans(project.clone()).unwrap();
        assert_eq!(plans.len(), 2);
        let active = plans.iter().find(|plan| !plan.archived).unwrap();
        assert_eq!(active.title, "Plan: Aktuell");
        assert_eq!(active.lifecycle.as_deref(), Some("active"));
        assert_eq!(active.status.as_deref(), Some("Bauen"));
        let archived = plans.iter().find(|plan| plan.archived).unwrap();
        assert_eq!(archived.title, "Alter Plan ohne Frontmatter");
        assert_eq!(archived.lifecycle, None);

        let skills = project_skills(project.clone()).unwrap();
        assert_eq!(skills.len(), 1);
        assert_eq!(skills[0].name, "alpha");
        assert_eq!(skills[0].description.as_deref(), Some("Erster Skill."));
        let origin = skills[0]
            .origin
            .as_ref()
            .expect("Herkunft aus expansions.yaml");
        assert_eq!(origin.source, "@speccify/alpha");
        assert_eq!(origin.version.as_deref(), Some("1.0.0"));
        assert_eq!(origin.tools, vec!["verify-something".to_string()]);

        let body = project_read_file(project, active.file.clone()).unwrap();
        assert!(body.contains("# Plan: Aktuell"));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn read_file_rejects_paths_that_escape_the_project() {
        let dir = project_fixture("escape");
        let project = dir.to_string_lossy().into_owned();
        for evil in ["../secrets.txt", "/etc/passwd", "a/../../b.md"] {
            let error = project_read_file(project.clone(), evil.into()).unwrap_err();
            assert!(error.contains("aus dem Projekt heraus"), "{evil} → {error}");
        }
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn frontmatter_split_tolerates_missing_or_broken_frontmatter() {
        let (none, body) = split_frontmatter("# Nur Body\n");
        assert!(none.is_none());
        assert_eq!(body, "# Nur Body\n");

        let (broken, body) = split_frontmatter("---\n[kein: yaml\n---\n# B\n");
        assert!(broken.is_none());
        assert_eq!(body, "# B\n");
    }

    /// Ein Projekt, das noch kein `.agent/` hat, ist kein Fehler — die Tabs
    /// zeigen dann leere Listen (und das Terminal ist trotzdem nützlich).
    #[test]
    fn projects_without_agent_dir_yield_empty_lists() {
        let dir = std::env::temp_dir().join(format!("speccify-empty-test-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let project = dir.to_string_lossy().into_owned();
        assert!(project_plans(project.clone()).unwrap().is_empty());
        assert!(project_skills(project).unwrap().is_empty());
        let _ = std::fs::remove_dir_all(&dir);
    }
}
