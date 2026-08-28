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
    let canonical = path
        .canonicalize()
        .map_err(|e| format!("{}: {e}", path.display()))?;
    Ok(strip_verbatim(canonical))
}

/// Windows-`canonicalize` liefert Verbatim-Pfade (`\\?\C:\…`) — fürs UI und
/// als cwd-String unbrauchbar. Präfix abstreifen; anderswo ein No-op.
fn strip_verbatim(path: PathBuf) -> PathBuf {
    let text = path.to_string_lossy();
    if let Some(rest) = text.strip_prefix(r"\\?\UNC\") {
        return PathBuf::from(format!(r"\\{rest}"));
    }
    if let Some(rest) = text.strip_prefix(r"\\?\") {
        return PathBuf::from(rest.to_string());
    }
    path
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

/// Traversal-Guard für read **und** write: nur relative Pfade ohne `..`,
/// ohne Wurzel (has_root fängt Windows-Sonderfälle wie `/etc/passwd` —
/// dort laufwerkslos und damit NICHT is_absolute) und ohne Laufwerkspräfix.
fn safe_project_path(root: &Path, file: &str) -> Result<PathBuf, String> {
    let relative = Path::new(file);
    let escapes = relative.is_absolute()
        || relative.has_root()
        || relative
            .components()
            .any(|component| matches!(component, Component::ParentDir | Component::Prefix(_)));
    if escapes {
        return Err(format!("Pfad zeigt aus dem Projekt heraus: {file}"));
    }
    Ok(root.join(relative))
}

/// Eine Datei unterhalb der Projektwurzel lesen (Pläne, SKILL.md, …).
#[tauri::command]
pub fn project_read_file(project: String, file: String) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))
}

/// Eine Datei unterhalb der Projektwurzel schreiben (D20: Plan-Editor).
/// Legt keine Verzeichnisse an — der Zielordner muss existieren.
#[tauri::command]
pub fn project_write_file(project: String, file: String, content: String) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    std::fs::write(&path, content).map_err(|e| format!("{}: {e}", path.display()))
}

// --- Board (D19: iKanbanAI-Format) -------------------------------------------
// `.agent/board/<id>.md`: flaches Frontmatter (`key: value`, kein
// verschachteltes YAML) zwischen `---`-Zeilen, danach der Markdown-Body.
// Zusatzfelder bleiben byte-stabil erhalten — beim Verschieben wird darum
// NUR die `station:`-Zeile umgeschrieben.

pub const BOARD_STATIONS: [&str; 3] = ["Backlog", "Doing", "Done"];

#[derive(Serialize)]
pub struct TicketEntry {
    /// Relativ zur Projektwurzel (Schlüssel für `project_board_move`).
    file: String,
    id: String,
    title: String,
    station: String,
    assignee: Option<String>,
    created: Option<String>,
    ready: bool,
    needs_human: bool,
    /// Backlog-Sortierung (iKanban R5a): `order` → `created` → `id`.
    order: Option<i64>,
    body: String,
}

/// Flaches Frontmatter: Zeilen zwischen erster und zweiter `---`-Zeile,
/// jede als `key: value` (erste `:`-Trennung). Kein YAML-Parser — die
/// iKanban-Dateien sind flach, und wir wollen sie byte-stabil lassen.
fn parse_flat_frontmatter(text: &str) -> Option<(Vec<(String, String)>, &str)> {
    let mut lines = text.split_inclusive('\n');
    if lines.next()?.trim_end() != "---" {
        return None;
    }
    let mut fields = Vec::new();
    let mut consumed = text.find('\n')? + 1;
    for line in lines {
        if line.trim_end() == "---" {
            let body = &text[consumed + line.len()..];
            return Some((fields, body.strip_prefix('\n').unwrap_or(body)));
        }
        if let Some((key, value)) = line.split_once(':') {
            fields.push((key.trim().to_string(), value.trim().to_string()));
        }
        consumed += line.len();
    }
    None
}

fn flat_lookup<'a>(fields: &'a [(String, String)], key: &str) -> Option<&'a str> {
    fields
        .iter()
        .find(|(k, _)| k.eq_ignore_ascii_case(key))
        .map(|(_, v)| v.as_str())
}

fn flat_truthy(fields: &[(String, String)], key: &str) -> bool {
    matches!(
        flat_lookup(fields, key)
            .map(str::to_ascii_lowercase)
            .as_deref(),
        Some("true" | "yes" | "1")
    )
}

