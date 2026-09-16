//! Native adapter for the portable core workspace-registers.json contract.
use super::*;
use std::collections::BTreeMap;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Identity {
    pub id: String,
    pub name: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub version: u32,
    pub id: String,
    pub name: String,
    pub sources: Vec<Identity>,
    pub repositories: Vec<Identity>,
    pub default_source: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Binding {
    pub manifest: Manifest,
    /// First checkout is the explicit write target; others are compared, never merged.
    pub bindings: BTreeMap<String, Vec<String>>,
}

fn identity(value: &Identity) -> bool {
    !value.id.is_empty()
        && value.id.len() <= 128
        && value.id.as_bytes()[0].is_ascii_alphanumeric()
        && value
            .id
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || b"._-".contains(&c))
        && !value.name.trim().is_empty()
        && value.name.chars().count() <= 200
}

fn parse(text: &str) -> Result<Manifest, String> {
    if text.len() > 256 * 1024 {
        return Err("Registermanifest zu groß".into());
    }
    let value: Manifest = serde_json::from_str(text).map_err(|e| e.to_string())?;
    if value.version != 1
        || !identity(&Identity {
            id: value.id.clone(),
            name: value.name.clone(),
        })
    {
        return Err("Ungültige Manifestversion oder Workspace-Identität".into());
    }
    for entries in [&value.sources, &value.repositories] {
        let mut ids = HashSet::new();
        if entries.is_empty()
            || entries.len() > 100
            || entries
                .iter()
                .any(|entry| !identity(entry) || !ids.insert(&entry.id))
        {
            return Err("Register-/Repo-IDs müssen eindeutig sein (1–100 Einträge)".into());
        }
    }
    if value
        .default_source
        .as_ref()
        .is_some_and(|id| !value.sources.iter().any(|s| &s.id == id))
    {
        return Err("Standardregister fehlt im Manifest".into());
    }
    Ok(value)
}

fn binding_path(workspace: &Workspace) -> Result<PathBuf, String> {
    Ok(store_path()?
        .parent()
        .ok_or("Workspace-Speicher fehlt")?
        .join(format!("registers-{}.json", workspace.id)))
}

pub(super) fn load_binding(workspace: &Workspace) -> Result<Option<Binding>, String> {
    let path = binding_path(workspace)?;
    if !path.exists() {
        return Ok(None);
    }
    let binding: Binding =
        serde_json::from_str(&small_text(&path, 512 * 1024)?).map_err(|e| e.to_string())?;
    parse(&serde_json::to_string(&binding.manifest).map_err(|e| e.to_string())?)?;
    validate_binding(workspace, &binding, false)?;
    Ok(Some(binding))
}

fn validate_binding(
    workspace: &Workspace,
    binding: &Binding,
    check_targets: bool,
) -> Result<(), String> {
    if binding.bindings.len() != binding.manifest.sources.len() {
        return Err("Jedes Register benötigt eine lokale Bindung".into());
    }
    let mut seen = HashSet::new();
    for source in &binding.manifest.sources {
        let trees = binding
            .bindings
            .get(&source.id)
            .ok_or("Registerbindung fehlt")?;
        if trees.is_empty() || trees.len() > 100 {
            return Err("Register benötigt 1–100 Checkouts".into());
        }
        for id in trees {
            if !seen.insert(id) {
                return Err("Checkout darf nur einem Register zugeordnet sein".into());
            }
            // Missing paths are reported independently when reading the board.
            if check_targets
                && id != &format!("root:{}", workspace.id)
                && !workspace
                    .repositories
                    .iter()
                    .any(|repo| repo.worktrees.iter().any(|tree| &tree.id == id))
            {
                return Err(format!("Unbekannte lokale Checkout-ID: {id}"));
            }
        }
    }
    Ok(())
}

pub(super) fn with_root(mut workspace: Workspace) -> Workspace {
    if workspace.repositories.iter().any(|repo| {
        repo.worktrees
            .iter()
            .any(|tree| tree.path == workspace.root)
    }) {
        return workspace;
    }
    let id = format!("root:{}", workspace.id);
    workspace.projects.push(Project {
        id: id.clone(),
        name: workspace.name.clone(),
        repository_ids: vec![id.clone()],
    });
    workspace.repositories.push(Repository {
        id: id.clone(),
        name: "Workspace-Ordner".into(),
        common_dir: None,
        default_project_id: id.clone(),
        worktrees: vec![Worktree {
            id,
            path: workspace.root.clone(),
            relative_path: ".".into(),
            markers: vec![],
            available: true,
        }],
    });
    workspace
}

