//! Dateibaum und Datei-Infos fürs Projektfenster (Plan
//! ide-im-projektfenster.md, I1). Der Baum wird **je Verzeichnis** gelesen
//! (lazy), `.gitignore`/`.git/info/exclude` gelten über das `ignore`-Crate,
//! `.git` selbst bleibt immer zu. Lesen/Schreiben von Dateien läuft über
//! die vorhandenen `project_read_file`/`project_write_file` (Traversal-Guard
//! in `safe_project_path`).

use std::path::Path;

use serde::Serialize;

use crate::project_cmd::{resolve_project_root, safe_project_path};

#[derive(Serialize, Debug, PartialEq)]
pub struct TreeEntry {
    pub name: String,
    /// Relativ zur Projektwurzel, immer mit `/` getrennt.
    pub path: String,
    pub is_dir: bool,
    pub size: u64,
}

/// Immer ausgeblendet — unabhängig von .gitignore.
const ALWAYS_HIDDEN: [&str; 1] = [".git"];

fn relative_slash(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .components()
        .map(|component| component.as_os_str().to_string_lossy().into_owned())
        .collect::<Vec<_>>()
        .join("/")
}

pub(crate) fn list_dir(root: &Path, dir: &str) -> Result<Vec<TreeEntry>, String> {
    let base = if dir.is_empty() {
        root.to_path_buf()
    } else {
        safe_project_path(root, dir)?
    };
    if !base.is_dir() {
        return Err(format!("Kein Verzeichnis: {dir}"));
    }
    let mut entries = Vec::new();
    // WalkBuilder liest .gitignore-Regeln aus allen Elternordnern bis zur
    // Wurzel; max_depth(1) = nur die direkten Kinder.
    let walker = ignore::WalkBuilder::new(&base)
        .max_depth(Some(1))
        .hidden(false)
        .git_ignore(true)
        .git_exclude(true)
        .git_global(false)
        .parents(true)
        .build();
    for item in walker.flatten() {
        let path = item.path();
        if path == base {
            continue;
        }
        let name = item.file_name().to_string_lossy().into_owned();
        if ALWAYS_HIDDEN.contains(&name.as_str()) {
            continue;
        }
        let metadata = item.metadata().ok();
        let is_dir = item.file_type().map(|t| t.is_dir()).unwrap_or(false);
        entries.push(TreeEntry {
            name,
            path: relative_slash(root, path),
            is_dir,
            size: if is_dir {
                0
            } else {
                metadata.map(|m| m.len()).unwrap_or(0)
            },
        });
    }
    entries.sort_by(|a, b| {
        b.is_dir
            .cmp(&a.is_dir)
            .then_with(|| a.name.to_lowercase().cmp(&b.name.to_lowercase()))
    });
    Ok(entries)
}

/// Direkte Kinder eines Projektverzeichnisses (`dir` relativ, `""` = Wurzel).
#[tauri::command]
pub fn project_tree(project: String, dir: String) -> Result<Vec<TreeEntry>, String> {
    let root = resolve_project_root(&project)?;
    list_dir(&root, &dir)
}

// --- I3: Suche, Anlegen, Umbenennen, Löschen -----------------------------------

#[derive(Serialize, Debug, PartialEq)]
pub struct SearchHit {
    pub path: String,
    pub line: u64,
    /// 0-basierte Spalte des ersten Treffers in der Zeile.
    pub column: usize,
    pub text: String,
}

const SEARCH_MAX_FILE: u64 = 2 * 1024 * 1024;

fn escape_regex(text: &str) -> String {
    let mut out = String::with_capacity(text.len() * 2);
    for ch in text.chars() {
        if "\\.+*?()|[]{}^$#&-~".contains(ch) {
            out.push('\\');
        }
        out.push(ch);
    }
    out
}