/// Tickets aus `.agent/board/`. Fehlender Ordner ⇒ leere Liste; die
/// Spalten-Sortierung (Backlog: order → created → id) macht das Frontend.
#[tauri::command]
pub fn project_board(project: String) -> Result<Vec<TicketEntry>, String> {
    let root = resolve_project_root(&project)?;
    let board_dir = root.join(".agent/board");
    let Ok(entries) = std::fs::read_dir(&board_dir) else {
        return Ok(Vec::new());
    };
    let mut paths: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "md"))
        .collect();
    paths.sort();
    let mut tickets = Vec::new();
    for path in paths {
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        let Some((fields, body)) = parse_flat_frontmatter(&text) else {
            continue;
        };
        let stem = path
            .file_stem()
            .map(|stem| stem.to_string_lossy().into_owned())
            .unwrap_or_default();
        let Some(station) = flat_lookup(&fields, "station") else {
            continue;
        };
        tickets.push(TicketEntry {
            file: path
                .strip_prefix(&root)
                .unwrap_or(&path)
                .to_string_lossy()
                .into_owned(),
            id: flat_lookup(&fields, "id").unwrap_or(&stem).to_string(),
            title: flat_lookup(&fields, "title").unwrap_or(&stem).to_string(),
            station: station.to_string(),
            assignee: flat_lookup(&fields, "assignee").map(str::to_string),
            created: flat_lookup(&fields, "created").map(str::to_string),
            ready: flat_truthy(&fields, "ready"),
            needs_human: flat_truthy(&fields, "needs_human"),
            order: flat_lookup(&fields, "order").and_then(|raw| raw.parse().ok()),
            body: body.to_string(),
        });
    }
    Ok(tickets)
}

/// Verschiebt ein Ticket in eine andere Station: ersetzt **nur** die
/// `station:`-Zeile im Frontmatter, alles andere bleibt byte-stabil —
/// iKanbanAI beobachtet das Verzeichnis und zieht live nach.
#[tauri::command]
pub fn project_board_move(project: String, file: String, station: String) -> Result<(), String> {
    if !BOARD_STATIONS.contains(&station.as_str()) {
        return Err(format!("Unbekannte Station: {station}"));
    }
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    if !path.starts_with(root.join(".agent/board")) {
        return Err(format!("Kein Board-Ticket: {file}"));
    }
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    let mut in_frontmatter = false;
    let mut replaced = false;
    let mut out = String::with_capacity(text.len());
    for line in text.split_inclusive('\n') {
        if line.trim_end() == "---" {
            in_frontmatter = !in_frontmatter;
            out.push_str(line);
            continue;
        }
        if in_frontmatter && !replaced {
            if let Some((key, _)) = line.split_once(':') {
                if key.trim().eq_ignore_ascii_case("station") {
                    let ending = if line.ends_with("\r\n") {
                        "\r\n"
                    } else if line.ends_with('\n') {
                        "\n"
                    } else {
                        ""
                    };
                    out.push_str(&format!("station: {station}{ending}"));
                    replaced = true;
                    continue;
                }
            }
        }
        out.push_str(line);
    }
    if !replaced {
        return Err(format!("Keine station:-Zeile im Frontmatter: {file}"));
    }
    std::fs::write(&path, out).map_err(|e| format!("{}: {e}", path.display()))
}

// --- Tools (P3: TOOL.md + Status je Plattform) --------------------------------

#[derive(Serialize)]
pub struct ToolPlatform {
    name: String,
    status: Option<String>,
    checked: Option<String>,
}

#[derive(Serialize)]
pub struct ToolEntry {
    name: String,
    /// TOOL.md relativ zur Projektwurzel (für `project_read_file`).
    file: String,
    description: Option<String>,
    /// Aus welchen Skills der Spec stammt (`expansions.yaml`, tools.<n>.from).
    from: Vec<String>,
    platforms: Vec<ToolPlatform>,
    /// Dateien im Tool-Ordner außer TOOL.md (Implementierungen, Referenzen).
    files: Vec<String>,
}

