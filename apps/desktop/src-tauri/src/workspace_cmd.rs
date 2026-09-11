//! Local workspace discovery and metadata. Contract: docs/workspaces.md.
use serde::{Deserialize, Serialize};
use std::collections::{HashSet, VecDeque};
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::Manager;

static STORE_LOCK: Mutex<()> = Mutex::new(());
const DISCOVERY_MAX_DEPTH: usize = 16;
const DISCOVERY_MAX_ENTRIES: usize = 20_000;
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
    #[serde(default)]
    window_open: bool,
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
    let mut depth_cutoffs = vec![];
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
        let relative_dir = if dir == root {
            ".".to_owned()
        } else {
            display(dir.strip_prefix(root).unwrap_or(&dir))
        };
        dirs_seen += 1;
        if dirs_seen > 2000 || started.elapsed() > Duration::from_secs(3) {
            result.partial = true;
            result.warnings.push(format!(
                "Suchbudget erreicht bei {}. Dieser und weitere ausstehende Ordner wurden nicht durchsucht.",
                relative_dir
            ));
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
                result.warnings.push(format!(
                    "Dateianzahl-Limit erreicht bei {}. Dieser und weitere ausstehende Ordner wurden nicht vollständig durchsucht.",
                    relative_dir
                ));
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
                    depth_cutoffs.push(entry.path());
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
    if !depth_cutoffs.is_empty() {
        depth_cutoffs.sort();
        let total = depth_cutoffs.len();
        let paths = depth_cutoffs
            .iter()
            .take(8)
            .map(|path| display(path.strip_prefix(root).unwrap_or(path)))
            .collect::<Vec<_>>()
            .join(", ");
        let more = if total > 8 {
            format!(" (und {} weitere)", total - 8)
        } else {
            String::new()
        };
        result.warnings.push(format!(
            "Suchtiefe von {max_depth} Ebenen erreicht. Nicht durchsucht: {paths}{more}. Diese Unterordner bei Bedarf separat öffnen."
        ));
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
                window_open: false,
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
        let scan = scan(&root, DISCOVERY_MAX_ENTRIES, DISCOVERY_MAX_DEPTH);
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

async fn workspace_snapshot(workspace_id: String) -> Result<Workspace, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
        let store = load(&store_path()?)?;
        let mut workspace = store
            .workspaces
            .into_iter()
            .find(|entry| entry.id == workspace_id)
            .ok_or("Workspace nicht gefunden")?;
        for repo in &mut workspace.repositories {
            for tree in &mut repo.worktrees {
                tree.available = Path::new(&tree.path).is_dir();
            }
        }
        Ok(workspace)
    })
    .await
    .map_err(|e| e.to_string())?
}

fn remember_workspace_window(workspace_id: &str, open: bool) -> Result<(), String> {
    let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
    let path = store_path()?;
    let mut store = load(&path)?;
    let workspace = store
        .workspaces
        .iter_mut()
        .find(|entry| entry.id == workspace_id)
        .ok_or("Workspace nicht gefunden")?;
    workspace.window_open = open;
    save(&path, &store)
}

#[tauri::command]
pub async fn workspace_window_current(window: tauri::WebviewWindow) -> Result<Workspace, String> {
    let id = window
        .label()
        .strip_prefix("workspace-")
        .ok_or("Kein Workspace-Fenster")?;
    workspace_snapshot(id.to_owned()).await
}

