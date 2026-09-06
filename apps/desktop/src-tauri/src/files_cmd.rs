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
}