fn expansion_tools(root: &Path) -> HashMap<String, (Vec<String>, Vec<ToolPlatform>)> {
    let Ok(text) = std::fs::read_to_string(root.join(".agent/speccify/expansions.yaml")) else {
        return HashMap::new();
    };
    let Ok(value) = serde_yaml::from_str::<serde_yaml::Value>(&text) else {
        return HashMap::new();
    };
    let Some(tools) = value.get("tools").and_then(|tools| tools.as_mapping()) else {
        return HashMap::new();
    };
    tools
        .iter()
        .filter_map(|(name, entry)| {
            let name = name.as_str()?.to_string();
            let from = entry
                .get("from")
                .and_then(|from| from.as_sequence())
                .map(|from| {
                    from.iter()
                        .filter_map(|skill| skill.as_str().map(str::to_string))
                        .collect()
                })
                .unwrap_or_default();
            let platforms = entry
                .get("platforms")
                .and_then(|platforms| platforms.as_mapping())
                .map(|platforms| {
                    platforms
                        .iter()
                        .filter_map(|(platform, details)| {
                            let platform = platform.as_str()?.to_string();
                            // Je nach Stand String (`implemented`) oder
                            // Mapping (`{status, checked}`).
                            let (status, checked) = match details {
                                serde_yaml::Value::String(status) => (Some(status.clone()), None),
                                other => (
                                    other
                                        .get("status")
                                        .and_then(|s| s.as_str())
                                        .map(str::to_string),
                                    other
                                        .get("checked")
                                        .and_then(|c| c.as_str())
                                        .map(str::to_string),
                                ),
                            };
                            Some(ToolPlatform {
                                name: platform,
                                status,
                                checked,
                            })
                        })
                        .collect()
                })
                .unwrap_or_default();
            Some((name, (from, platforms)))
        })
        .collect()
}

/// Tools aus `.agent/tools/` mit Status je Plattform aus `expansions.yaml`.
#[tauri::command]
pub fn project_tools(project: String) -> Result<Vec<ToolEntry>, String> {
    let root = resolve_project_root(&project)?;
    let mut origins = expansion_tools(&root);
    let tools_dir = root.join(".agent/tools");
    let Ok(entries) = std::fs::read_dir(&tools_dir) else {
        return Ok(Vec::new());
    };
    let mut dirs: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.join("TOOL.md").is_file())
        .collect();
    dirs.sort();
    Ok(dirs
        .into_iter()
        .map(|dir| {
            let name = dir
                .file_name()
                .map(|name| name.to_string_lossy().into_owned())
                .unwrap_or_default();
            let tool_md = dir.join("TOOL.md");
            let frontmatter = std::fs::read_to_string(&tool_md)
                .ok()
                .and_then(|text| split_frontmatter(&text).0);
            let mut files: Vec<String> = std::fs::read_dir(&dir)
                .map(|entries| {
                    entries
                        .filter_map(Result::ok)
                        .map(|entry| entry.file_name().to_string_lossy().into_owned())
                        .filter(|file| file != "TOOL.md")
                        .collect()
                })
                .unwrap_or_default();
            files.sort();
            let (from, platforms) = origins.remove(&name).unwrap_or_default();
            ToolEntry {
                file: tool_md
                    .strip_prefix(&root)
                    .unwrap_or(&tool_md)
                    .to_string_lossy()
                    .into_owned(),
                description: frontmatter_str(&frontmatter, "description"),
                from,
                platforms,
                files,
                name,
            }
        })
        .collect())
}

/// Die Plattform, auf der die App gerade läuft — der Tools-Tab zeigt damit
/// „fehlt auf dieser Plattform" an (Sprache von `expansions.yaml`).
#[tauri::command]
pub fn project_platform() -> &'static str {
    if cfg!(windows) {
        "windows"
    } else if cfg!(target_os = "macos") {
        "macos"
    } else {
        "linux"
    }
}

// --- MCPs (F2: .mcp.json + Allowlist) -----------------------------------------

#[derive(Serialize)]
pub struct McpInfo {
    /// `mcpServers` aus `.mcp.json` (roh — die UI zeigt Name + Details).
    servers: serde_json::Value,
    /// `permissions.allow` aus `.claude/settings.json`.
    allow: Vec<String>,
    /// `permissions.allow` aus `.claude/settings.local.json`.
    allow_local: Vec<String>,
}

fn permissions_allow(path: &Path) -> Vec<String> {
    std::fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str::<serde_json::Value>(&text).ok())
        .and_then(|value| {
            value
                .get("permissions")?
                .get("allow")?
                .as_array()
                .map(|allow| {
                    allow
                        .iter()
                        .filter_map(|entry| entry.as_str().map(str::to_string))
                        .collect()
                })
        })
        .unwrap_or_default()
}

/// Projektbezogene MCP-Server und Claude-Allowlist (lesend, F2).
#[tauri::command]
pub fn project_mcps(project: String) -> Result<McpInfo, String> {
    let root = resolve_project_root(&project)?;
    let servers = std::fs::read_to_string(root.join(".mcp.json"))
        .ok()
        .and_then(|text| serde_json::from_str::<serde_json::Value>(&text).ok())
        .and_then(|value| value.get("mcpServers").cloned())
        .unwrap_or(serde_json::Value::Null);
    Ok(McpInfo {
        servers,
        allow: permissions_allow(&root.join(".claude/settings.json")),
        allow_local: permissions_allow(&root.join(".claude/settings.local.json")),
    })
}