#[tauri::command]
pub async fn workspace_resolve_target(
    workspace_id: String,
    worktree_id: String,
) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
        let store = load(&store_path()?)?;
        let workspace = store
            .workspaces
            .iter()
            .find(|entry| entry.id == workspace_id)
            .ok_or("Workspace nicht gefunden")?;
        resolve_worktree(workspace, &worktree_id)
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn workspace_window_open(
    app: tauri::AppHandle,
    workspace_id: String,
) -> Result<(), String> {
    let workspace = workspace_snapshot(workspace_id.clone()).await?;
    let label = format!("workspace-{}", workspace.id);
    if let Some(window) = app.get_webview_window(&label) {
        window.set_focus().map_err(|e| e.to_string())?;
        return Ok(());
    }
    let builder =
        tauri::WebviewWindowBuilder::new(&app, &label, tauri::WebviewUrl::App("index.html".into()))
            .title(format!("{} · Workspace — Speccify", workspace.name))
            .inner_size(1500.0, 940.0)
            .min_inner_size(1000.0, 650.0);
    #[cfg(target_os = "macos")]
    let builder = builder
        .title_bar_style(tauri::TitleBarStyle::Overlay)
        .hidden_title(true);
    let window = builder.build().map_err(|e| e.to_string())?;
    let close_id = workspace.id.clone();
    window.on_window_event(move |event| {
        if matches!(event, tauri::WindowEvent::CloseRequested { .. }) {
            let id = close_id.clone();
            tauri::async_runtime::spawn_blocking(move || {
                if let Err(error) = remember_workspace_window(&id, false) {
                    eprintln!("Workspace-Fenster: {error}");
                }
            });
        }
    });
    tauri::async_runtime::spawn_blocking(move || remember_workspace_window(&workspace_id, true))
        .await
        .map_err(|e| e.to_string())??;
    Ok(())
}

pub fn restore_workspace_windows(app: &tauri::AppHandle) {
    let app = app.clone();
    tauri::async_runtime::spawn(async move {
        match workspace_list().await {
            Ok(workspaces) => {
                for workspace in workspaces.into_iter().filter(|entry| entry.window_open) {
                    if let Err(error) = workspace_window_open(app.clone(), workspace.id).await {
                        eprintln!("Workspace-Fenster nicht wiederhergestellt: {error}");
                    }
                }
            }
            Err(error) => eprintln!("Workspace-Fensterliste: {error}"),
        }
    });
}

#[derive(Serialize)]
struct WorkspaceSpec {
    key: String,
    project_id: String,
    project_name: String,
    repository_id: String,
    repository_name: String,
    worktree_id: String,
    worktree_path: String,
    worktree_label: String,
    spec: crate::project_cmd::TicketEntry,
}

#[derive(Serialize)]
pub struct WorkspaceBoard {
    workspace_id: String,
    revision: u64,
    captured_at: u64,
    specs: Vec<WorkspaceSpec>,
    warnings: Vec<String>,
    partial: bool,
}

// This reader intentionally refuses linked knowledge directories. Merely resolving
// the final SPEC.md would allow enumeration outside the selected worktree first.
fn board_directory(path: &Path) -> Result<bool, String> {
    match fs::symlink_metadata(path) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(e) => Err(format!("{}: {e}", display(path))),
        Ok(meta) if meta.is_dir() && !meta.file_type().is_symlink() => Ok(true),
        Ok(_) => Err(format!("Kein regulärer Wissensordner: {}", display(path))),
    }
}

