//! Local workspace discovery and metadata. Contract: docs/workspaces.md.
use serde::{Deserialize, Serialize};
use std::collections::{HashSet, VecDeque};
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{Duration, Instant};

static STORE_LOCK: Mutex<()> = Mutex::new(());
const EXCLUDED: &[&str] = &[
    ".git",
    ".agent",
    ".agents",
    ".claude",
    ".codex",
    "node_modules",
    "target",
    "dist",
    "build",
    ".venv",
    "venv",
    "vendor",
    ".next",
    ".cache",
    "__pycache__",
    "Pods",
    ".idea",
    ".gradle",
];

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Worktree {
    id: String,
    path: String,
    relative_path: String,
    markers: Vec<String>,
    available: bool,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Repository {
    id: String,
    name: String,
    common_dir: Option<String>,
    default_project_id: String,
    worktrees: Vec<Worktree>,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Project {
    id: String,
    name: String,
    repository_ids: Vec<String>,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Workspace {
    id: String,
    name: String,
    root: String,
    revision: u64,
    projects: Vec<Project>,
    repositories: Vec<Repository>,
    warnings: Vec<String>,
    partial: bool,
}

#[derive(Serialize, Deserialize)]
struct Store {
    version: u32,
    workspaces: Vec<Workspace>,
}

#[derive(Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Edit {
    Rename {
        project_id: String,
        name: String,
    },
    Group {
        repository_ids: Vec<String>,
        name: String,
    },
    Ungroup {
        repository_id: String,
    },
}

struct Found {
    path: PathBuf,
    common: Option<PathBuf>,
    markers: Vec<String>,
}
struct Scan {
    found: Vec<Found>,
    warnings: Vec<String>,
    partial: bool,
}

fn id() -> String {
    uuid::Uuid::new_v4().to_string()
}
fn display(path: &Path) -> String {
    crate::project_cmd::strip_verbatim(path.to_path_buf())
        .to_string_lossy()
        .into_owned()
}
fn name(path: &Path) -> String {
    path.file_name()
        .map(|v| v.to_string_lossy().into_owned())
        .unwrap_or_else(|| display(path))
}

fn small_text(path: &Path, limit: u64) -> Result<String, String> {
    let metadata = fs::symlink_metadata(path).map_err(|e| format!("{}: {e}", path.display()))?;
    if !metadata.is_file() || metadata.file_type().is_symlink() {
        return Err(format!("Keine reguläre Metadatei: {}", path.display()));
    }
    let mut text = String::new();
    fs::File::open(path)
        .map_err(|e| format!("{}: {e}", path.display()))?
        .take(limit + 1)
        .read_to_string(&mut text)
        .map_err(|e| e.to_string())?;
    if text.len() as u64 > limit {
        return Err(format!("Datei zu groß: {}", path.display()));
    }
    Ok(text)
}

fn common_dir(root: &Path) -> Result<Option<PathBuf>, String> {
    let marker = root.join(".git");
    let metadata = match fs::symlink_metadata(&marker) {
        Ok(value) => value,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(format!("{}: {e}", marker.display())),
    };
    if metadata.file_type().is_symlink() {
        return Err(format!("Git-Symlink übersprungen: {}", marker.display()));
    }
    let git = if metadata.is_dir() {
        marker
    } else if metadata.is_file() {
        let text = small_text(&marker, 4096)?;
        let target = text
            .trim()
            .strip_prefix("gitdir: ")
            .filter(|value| !value.is_empty())
            .ok_or_else(|| format!("Ungültiger Git-Verweis: {}", marker.display()))?;
        root.join(target)
    } else {
        return Err(format!(
            "Keine reguläre Git-Metadatei: {}",
            marker.display()
        ));
    };
    let git = git
        .canonicalize()
        .map_err(|e| format!("{}: {e}", git.display()))?;
    if !git.join("HEAD").is_file() {
        return Err(format!("Git HEAD fehlt: {}", git.display()));
    }
    let common = if git.join("commondir").exists() {
        let relative = small_text(&git.join("commondir"), 4096)?;
        if relative.trim().is_empty() {
            return Err("Leerer Git-commondir-Verweis".into());
        }
        git.join(relative.trim())
            .canonicalize()
            .map_err(|e| e.to_string())?
    } else {
        git
    };
    if !common.join("objects").is_dir() || !common.join("refs").is_dir() {
        return Err(format!(
            "Ungültiges Git-Common-Verzeichnis: {}",
            common.display()
        ));
    }
    Ok(Some(common))
}

fn markers(root: &Path) -> Vec<String> {
    [
        "speccify.yaml",
        ".agent/agent.md",
        "AGENTS.md",
        "CLAUDE.md",
        "openspec/config.yaml",
        ".specify",
    ]
    .iter()
    .filter(|marker| root.join(marker).exists())
    .map(|marker| (*marker).to_owned())
    .collect()
}

fn scan(root: &Path, max_entries: usize, max_depth: usize) -> Scan {
    let mut result = Scan {
        found: vec![],
        warnings: vec![],
        partial: false,
    };
    let mut queue = VecDeque::from([(root.to_path_buf(), 0)]);
    let started = Instant::now();
    let mut entries_seen = 0;
    let mut dirs_seen = 0;
    while let Some((dir, depth)) = queue.pop_front() {
        if !fs::symlink_metadata(&dir)
            .is_ok_and(|metadata| metadata.is_dir() && !metadata.file_type().is_symlink())
        {
            result.partial = true;
            result.warnings.push(format!(
                "Verzeichnis inzwischen verändert: {}",
                dir.display()
            ));
            continue;
        }
        dirs_seen += 1;
        if dirs_seen > 2000 || started.elapsed() > Duration::from_secs(3) {
            result.partial = true;
            result.warnings.push(
                "Suchbudget erreicht; Ergebnis unvollständig. Unterordner separat öffnen.".into(),
            );
            break;
        }
        let found_markers = markers(&dir);
        match common_dir(&dir) {
            Ok(Some(common)) => result.found.push(Found {
                path: dir.clone(),
                common: Some(common),
                markers: found_markers,
            }),
            Ok(None)
                if found_markers.iter().any(|value| {
                    value == "speccify.yaml"
                        || value == ".agent/agent.md"
                        || value.starts_with("openspec/")
                        || value == ".specify"
                }) =>
            {
                result.found.push(Found {
                    path: dir.clone(),
                    common: None,
                    markers: found_markers,
                });
            }
            Ok(None) => (),
            Err(error) => result.warnings.push(error),
        }
        let entries = match fs::read_dir(&dir) {
            Ok(entries) => entries,
            Err(e) => {
                result.partial = true;
                result.warnings.push(format!("{}: {e}", dir.display()));
                continue;
            }
        };
        let mut children = vec![];
        for entry in entries {
            entries_seen += 1;
            if entries_seen > max_entries {
                result.partial = true;
                result
                    .warnings
                    .push("Dateianzahl-Limit erreicht; Ergebnis unvollständig.".into());
                queue.clear();
                break;
            }
            let entry = match entry {
                Ok(entry) => entry,
                Err(e) => {
                    result.partial = true;
                    result.warnings.push(e.to_string());
                    continue;
                }
            };
            if EXCLUDED.contains(&entry.file_name().to_string_lossy().as_ref()) {
                continue;
            }
            let kind = match entry.file_type() {
                Ok(kind) => kind,
                Err(e) => {
                    result.partial = true;
                    result.warnings.push(e.to_string());
                    continue;
                }
            };
            if kind.is_symlink() {
                continue;
            }
            if kind.is_dir() {
                if depth >= max_depth {
                    result.partial = true;
                } else {
                    children.push(entry.path());
                }
            }
        }
        if entries_seen > max_entries {
            break;
        }
        children.sort();
        queue.extend(children.into_iter().map(|path| (path, depth + 1)));
    }
    if result.partial && result.warnings.is_empty() {
        result
            .warnings
            .push("Maximale Suchtiefe erreicht; Unterordner separat öffnen.".into());
    }
    if result.found.is_empty() {
        result.found.push(Found {
            path: root.to_path_buf(),
            common: None,
            markers: markers(root),
        });
    }
    result
}

fn store_path() -> Result<PathBuf, String> {
    Ok(crate::settings::home_dir()?.join(".speccify/workspaces.json"))
}

fn load(path: &Path) -> Result<Store, String> {
    match fs::symlink_metadata(path) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            return Ok(Store {
                version: 1,
                workspaces: vec![],
            })
        }
        Err(e) => return Err(e.to_string()),
        Ok(_) => (),
    }
    let store: Store = serde_json::from_str(&small_text(path, 4 * 1024 * 1024)?)
        .map_err(|e| format!("Workspace-Datei beschädigt; unverändert erhalten: {e}"))?;
    if store.version != 1 {
        return Err(format!("Unbekanntes Workspace-Format {}", store.version));
    }
    for workspace in &store.workspaces {
        validate(workspace)?;
    }
    Ok(store)
}

