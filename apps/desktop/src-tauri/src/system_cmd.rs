//! Umgebungs-Diagnose, Python-Verwaltung und Knowledgebase-Liste — nativer
//! Ersatz der letzten dotagent-CLI-Aufrufe (Rust-Plan R3). JSON-Formate
//! bleiben 1:1 wie `dotagent doctor|python list|kb kbs --json`, damit die
//! Views nur die Datenquelle wechseln.

use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;

use serde::Serialize;
use serde_json::{json, Value};
use wait_timeout::ChildExt;

// --- Doctor --------------------------------------------------------------------

struct DoctorCheckDef {
    name: &'static str,
    binary: &'static str,
    hint: &'static str,
}

/// Prüf-Liste (aus dotagent übernommen, bereinigt: pipx/dotagent raus,
/// beide unterstützten Terminal-Agents rein).
const CHECKS: &[DoctorCheckDef] = &[
    DoctorCheckDef {
        name: "Python",
        binary: "python3",
        hint: "brew install python",
    },
    DoctorCheckDef {
        name: "uv",
        binary: "uv",
        hint: "brew install uv",
    },
    DoctorCheckDef {
        name: "Node.js",
        binary: "node",
        hint: "brew install node",
    },
    DoctorCheckDef {
        name: "npm",
        binary: "npm",
        hint: "wird mit Node.js installiert",
    },
    DoctorCheckDef {
        name: "Git",
        binary: "git",
        hint: "xcode-select --install",
    },
    DoctorCheckDef {
        name: "Rust (cargo)",
        binary: "cargo",
        hint: "brew install rustup && rustup default stable",
    },
    DoctorCheckDef {
        name: "Claude Code",
        binary: "claude",
        hint: "npm install -g @anthropic-ai/claude-code",
    },
    DoctorCheckDef {
        name: "OpenAI Codex",
        binary: "codex",
        hint: "npm install -g @openai/codex",
    },
    DoctorCheckDef {
        name: ".NET SDK",
        binary: "dotnet",
        hint: "im Parallels-Setup typischerweise nur in der VM nötig",
    },
    DoctorCheckDef {
        name: "Parallels CLI",
        binary: "prlctl",
        hint: "Parallels Desktop Pro/Business installieren",
    },
];

/// Bekannte Install-Orte jenseits des (bei GUI-Starts minimalen) PATH.
fn search_dirs() -> Vec<PathBuf> {
    let home = std::env::var("HOME").unwrap_or_default();
    let known = [
        "/opt/homebrew/bin".to_string(),
        "/opt/homebrew/opt/rustup/bin".to_string(),
        "/usr/local/bin".to_string(),
        format!("{home}/.local/bin"),
        format!("{home}/.cargo/bin"),
        format!("{home}/.dotnet"),
    ];
    let mut seen = HashSet::new();
    let mut result = Vec::new();
    let path = std::env::var_os("PATH").unwrap_or_default();
    // Zuerst das App-Bundle: dort liegt das mitgelieferte `uv` (R5.2), mit dem
    // die Engine gebaut wird — sonst meldete der Doctor „uv fehlt", obwohl die
    // App eins dabei hat.
    for dir in crate::sidecar::bundle_dir()
        .into_iter()
        .chain(std::env::split_paths(&path))
        .chain(known.iter().map(PathBuf::from))
    {
        if seen.insert(dir.clone()) {
            result.push(dir);
        }
    }
    result
}

fn joined_search_path() -> std::ffi::OsString {
    std::env::join_paths(search_dirs()).unwrap_or_default()
}

/// Alle ausführbaren Fundorte eines Binaries — dedupliziert nach
/// aufgelöstem Ziel (Symlink-Ketten zählen nur einmal).
fn find_all(binary: &str) -> Vec<PathBuf> {
    let mut resolved_seen = HashSet::new();
    let mut found = Vec::new();
    for dir in search_dirs() {
        // Windows: `git` liegt als `git.exe` auf der Platte (PATHEXT).
        let Some(candidate) = crate::sidecar::find_in_dir(&dir, binary) else {
            continue;
        };
        let resolved = candidate
            .canonicalize()
            .unwrap_or_else(|_| candidate.clone());
        if resolved_seen.insert(resolved) {
            found.push(candidate);
        }
    }
    // Der gebündelte uv heißt `speccify-uv` (siehe sidecar::resolve_uv) und
    // zählt für den Doctor als vorhandenes uv.
    if binary == "uv" {
        if let (Some(bundled), _) = crate::sidecar::resolve("speccify-uv") {
            let resolved = bundled.canonicalize().unwrap_or_else(|_| bundled.clone());
            if resolved_seen.insert(resolved) {
                found.push(bundled);
            }
        }
    }
    found
}