fn read_workspace_board(workspace: &Workspace, max_entries: usize) -> WorkspaceBoard {
    let mut result = WorkspaceBoard {
        workspace_id: workspace.id.clone(),
        revision: workspace.revision,
        captured_at: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64,
        specs: vec![],
        warnings: vec![],
        partial: false,
    };
    let started = Instant::now();
    let mut entries_seen = 0;
    let mut trees_seen = 0;
    let mut bytes_read = 0;
    'repos: for repo in &workspace.repositories {
        let Some(project) = workspace
            .projects
            .iter()
            .find(|project| project.repository_ids.contains(&repo.id))
        else {
            continue;
        };
        'trees: for tree in &repo.worktrees {
            trees_seen += 1;
            if trees_seen > 100 || started.elapsed() > Duration::from_secs(3) {
                result
                    .warnings
                    .push("Board-Lesebudget erreicht; Ergebnis unvollständig.".into());
                break 'repos;
            }
            let root = match resolve_worktree(workspace, &tree.id) {
                Ok(root) => PathBuf::from(root),
                Err(e) => {
                    result.warnings.push(format!("{}: {e}", tree.path));
                    continue;
                }
            };
            let base = root.join(crate::project_cmd::SPECS_DIR);
            for directory in [root.join(".agent"), base.clone()] {
                match board_directory(&directory) {
                    Ok(true) => (),
                    Ok(false) => continue 'trees,
                    Err(e) => {
                        result.warnings.push(e);
                        continue 'trees;
                    }
                }
            }
            for directory in [base.clone(), base.join("archive")] {
                match board_directory(&directory) {
                    Ok(true) => (),
                    Ok(false) => continue,
                    Err(e) => {
                        result.warnings.push(e);
                        continue;
                    }
                }
                let entries = match fs::read_dir(&directory) {
                    Ok(entries) => entries,
                    Err(e) => {
                        result
                            .warnings
                            .push(format!("{}: {e}", display(&directory)));
                        continue;
                    }
                };
                for entry in entries {
                    entries_seen += 1;
                    if entries_seen > max_entries
                        || bytes_read >= 8 * 1024 * 1024
                        || started.elapsed() > Duration::from_secs(3)
                    {
                        result
                            .warnings
                            .push("Board-Lesebudget erreicht; Ergebnis unvollständig.".into());
                        break 'repos;
                    }
                    let entry = match entry {
                        Ok(entry) => entry,
                        Err(e) => {
                            result.warnings.push(e.to_string());
                            continue;
                        }
                    };
                    let dir = entry.path();
                    if dir == base.join("archive") {
                        continue;
                    }
                    let kind = match entry.file_type() {
                        Ok(kind) => kind,
                        Err(e) => {
                            result.warnings.push(e.to_string());
                            continue;
                        }
                    };
                    if kind.is_symlink() {
                        result
                            .warnings
                            .push(format!("Verlinkte Spec ausgelassen: {}", display(&dir)));
                        continue;
                    }
                    if !kind.is_dir() {
                        continue;
                    }
                    let path = dir.join("SPEC.md");
                    // Recheck directory identity before accessing its file.
                    if !board_directory(&dir).unwrap_or(false) {
                        result
                            .warnings
                            .push(format!("Spec-Ordner verändert: {}", display(&dir)));
                        continue;
                    }
                    match fs::symlink_metadata(&path) {
                        Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
                        _ => (),
                    }
                    let text = match small_text(&path, 256 * 1024) {
                        Ok(text) => text,
                        Err(e) => {
                            result.warnings.push(e);
                            continue;
                        }
                    };
                    bytes_read += text.len();
                    let Some(spec) = crate::project_cmd::spec_from_text(&root, &path, &text) else {
                        result
                            .warnings
                            .push(format!("Ungültiges Spec-Frontmatter: {}", display(&path)));
                        continue;
                    };
                    let relative = path
                        .strip_prefix(&root)
                        .unwrap()
                        .to_string_lossy()
                        .replace('\\', "/");
                    result.specs.push(WorkspaceSpec {
                        key: serde_json::to_string(&[&workspace.id, &repo.id, &tree.id, &relative])
                            .unwrap(),
                        project_id: project.id.clone(),
                        project_name: project.name.clone(),
                        repository_id: repo.id.clone(),
                        repository_name: repo.name.clone(),
                        worktree_id: tree.id.clone(),
                        worktree_path: tree.path.clone(),
                        worktree_label: tree.relative_path.clone(),
                        spec,
                    });
                }
            }
        }
    }
    result.specs.sort_by(|a, b| a.key.cmp(&b.key));
    result.partial = !result.warnings.is_empty();
    result
}