fn save(path: &Path, store: &Store) -> Result<(), String> {
    let parent = path
        .parent()
        .ok_or("Workspace-Speicher hat keinen Ordner")?;
    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let mut temporary = tempfile::NamedTempFile::new_in(parent).map_err(|e| e.to_string())?;
    let json = serde_json::to_vec_pretty(store).map_err(|e| e.to_string())?;
    if json.len() > 4 * 1024 * 1024 {
        return Err("Workspace-Speicherlimit erreicht".into());
    }
    temporary.write_all(&json).map_err(|e| e.to_string())?;
    temporary.as_file().sync_all().map_err(|e| e.to_string())?;
    temporary.persist(path).map_err(|e| e.to_string())?;
    Ok(())
}

fn validate(workspace: &Workspace) -> Result<(), String> {
    let repo_ids: HashSet<_> = workspace.repositories.iter().map(|repo| &repo.id).collect();
    let project_ids: HashSet<_> = workspace
        .projects
        .iter()
        .map(|project| &project.id)
        .collect();
    let assigned: Vec<_> = workspace
        .projects
        .iter()
        .flat_map(|project| &project.repository_ids)
        .collect();
    if repo_ids.len() != workspace.repositories.len()
        || project_ids.len() != workspace.projects.len()
        || assigned.len() != repo_ids.len()
        || assigned.iter().copied().collect::<HashSet<_>>() != repo_ids
        || workspace
            .repositories
            .iter()
            .any(|repo| !project_ids.contains(&repo.default_project_id))
    {
        return Err("Ungültige Workspace-Zuordnungen; Datei bleibt unverändert.".into());
    }
    Ok(())
}