/// `<binary> --version` mit Timeout; erste Ausgabezeile (stdout, sonst stderr).
fn probe_version_line(path: &Path) -> Option<String> {
    let mut child = Command::new(path)
        .arg("--version")
        .env("PATH", joined_search_path())
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .ok()?;
    let mut stdout = child.stdout.take();
    let mut stderr = child.stderr.take();
    let out_handle = std::thread::spawn(move || read_lossy(stdout.as_mut()));
    let err_handle = std::thread::spawn(move || read_lossy(stderr.as_mut()));
    match child.wait_timeout(Duration::from_secs(10)) {
        Ok(Some(_)) => {}
        _ => {
            let _ = child.kill();
            let _ = child.wait();
            return None;
        }
    }
    let output = {
        let out = out_handle.join().unwrap_or_default();
        if out.trim().is_empty() {
            err_handle.join().unwrap_or_default()
        } else {
            out
        }
    };
    output
        .lines()
        .next()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .map(String::from)
}

fn read_lossy<R: std::io::Read>(reader: Option<&mut R>) -> String {
    let mut buffer = Vec::new();
    if let Some(reader) = reader {
        let _ = reader.read_to_end(&mut buffer);
    }
    String::from_utf8_lossy(&buffer).into_owned()
}

/// Erste Versionsnummer (`\d+(\.\d+)+`) aus einer Zeile.
fn extract_version(line: &str) -> Option<String> {
    let bytes = line.as_bytes();
    let mut start = 0;
    while start < bytes.len() {
        if bytes[start].is_ascii_digit() {
            let mut end = start;
            let mut dots = 0;
            while end < bytes.len() && (bytes[end].is_ascii_digit() || bytes[end] == b'.') {
                if bytes[end] == b'.' {
                    // kein Punkt am Ende / doppelt
                    if end + 1 >= bytes.len() || !bytes[end + 1].is_ascii_digit() {
                        break;
                    }
                    dots += 1;
                }
                end += 1;
            }
            if dots >= 1 {
                return Some(line[start..end].to_string());
            }
            start = end + 1;
        } else {
            start += 1;
        }
    }
    None
}

fn probe_candidates(paths: Vec<PathBuf>) -> Vec<Value> {
    // Parallel proben (I/O-gebunden) — sequenziell kostete der volle
    // Doctor-Lauf ~2 s (dotagent-Erfahrungswert).
    let handles: Vec<_> = paths
        .into_iter()
        .map(|path| {
            std::thread::spawn(move || {
                let version = probe_version_line(&path)
                    .as_deref()
                    .and_then(extract_version);
                json!({"path": path.display().to_string(), "version": version})
            })
        })
        .collect();
    handles
        .into_iter()
        .filter_map(|handle| handle.join().ok())
        .collect()
}

#[derive(Serialize)]
pub struct DoctorReport {
    checks: Vec<Value>,
}

#[tauri::command]
pub fn doctor() -> DoctorReport {
    let handles: Vec<_> = CHECKS
        .iter()
        .map(|check| {
            let (name, binary, hint) = (check.name, check.binary, check.hint);
            std::thread::spawn(move || {
                let candidates = probe_candidates(find_all(binary));
                let first = candidates.first();
                json!({
                    "name": name,
                    "binary": binary,
                    "found": !candidates.is_empty(),
                    "path": first.and_then(|c| c.get("path")).cloned().unwrap_or(Value::Null),
                    "version": first.and_then(|c| c.get("version")).cloned().unwrap_or(Value::Null),
                    "hint": hint,
                    "candidates": candidates,
                })
            })
        })
        .collect();
    DoctorReport {
        checks: handles
            .into_iter()
            .filter_map(|handle| handle.join().ok())
            .collect(),
    }
}

// --- Python-Verwaltung (via uv) --------------------------------------------------

