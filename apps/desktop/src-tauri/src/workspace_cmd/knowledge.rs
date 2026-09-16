//! A provenance-only index over existing project readers. Never host credentials.
use super::*;

#[derive(Serialize)]
pub struct KnowledgeEntry {
    pub key: String,
    pub kind: String,
    pub name: String,
    pub title: String,
    pub file: String,
    pub absolute_path: String,
    pub worktree_id: String,
    pub source: String,
    pub root: String,
    pub status: String,
    pub host: Option<String>,
}

#[derive(Serialize)]
pub struct KnowledgeSource {
    pub id: String,
    pub name: String,
    pub path: String,
    pub available: bool,
    pub errors: Vec<String>,
}

#[derive(Serialize)]
pub struct KnowledgeCatalog {
    pub entries: Vec<KnowledgeEntry>,
    pub sources: Vec<KnowledgeSource>,
    pub warnings: Vec<String>,
}

fn preflight(root: &Path, kind: &str) -> Result<bool, String> {
    if !board_directory(&root.join(".agent"))? {
        return Ok(false);
    }
    let dir = root.join(".agent").join(kind);
    if !board_directory(&dir)? {
        return Ok(false);
    }
    let mut count = 0;
    for entry in fs::read_dir(&dir).map_err(|e| e.to_string())? {
        count += 1;
        if count > 1000 {
            return Err("Wissensquelle hat mehr als 1000 Einträge".into());
        }
        let path = entry.map_err(|e| e.to_string())?.path();
        if kind == "playbooks" {
            if path.extension().is_some_and(|v| v == "md") {
                small_text(&path, 256 * 1024)?;
            }
        } else if fs::symlink_metadata(&path)
            .map_err(|e| e.to_string())?
            .is_file()
        {
            continue;
        } else if board_directory(&path)? {
            let file = path.join(if kind == "skills" {
                "SKILL.md"
            } else {
                "TOOL.md"
            });
            if file.exists() {
                small_text(&file, 256 * 1024)?;
            }
        }
    }
    Ok(true)
}