fn resolve_worktree(workspace: &Workspace, worktree_id: &str) -> Result<String, String> {
    let (repo, tree) = workspace
        .repositories
        .iter()
        .find_map(|repo| {
            repo.worktrees
                .iter()
                .find(|tree| tree.id == worktree_id)
                .map(|tree| (repo, tree))
        })
        .ok_or("Worktree nicht gefunden")?;
    let root = crate::project_cmd::resolve_project_root(&tree.path)?;
    if display(&root) != tree.path || !root.starts_with(Path::new(&workspace.root)) {
        return Err("Worktree-Pfad hat sich geändert. Workspace erneut erkennen.".into());
    }
    let common = common_dir(&root)?.as_deref().map(display);
    if common != repo.common_dir {
        return Err("Git-Zuordnung hat sich geändert. Workspace erneut erkennen.".into());
    }
    Ok(display(&root))
}

fn merge(store: &mut Store, root: &Path, scan: Scan) -> Workspace {
    let root_text = display(root);
    let index = store
        .workspaces
        .iter()
        .position(|workspace| workspace.root == root_text)
        .unwrap_or_else(|| {
            store.workspaces.push(Workspace {
                id: id(),
                name: name(root),
                root: root_text.clone(),
                revision: 0,
                projects: vec![],
                repositories: vec![],
                warnings: vec![],
                partial: false,
            });
            store.workspaces.len() - 1
        });
    let workspace = &mut store.workspaces[index];
    for repo in &mut workspace.repositories {
        for tree in &mut repo.worktrees {
            tree.available = Path::new(&tree.path).is_dir();
        }
    }
    workspace.warnings = scan.warnings;
    workspace.partial = scan.partial;
    for found in scan.found {
        let common = found.common.as_deref().map(display);
        let path = display(&found.path);
        if let Some(previous) = workspace.repositories.iter_mut().find(|repo| {
            repo.common_dir.is_some()
                && repo.common_dir != common
                && repo.worktrees.iter().any(|tree| tree.path == path)
        }) {
            for tree in &mut previous.worktrees {
                if tree.path == path {
                    tree.available = false;
                }
            }
            workspace.warnings.push(format!(
                "Git-Zuordnung geändert: {path}. Bestehende Bindung nicht automatisch ersetzt."
            ));
            continue;
        }
        let repo_index = workspace
            .repositories
            .iter()
            .position(|repo| match &common {
                Some(value) => repo.common_dir.as_ref() == Some(value),
                None => {
                    repo.common_dir.is_none() && repo.worktrees.iter().any(|tree| tree.path == path)
                }
            })
            .or_else(|| {
                workspace.repositories.iter().position(|repo| {
                    repo.common_dir.is_none()
                        && repo.worktrees.len() == 1
                        && repo.worktrees[0].path == path
                })
            })
            .unwrap_or_else(|| {
                let repo_id = id();
                let project_id = id();
                workspace.projects.push(Project {
                    id: project_id.clone(),
                    name: name(&found.path),
                    repository_ids: vec![repo_id.clone()],
                });
                workspace.repositories.push(Repository {
                    id: repo_id,
                    name: name(&found.path),
                    common_dir: common,
                    default_project_id: project_id,
                    worktrees: vec![],
                });
                workspace.repositories.len() - 1
            });
        let repo = &mut workspace.repositories[repo_index];
        if repo.common_dir.is_none() {
            repo.common_dir = found.common.as_deref().map(display);
        }
        if let Some(tree) = repo.worktrees.iter_mut().find(|tree| tree.path == path) {
            tree.available = true;
            tree.markers = found.markers;
        } else {
            repo.worktrees.push(Worktree {
                id: id(),
                relative_path: display(found.path.strip_prefix(root).unwrap_or(&found.path)),
                path,
                markers: found.markers,
                available: true,
            });
        }
    }
    workspace.revision += 1;
    workspace.clone()
}