pub(crate) fn search_tree(
    root: &Path,
    query: &str,
    regex: bool,
    case_sensitive: bool,
    limit: usize,
) -> Result<Vec<SearchHit>, String> {
    use grep_matcher::Matcher;
    use grep_searcher::sinks::UTF8;
    use grep_searcher::{BinaryDetection, SearcherBuilder};

    if query.trim().is_empty() {
        return Ok(Vec::new());
    }
    let pattern = if regex {
        query.to_string()
    } else {
        escape_regex(query)
    };
    let matcher = grep_regex::RegexMatcherBuilder::new()
        .case_insensitive(!case_sensitive)
        .build(&pattern)
        .map_err(|e| format!("Suchmuster ungültig: {e}"))?;
    let mut searcher = SearcherBuilder::new()
        .binary_detection(BinaryDetection::quit(b'\x00'))
        .line_number(true)
        .build();
    let walker = ignore::WalkBuilder::new(root)
        .hidden(false)
        .git_ignore(true)
        .git_exclude(true)
        .git_global(false)
        .filter_entry(|entry| entry.file_name() != ".git")
        .build();
    let mut hits: Vec<SearchHit> = Vec::new();
    for item in walker.flatten() {
        if hits.len() >= limit {
            break;
        }
        let path = item.path();
        if !item.file_type().map(|t| t.is_file()).unwrap_or(false) {
            continue;
        }
        if item.metadata().map(|m| m.len()).unwrap_or(0) > SEARCH_MAX_FILE {
            continue;
        }
        let relative = relative_slash(root, path);
        let result = searcher.search_path(
            &matcher,
            path,
            UTF8(|line_number, line| {
                let column = matcher
                    .find(line.as_bytes())
                    .ok()
                    .flatten()
                    .map(|m| m.start())
                    .unwrap_or(0);
                hits.push(SearchHit {
                    path: relative.clone(),
                    line: line_number,
                    column,
                    text: line
                        .trim_end_matches(['\n', '\r'])
                        .chars()
                        .take(400)
                        .collect(),
                });
                Ok(hits.len() < limit)
            }),
        );
        // Unlesbare Dateien überspringen, nicht die Suche abbrechen.
        let _ = result;
    }
    Ok(hits)
}

/// Volltextsuche im Projekt (ripgrep-Bausteine, .gitignore gilt, .git bleibt zu).
#[tauri::command]
pub fn project_search(
    project: String,
    query: String,
    regex: bool,
    case_sensitive: bool,
    limit: u32,
) -> Result<Vec<SearchHit>, String> {
    let root = resolve_project_root(&project)?;
    search_tree(
        &root,
        &query,
        regex,
        case_sensitive,
        limit.clamp(1, 2000) as usize,
    )
}

/// Datei (leer) oder Ordner anlegen — nie über Bestehendes.
#[tauri::command]
pub fn project_file_create(project: String, path: String, is_dir: bool) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    let target = safe_project_path(&root, &path)?;
    if target.exists() {
        return Err(format!("Gibt es schon: {path}"));
    }
    if is_dir {
        std::fs::create_dir_all(&target).map_err(|e| format!("{path}: {e}"))?;
    } else {
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
        }
        std::fs::write(&target, b"").map_err(|e| format!("{path}: {e}"))?;
    }
    Ok(relative_slash(&root, &target))
}

/// Umbenennen/Verschieben innerhalb des Projekts — nie über Bestehendes.
#[tauri::command]
pub fn project_file_rename(project: String, from: String, to: String) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    let source = safe_project_path(&root, &from)?;
    let target = safe_project_path(&root, &to)?;
    if !source.exists() {
        return Err(format!("Gibt es nicht: {from}"));
    }
    if target.exists() {
        return Err(format!("Gibt es schon: {to}"));
    }
    if let Some(parent) = target.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    std::fs::rename(&source, &target).map_err(|e| format!("{from} → {to}: {e}"))?;
    Ok(relative_slash(&root, &target))
}

/// In den Papierkorb — kein endgültiges Löschen aus der App heraus.
#[tauri::command]
pub fn project_file_delete(project: String, path: String) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let target = safe_project_path(&root, &path)?;
    if !target.exists() {
        return Err(format!("Gibt es nicht: {path}"));
    }
    trash::delete(&target).map_err(|e| format!("{path}: {e}"))
}

#[derive(Serialize)]
pub struct FileInfo {
    pub path: String,
    pub size: u64,
    pub modified: Option<String>,
    /// Zeilen, nur für Textdateien bis 5 MB.
    pub lines: Option<usize>,
    pub binary: bool,
}

fn looks_binary(path: &Path) -> bool {
    use std::io::Read;
    let mut head = [0u8; 8192];
    match std::fs::File::open(path).and_then(|mut file| file.read(&mut head)) {
        Ok(read) => head[..read].contains(&0),
        Err(_) => false,
    }
}