pub(super) fn read(workspace: &Workspace) -> KnowledgeCatalog {
    let workspace = super::registers::with_root(workspace.clone());
    let mut catalog = KnowledgeCatalog {
        entries: vec![],
        sources: vec![],
        warnings: vec![],
    };
    let started = Instant::now();
    for tree in workspace
        .repositories
        .iter()
        .flat_map(|repo| &repo.worktrees)
    {
        if catalog.sources.len() >= 100 || started.elapsed() > Duration::from_secs(3) {
            catalog
                .warnings
                .push("Wissenskatalog unvollständig: Lesebudget erreicht".into());
            break;
        }
        let mut source = KnowledgeSource {
            id: tree.id.clone(),
            name: if tree.path == workspace.root {
                "Root".into()
            } else {
                tree.relative_path.clone()
            },
            path: tree.path.clone(),
            available: false,
            errors: vec![],
        };
        let root = match resolve_worktree(&workspace, &tree.id) {
            Ok(path) => PathBuf::from(path),
            Err(error) => {
                source.errors.push(error);
                catalog.sources.push(source);
                continue;
            }
        };
        source.available = true;
        for kind in ["skills", "tools", "playbooks"] {
            match preflight(&root, kind) {
                Ok(false) => continue,
                Err(error) => {
                    source.errors.push(format!("{kind}: {error}"));
                    continue;
                }
                Ok(true) => (),
            }
            let entries = match kind {
                "skills" => crate::project_cmd::project_skills(tree.path.clone())
                    .and_then(|v| serde_json::to_value(v).map_err(|e| e.to_string())),
                "tools" => crate::project_cmd::project_tools(tree.path.clone())
                    .and_then(|v| serde_json::to_value(v).map_err(|e| e.to_string())),
                _ => crate::playbook_cmd::project_playbooks(tree.path.clone())
                    .and_then(|v| serde_json::to_value(v).map_err(|e| e.to_string())),
            };
            match entries {
                Err(error) => source.errors.push(format!("{kind}: {error}")),
                Ok(entries) => {
                    for entry in entries.as_array().into_iter().flatten() {
                        let file = entry["file"].as_str().unwrap_or("").replace('\\', "/");
                        let name = entry["name"]
                            .as_str()
                            .or_else(|| entry["title"].as_str())
                            .unwrap_or(&file)
                            .to_owned();
                        catalog.entries.push(KnowledgeEntry {
                            key: serde_json::to_string(&[&workspace.id, &tree.id, kind, &file])
                                .unwrap(),
                            kind: kind.into(),
                            title: entry["title"].as_str().unwrap_or(&name).to_owned(),
                            name,
                            absolute_path: display(&root.join(&file)),
                            file,
                            worktree_id: tree.id.clone(),
                            source: source.name.clone(),
                            root: tree.path.clone(),
                            status: entry["status"]
                                .as_str()
                                .unwrap_or(if kind == "tools" {
                                    "contract"
                                } else {
                                    "readable"
                                })
                                .into(),
                            host: None,
                        });
                    }
                }
            }
        }
        // Read only names after validating both config files. No env, headers, args or URLs.
        for (host, file, field) in [
            ("claude", ".mcp.json", "mcpServers"),
            ("codex", ".codex/config.toml", "mcp_servers"),
        ] {
            let path = root.join(file);
            if !path.exists() {
                continue;
            }
            let result = (|| -> Result<serde_json::Value, String> {
                if host == "codex" {
                    board_directory(&root.join(".codex"))?;
                }
                let text = small_text(&path, 256 * 1024)?;
                let value = if host == "claude" {
                    serde_json::from_str(&text).map_err(|_| "Ungültiges JSON".to_string())?
                } else {
                    let toml: toml::Value =
                        toml::from_str(&text).map_err(|_| "Ungültiges TOML".to_string())?;
                    serde_json::to_value(toml)
                        .map_err(|_| "Ungültige MCP-Konfiguration".to_string())?
                };
                Ok(value)
            })();
            match result {
                Err(error) => source.errors.push(format!("{file}: {error}")),
                Ok(config) => {
                    if config.get(field).is_some_and(|value| !value.is_object()) {
                        source.errors.push(format!(
                            "{file}: Serverdefinitionen müssen ein Mapping sein"
                        ));
                        continue;
                    }
                    for (name, definition) in config[field].as_object().into_iter().flatten() {
                        catalog.entries.push(KnowledgeEntry {
                            key: serde_json::to_string(&[
                                &workspace.id,
                                &tree.id,
                                "mcps",
                                host,
                                name,
                            ])
                            .unwrap(),
                            kind: "mcps".into(),
                            name: name.clone(),
                            title: name.clone(),
                            file: file.into(),
                            absolute_path: display(&path),
                            worktree_id: tree.id.clone(),
                            source: source.name.clone(),
                            root: tree.path.clone(),
                            status: if definition.get("enabled").and_then(|v| v.as_bool())
                                == Some(false)
                            {
                                "disabled"
                            } else {
                                "host-unconfirmed"
                            }
                            .into(),
                            host: Some(host.into()),
                        });
                    }
                }
            }
        }
        catalog.sources.push(source);
    }
    catalog.entries.sort_by(|a, b| {
        a.title
            .to_lowercase()
            .cmp(&b.title.to_lowercase())
            .then(a.key.cmp(&b.key))
    });
    catalog
}

#[tauri::command]
pub async fn workspace_knowledge(workspace_id: String) -> Result<KnowledgeCatalog, String> {
    let workspace = workspace_snapshot(workspace_id).await?;
    tauri::async_runtime::spawn_blocking(move || read(&workspace))
        .await
        .map_err(|e| e.to_string())
}