fn checked_name(value: String) -> Result<String, String> {
    let value = value.trim();
    if value.is_empty() || value.chars().count() > 100 || value.chars().any(char::is_control) {
        return Err("Name muss 1–100 Zeichen ohne Steuerzeichen enthalten.".into());
    }
    Ok(value.to_owned())
}

fn edit(workspace: &mut Workspace, expected: u64, change: Edit) -> Result<(), String> {
    if workspace.revision != expected {
        return Err(
            "WORKSPACE_CHANGED: Zuordnung wurde geändert. Neu laden und erneut prüfen.".into(),
        );
    }
    match change {
        Edit::Rename { project_id, name } => {
            let name = checked_name(name)?;
            workspace
                .projects
                .iter_mut()
                .find(|project| project.id == project_id)
                .ok_or("Projekt nicht gefunden")?
                .name = name;
        }
        Edit::Group {
            repository_ids,
            name,
        } => {
            let name = checked_name(name)?;
            let ids: HashSet<_> = repository_ids.iter().collect();
            if ids.len() < 2
                || ids.len() != repository_ids.len()
                || repository_ids
                    .iter()
                    .any(|id| !workspace.repositories.iter().any(|repo| &repo.id == id))
            {
                return Err("Mindestens zwei unterschiedliche vorhandene Repos auswählen.".into());
            }
            for project in &mut workspace.projects {
                project.repository_ids.retain(|repo| !ids.contains(repo));
            }
            workspace.projects.push(Project {
                id: id(),
                name,
                repository_ids,
            });
        }
        Edit::Ungroup { repository_id } => {
            let target = workspace
                .repositories
                .iter()
                .find(|repo| repo.id == repository_id)
                .ok_or("Repo nicht gefunden")?
                .default_project_id
                .clone();
            for project in &mut workspace.projects {
                project.repository_ids.retain(|repo| repo != &repository_id);
            }
            workspace
                .projects
                .iter_mut()
                .find(|project| project.id == target)
                .ok_or("Ursprungsprojekt fehlt")?
                .repository_ids
                .push(repository_id);
        }
    }
    validate(workspace)?;
    workspace.revision += 1;
    Ok(())
}