const INSTALLABLE_MINORS: &[&str] = &["3.11", "3.12", "3.13", "3.14"];

#[tauri::command]
pub fn python_list() -> Value {
    let names: Vec<String> = std::iter::once("python3".to_string())
        .chain(
            ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]
                .iter()
                .map(|minor| format!("python{minor}")),
        )
        .collect();

    let mut resolved_seen = HashSet::new();
    let mut paths = Vec::new();
    for name in &names {
        for path in find_all(name) {
            let resolved = path.canonicalize().unwrap_or_else(|_| path.clone());
            if resolved_seen.insert(resolved) {
                paths.push(path);
            }
        }
    }
    let mut installed = probe_candidates(paths);
    installed.sort_by(|a, b| {
        let version_of = |value: &Value| {
            value
                .get("version")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_string()
        };
        version_of(b).cmp(&version_of(a))
    });

    let installed_minors: HashSet<String> = installed
        .iter()
        .filter_map(|candidate| candidate.get("version").and_then(Value::as_str))
        .map(|version| version.split('.').take(2).collect::<Vec<_>>().join("."))
        .collect();
    let available: Vec<&str> = INSTALLABLE_MINORS
        .iter()
        .copied()
        .filter(|minor| !installed_minors.contains(*minor))
        .collect();

    json!({
        "installed": installed,
        "available": available,
        "uv": !find_all("uv").is_empty(),
    })
}

#[tauri::command]
pub fn python_install(version: String) -> Result<Value, String> {
    if !INSTALLABLE_MINORS.contains(&version.as_str()) {
        return Err(format!(
            "Nicht unterstützte Version: {version} (verfügbar: {})",
            INSTALLABLE_MINORS.join(", ")
        ));
    }
    let uv = find_all("uv")
        .into_iter()
        .next()
        .ok_or("uv nicht gefunden — Installation: brew install uv")?;
    let output = Command::new(uv)
        .args(["python", "install", &version])
        .env("PATH", joined_search_path())
        .output()
        .map_err(|e| format!("uv: {e}"))?;
    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).into_owned());
    }
    Ok(json!({
        "exit_code": output.status.code(),
        "stdout": String::from_utf8_lossy(&output.stdout),
        "stderr": String::from_utf8_lossy(&output.stderr),
    }))
}

// --- Knowledgebases ---------------------------------------------------------------

/// Öffnbaren Pfad eines Buchs finden: Original-EPUB/PDF unter
/// `<base>/books/<kb>/`, sonst das extrahierte Markdown.
fn resolve_book_path(base: &Path, kb_name: &str, md_file: &str) -> Option<String> {
    let stem = Path::new(md_file)
        .file_stem()
        .map(|stem| stem.to_string_lossy().into_owned())?;
    for ext in ["pdf", "epub"] {
        let candidate = base
            .join("books")
            .join(kb_name)
            .join(format!("{stem}.{ext}"));
        if candidate.exists() {
            return Some(candidate.display().to_string());
        }
    }
    let markdown = base.join(kb_name).join("markdown").join(md_file);
    markdown.exists().then(|| markdown.display().to_string())
}