#[tauri::command]
pub fn project_file_info(project: String, file: String) -> Result<FileInfo, String> {
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    let metadata = std::fs::metadata(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    let modified = metadata.modified().ok().and_then(|time| {
        let stamp = time::OffsetDateTime::from(time);
        stamp
            .format(&time::format_description::well_known::Rfc3339)
            .ok()
    });
    let binary = metadata.is_file() && looks_binary(&path);
    let lines = if !binary && metadata.len() <= 5 * 1024 * 1024 {
        std::fs::read_to_string(&path)
            .ok()
            .map(|text| text.lines().count())
    } else {
        None
    };
    Ok(FileInfo {
        path: file,
        size: metadata.len(),
        modified,
        lines,
        binary,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(test: &str) -> std::path::PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-files-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join(".git")).unwrap();
        std::fs::create_dir_all(dir.join("build")).unwrap();
        std::fs::create_dir_all(dir.join("src")).unwrap();
        std::fs::write(dir.join(".gitignore"), "build/\n").unwrap();
        std::fs::write(dir.join("build/out.bin"), [0u8, 1, 2]).unwrap();
        std::fs::write(dir.join("src/main.rs"), "fn main() {}\n").unwrap();
        std::fs::write(dir.join("README.md"), "# Hi\n\nText\n").unwrap();
        std::fs::write(dir.join("logo.bin"), [0u8, 255, 0]).unwrap();
        dir
    }

    #[test]
    fn tree_hides_git_and_ignored_and_sorts_dirs_first() {
        let dir = fixture("tree");
        let names: Vec<(String, bool)> = list_dir(&dir, "")
            .unwrap()
            .into_iter()
            .map(|entry| (entry.name, entry.is_dir))
            .collect();
        assert_eq!(
            names,
            vec![
                ("src".into(), true),
                (".gitignore".into(), false),
                ("logo.bin".into(), false),
                ("README.md".into(), false),
            ]
        );
        let src = list_dir(&dir, "src").unwrap();
        assert_eq!(src[0].path, "src/main.rs");
        assert!(list_dir(&dir, "../etc").is_err());
    }

    #[test]
    fn file_info_counts_lines_and_detects_binary() {
        let dir = fixture("info");
        let project = dir.to_string_lossy().into_owned();
        let readme = project_file_info(project.clone(), "README.md".into()).unwrap();
        assert_eq!(readme.lines, Some(3));
        assert!(!readme.binary);
        assert!(readme.modified.is_some());
        let logo = project_file_info(project, "logo.bin".into()).unwrap();
        assert!(logo.binary);
        assert_eq!(logo.lines, None);
    }

    #[test]
    fn search_respects_gitignore_and_reports_line_and_column() {
        let dir = fixture("search");
        std::fs::write(
            dir.join("src/a.rs"),
            "fn main() {\n    let Needle = 1;\n}\n",
        )
        .unwrap();
        std::fs::write(dir.join("build/needle.txt"), "needle\n").unwrap();
        std::fs::write(
            dir.join("notes.md"),
            "# needle\nkein treffer\nNEEDLE again\n",
        )
        .unwrap();
        let hits = search_tree(&dir, "needle", false, false, 100).unwrap();
        let mut paths: Vec<String> = hits
            .iter()
            .map(|h| format!("{}:{}", h.path, h.line))
            .collect();
        paths.sort();
        assert_eq!(paths, vec!["notes.md:1", "notes.md:3", "src/a.rs:2"]);
        let hit = hits.iter().find(|h| h.path == "src/a.rs").unwrap();
        assert_eq!(hit.column, 8);
        assert_eq!(hit.text, "    let Needle = 1;");
        // Groß/klein, Regex, Limit.
        assert_eq!(
            search_tree(&dir, "Needle", false, true, 100).unwrap().len(),
            1
        );
        assert_eq!(
            search_tree(&dir, "^#\\s+nee", true, true, 100)
                .unwrap()
                .len(),
            1
        );
        assert_eq!(
            search_tree(&dir, "needle", false, false, 2).unwrap().len(),
            2
        );
        assert!(search_tree(&dir, "(", true, true, 10).is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn create_and_rename_never_overwrite() {
        let dir = fixture("create");
        let project = dir.to_string_lossy().into_owned();
        assert_eq!(
            project_file_create(project.clone(), "docs/neu.md".into(), false).unwrap(),
            "docs/neu.md"
        );
        assert!(dir.join("docs/neu.md").is_file());
        assert!(project_file_create(project.clone(), "docs/neu.md".into(), false).is_err());
        project_file_create(project.clone(), "assets/img".into(), true).unwrap();
        assert!(dir.join("assets/img").is_dir());
        assert_eq!(
            project_file_rename(
                project.clone(),
                "docs/neu.md".into(),
                "docs/alt/neu.md".into()
            )
            .unwrap(),
            "docs/alt/neu.md"
        );
        assert!(!dir.join("docs/neu.md").exists());
        assert!(dir.join("docs/alt/neu.md").is_file());
        std::fs::write(dir.join("docs/x.md"), "x").unwrap();
        assert!(project_file_rename(
            project.clone(),
            "docs/alt/neu.md".into(),
            "docs/x.md".into()
        )
        .is_err());
        assert!(
            project_file_rename(project.clone(), "docs/x.md".into(), "../raus.md".into()).is_err()
        );
        // Löschen geht in den Papierkorb — im Test nicht ausgeführt (würde den
        // Papierkorb des Entwicklers füllen); der Guard greift trotzdem:
        assert!(project_file_delete(project, "gibts-nicht.md".into()).is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }
}