#[tauri::command]
pub async fn workspace_list() -> Result<Vec<Workspace>, String> {
    tauri::async_runtime::spawn_blocking(|| {
        let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
        let mut store = load(&store_path()?)?;
        for workspace in &mut store.workspaces {
            for repo in &mut workspace.repositories {
                for tree in &mut repo.worktrees {
                    tree.available = Path::new(&tree.path).is_dir();
                }
            }
        }
        Ok(store.workspaces)
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn workspace_discover(path: String) -> Result<Workspace, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let root = crate::project_cmd::resolve_project_root(&path)?;
        let scan = scan(&root, 20000, 6);
        let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
        let path = store_path()?;
        let mut store = load(&path)?;
        let workspace = merge(&mut store, &root, scan);
        save(&path, &store)?;
        Ok(workspace)
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn workspace_edit(
    workspace_id: String,
    expected_revision: u64,
    change: Edit,
) -> Result<Workspace, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
        let path = store_path()?;
        let mut store = load(&path)?;
        let workspace = store
            .workspaces
            .iter_mut()
            .find(|workspace| workspace.id == workspace_id)
            .ok_or("Workspace nicht gefunden")?;
        edit(workspace, expected_revision, change)?;
        let result = workspace.clone();
        save(&path, &store)?;
        Ok(result)
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn workspace_open(
    app: tauri::AppHandle,
    state: tauri::State<'_, crate::project_cmd::ProjectWindows>,
    workspace_id: String,
    worktree_id: String,
) -> Result<String, String> {
    let path = tauri::async_runtime::spawn_blocking(move || {
        let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
        let store = load(&store_path()?)?;
        let workspace = store
            .workspaces
            .iter()
            .find(|workspace| workspace.id == workspace_id)
            .ok_or("Workspace nicht gefunden")?;
        resolve_worktree(workspace, &worktree_id)
    })
    .await
    .map_err(|e| e.to_string())??;
    crate::project_cmd::open_project_window(&app, &state, &path)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;

    fn git(root: &Path, args: &[&str]) {
        let result = Command::new("git")
            .arg("-C")
            .arg(root)
            .args(args)
            .env("GIT_CONFIG_NOSYSTEM", "1")
            .env(
                "GIT_CONFIG_GLOBAL",
                if cfg!(windows) { "NUL" } else { "/dev/null" },
            )
            .output()
            .unwrap();
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
    }
    fn repo(root: &Path) {
        fs::create_dir_all(root).unwrap();
        git(root, &["init", "-b", "main"]);
        git(
            root,
            &[
                "-c",
                "user.name=Demo",
                "-c",
                "user.email=demo@example.invalid",
                "commit",
                "--allow-empty",
                "-m",
                "initial",
            ],
        );
    }
    fn empty_store() -> Store {
        Store {
            version: 1,
            workspaces: vec![],
        }
    }

    #[test]
    fn recognizes_repos_nested_worktrees_and_ignores_dependencies_without_writing() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        let first = root.join("api");
        let second = root.join("web");
        let linked = root.join("api-feature");
        repo(&first);
        repo(&second);
        repo(&first.join("nested"));
        repo(&root.join("node_modules/hidden"));
        git(
            &first,
            &["worktree", "add", "-b", "feature", linked.to_str().unwrap()],
        );
        let index = fs::read(first.join(".git/index")).ok();
        let head = fs::read(first.join(".git/HEAD")).unwrap();
        let config = fs::read(first.join(".git/config")).unwrap();
        let scan = scan(&root, 20000, 6);
        assert!(!scan.partial);
        assert!(scan.warnings.is_empty());
        assert_eq!(scan.found.len(), 4);
        let mut store = empty_store();
        let workspace = merge(&mut store, &root, scan);
        assert_eq!(workspace.repositories.len(), 3);
        assert_eq!(workspace.projects.len(), 3);
        assert!(workspace
            .repositories
            .iter()
            .any(|repo| repo.worktrees.len() == 2));
        assert_eq!(fs::read(first.join(".git/index")).ok(), index);
        assert_eq!(fs::read(first.join(".git/HEAD")).unwrap(), head);
        assert_eq!(fs::read(first.join(".git/config")).unwrap(), config);
        assert!(!root.join(".agent").exists());
        for repo in &workspace.repositories {
            for tree in &repo.worktrees {
                assert_eq!(resolve_worktree(&workspace, &tree.id).unwrap(), tree.path);
            }
        }
    }

    #[test]
    fn grouping_rename_rescan_atomic_reload_and_ungroup_keep_identity() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        repo(&root.join("a"));
        repo(&root.join("b"));
        let mut store = empty_store();
        let initial = merge(&mut store, &root, scan(&root, 20000, 6));
        let ids: Vec<_> = initial
            .repositories
            .iter()
            .map(|repo| repo.id.clone())
            .collect();
        edit(
            &mut store.workspaces[0],
            1,
            Edit::Group {
                repository_ids: ids.clone(),
                name: "Portal".into(),
            },
        )
        .unwrap();
        let grouped = store.workspaces[0].projects.last().unwrap().id.clone();
        edit(
            &mut store.workspaces[0],
            2,
            Edit::Rename {
                project_id: grouped.clone(),
                name: "Customer Portal".into(),
            },
        )
        .unwrap();
        let again = merge(&mut store, &root, scan(&root, 20000, 6));
        assert_eq!(again.id, initial.id);
        assert_eq!(again.repositories[0].id, ids[0]);
        assert_eq!(
            again.repositories[0].worktrees[0].id,
            initial.repositories[0].worktrees[0].id
        );
        assert_eq!(again.projects.last().unwrap().name, "Customer Portal");
        let persistence = tempfile::tempdir().unwrap();
        let file = persistence.path().join("workspaces.json");
        save(&file, &store).unwrap();
        let mut restored = load(&file).unwrap();
        edit(
            &mut restored.workspaces[0],
            4,
            Edit::Ungroup {
                repository_id: ids[0].clone(),
            },
        )
        .unwrap();
        assert_eq!(
            restored.workspaces[0].projects[0].id,
            initial.projects[0].id
        );
        assert_eq!(
            restored.workspaces[0].projects[0].repository_ids,
            vec![ids[0].clone()]
        );
        assert_eq!(restored.workspaces[0].projects.last().unwrap().id, grouped);
        save(&file, &restored).unwrap();
        assert_eq!(load(&file).unwrap().workspaces[0].revision, 5);
    }

    #[test]
    fn stale_or_invalid_edits_and_corrupt_store_are_not_silently_replaced() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        let mut store = empty_store();
        let mut workspace = merge(&mut store, &root, scan(&root, 20000, 6));
        let before = serde_json::to_string(&workspace).unwrap();
        assert!(edit(
            &mut workspace,
            0,
            Edit::Rename {
                project_id: "missing".into(),
                name: "x".into()
            }
        )
        .unwrap_err()
        .contains("WORKSPACE_CHANGED"));
        assert!(edit(
            &mut workspace,
            1,
            Edit::Group {
                repository_ids: vec!["missing".into()],
                name: "x".into()
            }
        )
        .is_err());
        assert_eq!(serde_json::to_string(&workspace).unwrap(), before);
        let file = root.join("workspaces.json");
        fs::write(&file, "{broken").unwrap();
        assert!(load(&file).is_err());
        assert_eq!(fs::read_to_string(&file).unwrap(), "{broken");
        fs::write(&file, r#"{"version":99,"workspaces":[]}"#).unwrap();
        assert!(load(&file).is_err());
    }

    #[test]
    fn plain_projects_markers_limits_and_missing_paths_stay_explicit() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        let mut store = empty_store();
        let first = merge(&mut store, &root, scan(&root, 20000, 6));
        assert!(first.repositories[0].common_dir.is_none());
        assert!(!root.join(".git").exists());
        let child = root.join("deep/project");
        fs::create_dir_all(&child).unwrap();
        fs::write(child.join("speccify.yaml"), "{}\n").unwrap();
        let result = scan(&root, 20000, 6);
        assert_eq!(result.found.len(), 1);
        assert_eq!(result.found[0].path, child);
        assert!(scan(&root, 0, 6).partial);
        assert!(scan(&root, 20000, 0).partial);
        let current = merge(&mut store, &root, scan(&root, 20000, 6));
        let tree = current
            .repositories
            .iter()
            .flat_map(|repo| &repo.worktrees)
            .find(|tree| tree.path == display(&child))
            .unwrap()
            .id
            .clone();
        fs::rename(&child, root.join("moved")).unwrap();
        let current = merge(&mut store, &root, scan(&root, 0, 6));
        assert!(current
            .repositories
            .iter()
            .flat_map(|repo| &repo.worktrees)
            .any(|entry| entry.id == tree && !entry.available));
        assert!(resolve_worktree(&current, &tree).is_err());
    }

    #[test]
    fn external_git_metadata_is_identified_but_external_trees_are_not_enumerated() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        let source = root.join("source");
        let selected = root.join("selected");
        repo(&source);
        git(
            &source,
            &[
                "worktree",
                "add",
                "-b",
                "linked",
                selected.to_str().unwrap(),
            ],
        );
        let result = scan(&selected, 20000, 6);
        assert_eq!(result.found.len(), 1);
        assert_eq!(result.found[0].path, selected);
        assert_eq!(result.found[0].common, Some(source.join(".git")));
        let pointer = root.join("submodule");
        fs::create_dir(&pointer).unwrap();
        fs::write(pointer.join(".git"), "gitdir: ../source/.git\n").unwrap();
        assert_eq!(common_dir(&pointer).unwrap(), Some(source.join(".git")));
        fs::write(pointer.join(".git"), "invalid").unwrap();
        assert!(common_dir(&pointer).is_err());
        fs::write(pointer.join(".git"), "x".repeat(4097)).unwrap();
        assert!(common_dir(&pointer).is_err());
    }

    #[cfg(unix)]
    #[test]
    fn symlink_loops_and_metadata_symlinks_are_skipped() {
        use std::os::unix::fs::symlink;
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        repo(&root.join("a"));
        symlink(&root, root.join("loop")).unwrap();
        let bad = root.join("bad");
        fs::create_dir(&bad).unwrap();
        symlink(root.join("a/.git"), bad.join(".git")).unwrap();
        let result = scan(&root, 20000, 6);
        assert_eq!(result.found.len(), 1);
        assert!(!result.warnings.is_empty());
        let alias = root.join("state.json");
        symlink(root.join("a/.git/HEAD"), &alias).unwrap();
        assert!(load(&alias).is_err());
    }
}