/// Welche Agent-Konfigurationsdateien es im Projekt gibt (Agent-Tab).
#[tauri::command]
pub fn project_agent_files(project: String) -> Result<Vec<String>, String> {
    let root = resolve_project_root(&project)?;
    Ok(["CLAUDE.md", "AGENTS.md", ".agent/AGENT.md"]
        .into_iter()
        .filter(|candidate| root.join(candidate).is_file())
        .map(str::to_string)
        .collect())
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

    #[test]
    fn board_reads_tickets_and_moves_byte_stable() {
        let dir = project_fixture("board");
        std::fs::create_dir_all(dir.join(".agent/board")).unwrap();
        // Zusatzfelder + CRLF-fremde Details bewusst dabei: move darf NUR
        // die station-Zeile anfassen (D19, byte-stabiler Rest).
        let ticket = "---\nid: t-1\ntitle: Fenster testen\nstation: Backlog\ncreated: 2026-08-28T06:00:00Z\norder: 2\nready: true\ncustom: bleibt  erhalten\n---\n\n# Fenster testen\n\nBody bleibt unangetastet.\n";
        std::fs::write(dir.join(".agent/board/t-1.md"), ticket).unwrap();
        std::fs::write(
            dir.join(".agent/board/t-2.md"),
            "---\ntitle: Ohne id\nstation: Done\n---\nFertig.\n",
        )
        .unwrap();
        let project = dir.to_string_lossy().into_owned();

        let tickets = project_board(project.clone()).unwrap();
        assert_eq!(tickets.len(), 2);
        let first = &tickets[0];
        assert_eq!(first.id, "t-1");
        assert_eq!(first.title, "Fenster testen");
        assert_eq!(first.station, "Backlog");
        assert_eq!(first.order, Some(2));
        assert!(first.ready);
        assert!(!first.needs_human);
        assert!(first.body.contains("Body bleibt"));
        // Ohne id-Feld zählt der Dateistamm.
        assert_eq!(tickets[1].id, "t-2");

        project_board_move(project.clone(), first.file.clone(), "Doing".into()).unwrap();
        let moved = std::fs::read_to_string(dir.join(".agent/board/t-1.md")).unwrap();
        assert_eq!(moved, ticket.replace("station: Backlog", "station: Doing"));

        let unknown = project_board_move(project, "t-1.md".into(), "Doing".into()).unwrap_err();
        assert!(unknown.contains("Kein Board-Ticket"));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn write_file_honors_the_traversal_guard() {
        let dir = project_fixture("write");
        let project = dir.to_string_lossy().into_owned();
        project_write_file(
            project.clone(),
            ".agent/plans/aktuell.md".into(),
            "---\nlifecycle: active\n---\n# Neu\n".into(),
        )
        .unwrap();
        assert!(std::fs::read_to_string(dir.join(".agent/plans/aktuell.md"))
            .unwrap()
            .contains("# Neu"));
        for evil in ["../raus.md", "/etc/passwd"] {
            let error = project_write_file(project.clone(), evil.into(), "x".into()).unwrap_err();
            assert!(error.contains("aus dem Projekt heraus"), "{evil} → {error}");
        }
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn tools_carry_platform_status_from_expansions() {
        let dir = project_fixture("tools");
        std::fs::create_dir_all(dir.join(".agent/tools/verify-something")).unwrap();
        std::fs::write(
            dir.join(".agent/tools/verify-something/TOOL.md"),
            "---\nname: verify-something\ndescription: Prueft etwas.\n---\n# Spec\n",
        )
        .unwrap();
        std::fs::write(
            dir.join(".agent/tools/verify-something/macos.sh"),
            "#!/bin/sh\n",
        )
        .unwrap();
        std::fs::write(
            dir.join(".agent/speccify/expansions.yaml"),
            "schema_version: 1\nskills: {}\ntools:\n  verify-something:\n    from:\n    - alpha\n    platforms:\n      macos:\n        status: verified\n        checked: '2026-08-28'\n",
        )
        .unwrap();
        let project = dir.to_string_lossy().into_owned();

        let tools = project_tools(project).unwrap();
        assert_eq!(tools.len(), 1);
        let tool = &tools[0];
        assert_eq!(tool.name, "verify-something");
        assert_eq!(tool.description.as_deref(), Some("Prueft etwas."));
        assert_eq!(tool.from, vec!["alpha".to_string()]);
        assert_eq!(tool.files, vec!["macos.sh".to_string()]);
        assert_eq!(tool.platforms.len(), 1);
        assert_eq!(tool.platforms[0].name, "macos");
        assert_eq!(tool.platforms[0].status.as_deref(), Some("verified"));
        assert_eq!(tool.platforms[0].checked.as_deref(), Some("2026-08-28"));

        let _ = std::fs::remove_dir_all(&dir);
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