#[tauri::command]
pub fn kb_list() -> Value {
    let base = std::env::var("HOME")
        .map(|home| PathBuf::from(home).join("Knowledgebase"))
        .unwrap_or_default();
    let mut knowledgebases = Vec::new();

    let entries = std::fs::read_dir(&base).ok();
    let mut dirs: Vec<PathBuf> = entries
        .into_iter()
        .flatten()
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.is_dir())
        .collect();
    dirs.sort();

    for dir in dirs {
        let name = dir
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_default();
        let chunks_path = dir.join("data").join("chunks.json");
        let Ok(text) = std::fs::read_to_string(&chunks_path) else {
            continue;
        };
        let Ok(Value::Array(chunks)) = serde_json::from_str::<Value>(&text) else {
            continue;
        };

        // book_file → Titel (Erst-Vorkommen zählt, wie die Referenz).
        let mut books: Vec<(String, String)> = Vec::new();
        let mut seen_files = HashSet::new();
        for chunk in &chunks {
            let file = chunk.get("book_file").and_then(Value::as_str).unwrap_or("");
            let title = chunk.get("book").and_then(Value::as_str).unwrap_or("");
            if !file.is_empty() && seen_files.insert(file.to_string()) {
                books.push((file.to_string(), title.to_string()));
            }
        }
        let mut book_titles: Vec<String> = books.iter().map(|(_, title)| title.clone()).collect();
        book_titles.sort();
        let mut book_entries: Vec<Value> = books
            .iter()
            .map(|(file, title)| {
                json!({
                    "title": title,
                    "file": file,
                    "path": resolve_book_path(&base, &name, file),
                })
            })
            .collect();
        book_entries.sort_by(|a, b| {
            let title = |value: &Value| {
                value
                    .get("title")
                    .and_then(Value::as_str)
                    .unwrap_or("")
                    .to_string()
            };
            title(a).cmp(&title(b))
        });

        let index_size_mb = std::fs::metadata(dir.join("data").join("faiss.index"))
            .map(|meta| (meta.len() as f64 / 1024.0 / 1024.0 * 10.0).round() / 10.0)
            .unwrap_or(0.0);

        knowledgebases.push(json!({
            "name": name,
            "path": dir.display().to_string(),
            "books": book_titles.len(),
            "chunks": chunks.len(),
            "index_size_mb": index_size_mb,
            "book_titles": book_titles,
            "book_entries": book_entries,
        }));
    }

    json!({"knowledgebases": knowledgebases, "base_dir": base.display().to_string()})
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Das App-Bundle muss vor dem PATH gesucht werden — sonst gewinnt ein
    /// altes `uv` aus /opt/homebrew über das mitgelieferte (R5.2).
    #[test]
    fn bundle_dir_is_searched_first() {
        let dirs = search_dirs();
        if let Some(bundle) = crate::sidecar::bundle_dir() {
            assert_eq!(dirs.first(), Some(&bundle));
        }
        // Keine Duplikate — sonst tauchen Fundorte doppelt im Doctor auf.
        let unique: HashSet<_> = dirs.iter().collect();
        assert_eq!(unique.len(), dirs.len());
    }

    #[test]
    fn version_extraction() {
        assert_eq!(extract_version("Python 3.12.4"), Some("3.12.4".into()));
        assert_eq!(extract_version("git version 2.44.0"), Some("2.44.0".into()));
        assert_eq!(extract_version("v20.11.1"), Some("20.11.1".into()));
        assert_eq!(extract_version("keine version"), None);
        assert_eq!(extract_version("nur 7 hier"), None);
    }

    #[test]
    fn doctor_finds_git_on_dev_machines() {
        let report = doctor();
        let git = report
            .checks
            .iter()
            .find(|check| check["binary"] == "git")
            .unwrap();
        assert_eq!(git["found"], true);
        assert!(git["version"].is_string());
    }

    /// Paritäts-Check gegen die dotagent-Referenz (nur manuell:
    /// `cargo test -p speccify-desktop -- --ignored`); stirbt mit der
    /// Archivierung von dotagent.
    #[test]
    #[ignore]
    fn kb_list_matches_dotagent_reference() {
        let home = std::env::var("HOME").unwrap();
        let output = Command::new(format!(
            "{home}/Desktop/Work/Articles/dotagent/.venv/bin/dotagent"
        ))
        .args(["kb", "kbs", "--json"])
        .output()
        .expect("dotagent-Referenz nicht ausführbar");
        let reference: Value = serde_json::from_slice(&output.stdout).unwrap();
        let native = kb_list();

        let by_name = |value: &Value| -> Vec<(String, u64, u64, String)> {
            value["knowledgebases"]
                .as_array()
                .unwrap()
                .iter()
                .map(|kb| {
                    (
                        kb["name"].as_str().unwrap().to_string(),
                        kb["books"].as_u64().unwrap(),
                        kb["chunks"].as_u64().unwrap(),
                        kb["book_titles"].to_string(),
                    )
                })
                .collect()
        };
        assert_eq!(by_name(&reference), by_name(&native));
    }

    #[test]
    fn kb_list_shape_is_stable() {
        let result = kb_list();
        assert!(result.get("base_dir").is_some());
        let kbs = result["knowledgebases"].as_array().unwrap();
        for kb in kbs {
            assert!(kb["books"].as_u64().is_some());
            assert!(kb["chunks"].as_u64().is_some());
            assert!(kb["book_entries"].is_array());
        }
    }
}