pub(super) fn apply_binding(board: &mut WorkspaceBoard, binding: &Binding) {
    let all = std::mem::take(&mut board.specs);
    for source in &binding.manifest.sources {
        let trees = &binding.bindings[&source.id];
        let primary = &trees[0];
        let fingerprints = |tree: &String| -> BTreeMap<String, String> {
            all.iter()
                .filter(|s| &s.worktree_id == tree)
                .map(|s| {
                    (
                        s.spec.file.clone(),
                        serde_json::to_string(&s.spec).unwrap_or_default(),
                    )
                })
                .collect()
        };
        let canonical = fingerprints(primary);
        for tree in &trees[1..] {
            if fingerprints(tree) != canonical {
                board.warnings.push(format!("Register {}: Checkouts weichen ab. Gewähltes Schreibziel: {}. Bindung unter Registerquellen prüfen.", source.name, primary));
            }
        }
    }
    for mut entry in all {
        if let Some(source) = binding
            .manifest
            .sources
            .iter()
            .find(|s| binding.bindings[&s.id][0] == entry.worktree_id)
        {
            entry.key =
                serde_json::to_string(&[&binding.manifest.id, &source.id, &entry.spec.file])
                    .unwrap();
            entry.repository_id = source.id.clone();
            entry.repository_name = source.name.clone();
            board.specs.push(entry);
        }
    }
    board.partial = !board.warnings.is_empty();
}

#[tauri::command]
pub async fn workspace_registers(workspace_id: String) -> Result<Option<Binding>, String> {
    let workspace = workspace_snapshot(workspace_id).await?;
    load_binding(&workspace)
}

#[tauri::command]
pub async fn workspace_register_import(
    workspace_id: String,
    worktree_id: String,
) -> Result<Manifest, String> {
    let workspace = workspace_snapshot(workspace_id).await?;
    let root = PathBuf::from(resolve_worktree(&workspace, &worktree_id)?);
    let path =
        crate::project_cmd::safe_project_path(&root, ".agent/specs/workspace-registers.json")?;
    parse(&small_text(&path, 256 * 1024)?)
}

#[tauri::command]
pub async fn workspace_register_save(
    workspace_id: String,
    manifest: String,
    bindings: BTreeMap<String, Vec<String>>,
    export_target: Option<String>,
) -> Result<Binding, String> {
    let workspace = workspace_snapshot(workspace_id).await?;
    let binding = Binding {
        manifest: parse(&manifest)?,
        bindings,
    };
    validate_binding(&workspace, &binding, true)?;
    if let Some(target) = export_target {
        let root = PathBuf::from(resolve_worktree(&workspace, &target)?);
        let base = root.join(".agent/specs");
        if !board_directory(&root.join(".agent"))? || !board_directory(&base)? {
            return Err("Zuerst ein bestehendes Register als Speicherort wählen".into());
        }
        let path =
            crate::project_cmd::safe_project_path(&root, ".agent/specs/workspace-registers.json")?;
        if path.exists() {
            small_text(&path, 256 * 1024)?;
        }
        fs::write(
            path,
            format!(
                "{}\n",
                serde_json::to_string_pretty(&binding.manifest).unwrap()
            ),
        )
        .map_err(|e| e.to_string())?;
    }
    let path = binding_path(&workspace)?;
    let tmp = path.with_extension(format!("{}.tmp", id()));
    fs::write(&tmp, serde_json::to_vec_pretty(&binding).unwrap()).map_err(|e| e.to_string())?;
    fs::rename(tmp, path).map_err(|e| e.to_string())?;
    Ok(binding)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn portable_contract_rejects_local_paths_and_duplicate_sources() {
        let valid = r#"{"version":1,"id":"team","name":"Team","sources":[{"id":"api","name":"API"}],"repositories":[{"id":"code","name":"Code"}],"default_source":"api"}"#;
        assert!(parse(valid).is_ok());
        assert!(parse(&valid.replace("\"version\":1", "\"version\":2")).is_err());
        assert!(parse(
            &valid.replace("\"version\":1", "\"path\":\"/private/local\",\"version\":1")
        )
        .is_err());
        assert!(parse(&valid.replace(
            "\"default_source\":\"api\"",
            "\"default_source\":\"missing\""
        ))
        .is_err());
    }
}