#[tauri::command]
pub async fn workspace_board(workspace_id: String) -> Result<WorkspaceBoard, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let workspace = {
            let _guard = STORE_LOCK.lock().map_err(|e| e.to_string())?;
            let store = load(&store_path()?)?;
            store
                .workspaces
                .into_iter()
                .find(|workspace| workspace.id == workspace_id)
                .ok_or("Workspace nicht gefunden")?
        };
        Ok(read_workspace_board(&workspace, 5000))
    })
    .await
    .map_err(|e| e.to_string())?
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

    fn board_fixture_spec(root: &Path, relative: &str, station: &str) -> PathBuf {
        let path = root.join(relative);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(&path, format!("---\nstation: {station}\nready: true\nneeds_human: true\n---\n# Shared title\n\n- [x] Tested\n- [ ] Review\n")).unwrap();
        path
    }

    #[test]
    fn workspace_board_keeps_colliding_worktrees_and_group_identity_separate() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        let api = root.join("api");
        let web = root.join("web");
        let feature = root.join("api-feature");
        repo(&api);
        repo(&web);
        let file = ".agent/specs/001-shared/SPEC.md";
        board_fixture_spec(&api, file, "Backlog");
        git(&api, &["add", "."]);
        git(
            &api,
            &[
                "-c",
                "user.name=Demo",
                "-c",
                "user.email=demo@example.invalid",
                "commit",
                "-m",
                "spec",
            ],
        );
        git(
            &api,
            &[
                "worktree",
                "add",
                "-b",
                "feature",
                feature.to_str().unwrap(),
            ],
        );
        board_fixture_spec(&feature, file, "Doing");
        board_fixture_spec(&web, file, "Done");
        let index_before = fs::read(api.join(".git/index")).unwrap();
        let spec_before = fs::read(api.join(file)).unwrap();
        let mut workspace = merge(&mut empty_store(), &root, scan(&root, 20000, 6));
        let board = read_workspace_board(&workspace, 5000);
        assert!(!board.partial, "{:?}", board.warnings);
        assert_eq!(board.specs.len(), 3);
        assert_eq!(
            board
                .specs
                .iter()
                .map(|entry| &entry.key)
                .collect::<HashSet<_>>()
                .len(),
            3
        );
        for entry in &board.specs {
            let local =
                crate::project_cmd::read_project_board(entry.worktree_path.clone()).unwrap();
            assert_eq!(
                serde_json::to_value(&entry.spec).unwrap(),
                serde_json::to_value(&local[0]).unwrap()
            );
            assert_eq!(
                resolve_worktree(&workspace, &entry.worktree_id).unwrap(),
                entry.worktree_path
            );
        }
        let keys: Vec<_> = board.specs.iter().map(|entry| entry.key.clone()).collect();
        let repository_ids = workspace
            .repositories
            .iter()
            .map(|repo| repo.id.clone())
            .collect();
        edit(
            &mut workspace,
            1,
            Edit::Group {
                repository_ids,
                name: "Suite".into(),
            },
        )
        .unwrap();
        let grouped = read_workspace_board(&workspace, 5000);
        assert_eq!(
            grouped
                .specs
                .iter()
                .map(|entry| entry.key.clone())
                .collect::<Vec<_>>(),
            keys
        );
        assert!(grouped
            .specs
            .iter()
            .all(|entry| entry.project_name == "Suite"));
        assert_eq!(fs::read(api.join(".git/index")).unwrap(), index_before);
        assert_eq!(fs::read(api.join(file)).unwrap(), spec_before);
        board_fixture_spec(&feature, file, "Review");
        let updated = read_workspace_board(&workspace, 5000);
        let item = updated
            .specs
            .iter()
            .find(|entry| entry.worktree_path == display(&feature))
            .unwrap();
        assert_eq!(
            serde_json::to_value(&item.spec).unwrap()["station"],
            "Review"
        );
    }

    #[test]
    fn workspace_board_reports_limits_invalid_missing_and_historical_sources() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        let good = board_fixture_spec(&root, ".agent/specs/001-shared/SPEC.md", "Doing");
        board_fixture_spec(
            &root,
            ".agent/specs/archive/2026-09-10-001-shared/SPEC.md",
            "In Progress",
        );
        let broken = board_fixture_spec(&root, ".agent/specs/002-broken/SPEC.md", "Backlog");
        fs::write(&broken, "no frontmatter").unwrap();
        let huge = board_fixture_spec(&root, ".agent/specs/003-huge/SPEC.md", "Backlog");
        fs::write(&huge, vec![b'x'; 256 * 1024 + 1]).unwrap();
        let workspace = merge(&mut empty_store(), &root, scan(&root, 20000, 6));
        let board = read_workspace_board(&workspace, 5000);
        assert_eq!(board.specs.len(), 2);
        assert!(board.partial);
        assert_eq!(board.warnings.len(), 2);
        assert_ne!(board.specs[0].key, board.specs[1].key);
        assert!(read_workspace_board(&workspace, 0).partial);
        assert!(good.exists());
        let mut missing = workspace.clone();
        missing.repositories[0].worktrees[0].path = display(&root.join("missing"));
        let board = read_workspace_board(&missing, 5000);
        assert!(board.partial);
        assert!(board.specs.is_empty());
    }

    #[cfg(unix)]
    #[test]
    fn workspace_board_rejects_linked_knowledge_and_keeps_other_worktrees() {
        use std::os::unix::fs::symlink;
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        let api = root.join("api");
        let linked = root.join("linked");
        repo(&api);
        git(
            &api,
            &["worktree", "add", "-b", "feature", linked.to_str().unwrap()],
        );
        board_fixture_spec(&linked, ".agent/specs/001-shared/SPEC.md", "Doing");
        let workspace = merge(&mut empty_store(), &root, scan(&root, 20000, 6));
        // Missing knowledge in the first tree must not skip the second tree.
        assert_eq!(read_workspace_board(&workspace, 5000).specs.len(), 1);
        let outside = tempfile::tempdir().unwrap();
        let secret = board_fixture_spec(outside.path(), ".agent/specs/001-secret/SPEC.md", "Done");
        symlink(outside.path().join(".agent"), api.join(".agent")).unwrap();
        symlink(secret, linked.join(".agent/specs/001-shared/linked.md")).unwrap();
        symlink(
            outside.path().join(".agent/specs/001-secret"),
            linked.join(".agent/specs/002-linked"),
        )
        .unwrap();
        let file = board_fixture_spec(&linked, ".agent/specs/003-file-link/SPEC.md", "Backlog");
        fs::remove_file(&file).unwrap();
        symlink(
            outside.path().join(".agent/specs/001-secret/SPEC.md"),
            &file,
        )
        .unwrap();
        let board = read_workspace_board(&workspace, 5000);
        assert_eq!(board.specs.len(), 1);
        assert!(board.partial);
        assert_eq!(board.warnings.len(), 3);
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
    #[ignore = "requires SPECCIFY_DISCOVERY_SMOKE_ROOT; reads a real local workspace"]
    fn discovery_local_workspace_smoke() {
        let path = std::env::var("SPECCIFY_DISCOVERY_SMOKE_ROOT")
            .expect("set SPECCIFY_DISCOVERY_SMOKE_ROOT explicitly");
        let root = crate::project_cmd::resolve_project_root(&path).unwrap();
        let result = scan(&root, DISCOVERY_MAX_ENTRIES, DISCOVERY_MAX_DEPTH);
        assert!(!result.partial, "{:?}", result.warnings);
        assert!(result.warnings.is_empty(), "{:?}", result.warnings);
        for found in &result.found {
            println!(
                "Found: {} (Git: {})",
                display(found.path.strip_prefix(&root).unwrap()),
                found.common.is_some()
            );
        }
        println!(
            "Complete: {} discovered roots, no warnings; no store or project writes",
            result.found.len()
        );
    }

    #[test]
    fn workspace_window_preference_migrates_and_survives_rescan_without_changing_bindings() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        let mut store = empty_store();
        let workspace = merge(&mut store, &root, scan(&root, 20000, 6));
        assert!(!workspace.window_open);
        let mut old_format = serde_json::to_value(&workspace).unwrap();
        old_format.as_object_mut().unwrap().remove("window_open");
        assert!(
            !serde_json::from_value::<Workspace>(old_format)
                .unwrap()
                .window_open
        );
        store.workspaces[0].window_open = true;
        let next = merge(&mut store, &root, scan(&root, 20000, 6));
        assert!(next.window_open);
        assert_eq!(next.id, workspace.id);
        assert_eq!(
            next.repositories[0].worktrees[0].id,
            workspace.repositories[0].worktrees[0].id
        );
        let path = root.join("store.json");
        save(&path, &store).unwrap();
        assert!(load(&path).unwrap().workspaces[0].window_open);
    }

    #[test]
    fn discovery_default_handles_deep_sources_and_preserves_rescan_identity() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        for name in ["app", "infra", "portal"] {
            repo(&root.join(name));
        }
        for path in [
            "app/frontend/src/app/shared/ui/icons",
            "infra/keycloak/provider/src/main/java/com/example/server/features",
            "portal/docs/migration/originals/date/docs/migration/originals/date/specs",
        ] {
            fs::create_dir_all(root.join(path)).unwrap();
        }
        let mut store = empty_store();
        let old = merge(&mut store, &root, scan(&root, DISCOVERY_MAX_ENTRIES, 6));
        assert!(old.partial);
        assert!(!old.warnings.is_empty());
        let ids = old
            .repositories
            .iter()
            .map(|repo| repo.id.clone())
            .collect();
        let grouped = store.workspaces.first_mut().unwrap();
        edit(
            grouped,
            old.revision,
            Edit::Group {
                repository_ids: ids,
                name: "Pilot".into(),
            },
        )
        .unwrap();
        let before = serde_json::to_value(&store.workspaces[0]).unwrap();
        let result = scan(&root, DISCOVERY_MAX_ENTRIES, DISCOVERY_MAX_DEPTH);
        assert!(!result.partial);
        assert!(result.warnings.is_empty());
        assert_eq!(result.found.len(), 3);
        let current = merge(&mut store, &root, result);
        assert!(!current.partial);
        assert!(current.warnings.is_empty());
        let after = serde_json::to_value(&current).unwrap();
        for key in ["id", "projects", "repositories"] {
            assert_eq!(before[key], after[key], "rescan changed {key}");
        }
        let nested = root.join("app/frontend/src/app/shared/ui/plugins/nested");
        repo(&nested);
        let result = scan(&root, DISCOVERY_MAX_ENTRIES, DISCOVERY_MAX_DEPTH);
        assert!(!result.partial);
        assert!(result.found.iter().any(|found| found.path == nested));
    }

    #[test]
    fn discovery_real_depth_limits_name_skipped_paths_with_bounded_examples() {
        let fixture = tempfile::tempdir().unwrap();
        let root = fixture.path().canonicalize().unwrap();
        let boundary = (0..DISCOVERY_MAX_DEPTH).fold(root.clone(), |path, _| path.join("level"));
        fs::create_dir_all(&boundary).unwrap();
        fs::write(boundary.join("speccify.yaml"), "{}\n").unwrap();
        let complete = scan(&root, DISCOVERY_MAX_ENTRIES, DISCOVERY_MAX_DEPTH);
        assert!(!complete.partial, "a leaf at the limit is fully scanned");
        assert_eq!(complete.found[0].path, boundary);
        for index in 0..12 {
            fs::create_dir(boundary.join(format!("child-{index:02}"))).unwrap();
        }
        let result = scan(&root, DISCOVERY_MAX_ENTRIES, DISCOVERY_MAX_DEPTH);
        assert!(result.partial);
        assert_eq!(result.warnings.len(), 1);
        let warning = &result.warnings[0];
        assert!(warning.contains("16 Ebenen"));
        assert!(warning.contains(&display(
            &boundary.strip_prefix(&root).unwrap().join("child-00")
        )));
        assert!(warning.contains("child-07"));
        assert!(!warning.contains("child-08"));
        assert!(warning.contains("und 4 weitere"));
        assert!(
            !warning.contains(&display(&root)),
            "diagnostics use relative paths"
        );
        // Entry count includes sixteen ancestors and the marker at the boundary.
        let mixed = scan(&root, DISCOVERY_MAX_DEPTH + 5, DISCOVERY_MAX_DEPTH);
        assert!(mixed.partial);
        assert!(mixed
            .warnings
            .iter()
            .any(|warning| warning.contains("Dateianzahl-Limit")));
        assert!(mixed
            .warnings
            .iter()
            .any(|warning| warning.contains("Nicht durchsucht:")));
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
