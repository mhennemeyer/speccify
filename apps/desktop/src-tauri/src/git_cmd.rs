//! Git fürs Projektfenster (Plan ide-im-projektfenster.md, I2/E1): über
//! das **System-`git`**, nicht libgit2 — Credentials laufen dann über die
//! vorhandenen Helper (Keychain, Credential Manager, SSH-Agent). Alle
//! Aufrufe: argv ohne Shell, cwd = Projektwurzel, `GIT_TERMINAL_PROMPT=0`
//! (nie hängen bleiben), maschinenlesbare Formate (`--porcelain=v2 -z`,
//! `--format` mit Unit Separator). Pull/Push mit Live-Ausgabe laufen über
//! die Aktions-Mechanik (`project_action_run`), nicht hier.

use std::path::Path;
use std::process::{Command, Stdio};
use std::time::Duration;

use serde::Serialize;
use wait_timeout::ChildExt;

use crate::project_cmd::resolve_project_root;

const GIT_TIMEOUT: Duration = Duration::from_secs(30);

struct GitOutput {
    code: i32,
    stdout: Vec<u8>,
    stderr: String,
}

fn git(root: &Path, args: &[&str]) -> Result<GitOutput, String> {
    let mut command = Command::new("git");
    command
        .args(args)
        .current_dir(root)
        .env("GIT_TERMINAL_PROMPT", "0")
        .env("LC_ALL", "C")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }
    let mut child = command
        .spawn()
        .map_err(|e| format!("git nicht startbar ({e}) — ist Git installiert und im PATH?"))?;
    let stdout_pipe = child.stdout.take();
    let stderr_pipe = child.stderr.take();
    let reader = std::thread::spawn(move || {
        use std::io::Read;
        let mut out = Vec::new();
        let mut err = String::new();
        if let Some(mut pipe) = stdout_pipe {
            let _ = pipe.read_to_end(&mut out);
        }
        if let Some(mut pipe) = stderr_pipe {
            let _ = pipe.read_to_string(&mut err);
        }
        (out, err)
    });
    let status = match child.wait_timeout(GIT_TIMEOUT).map_err(|e| e.to_string())? {
        Some(status) => status,
        None => {
            let _ = child.kill();
            let _ = child.wait();
            return Err(format!(
                "git {} hat nach 30 s nicht geantwortet.",
                args.join(" ")
            ));
        }
    };
    let (stdout, stderr) = reader
        .join()
        .map_err(|_| "git-Ausgabe verloren".to_string())?;
    Ok(GitOutput {
        code: status.code().unwrap_or(-1),
        stdout,
        stderr,
    })
}

fn git_ok(root: &Path, args: &[&str]) -> Result<String, String> {
    let output = git(root, args)?;
    if output.code != 0 {
        let message = output.stderr.trim();
        return Err(if message.is_empty() {
            format!("git {} → Exit {}", args.join(" "), output.code)
        } else {
            message.to_string()
        });
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

// --- Status --------------------------------------------------------------------

#[derive(Serialize, Debug, Clone, PartialEq)]
pub struct GitEntry {
    pub path: String,
    /// Index-Zustand (`M`, `A`, `D`, `R`, `C`, `U`) oder `.`
    pub index: String,
    /// Working-Tree-Zustand oder `.`
    pub worktree: String,
    pub untracked: bool,
    pub conflicted: bool,
    /// Bei Umbenennung: der alte Pfad.
    pub renamed_from: Option<String>,
}

#[derive(Serialize, Debug, Default, PartialEq)]
pub struct GitStatus {
    pub repo: bool,
    pub branch: Option<String>,
    pub upstream: Option<String>,
    pub ahead: i64,
    pub behind: i64,
    pub entries: Vec<GitEntry>,
    pub error: Option<String>,
}

/// `git status --porcelain=v2 --branch -z` parsen. Öffentlich fürs Testen.
pub(crate) fn parse_status_v2(raw: &[u8]) -> GitStatus {
    let mut status = GitStatus {
        repo: true,
        ..Default::default()
    };
    let text = String::from_utf8_lossy(raw);
    let mut fields = text.split('\0').peekable();
    while let Some(record) = fields.next() {
        if record.is_empty() {
            continue;
        }
        if let Some(rest) = record.strip_prefix("# branch.head ") {
            status.branch = (rest != "(detached)").then(|| rest.to_string());
        } else if let Some(rest) = record.strip_prefix("# branch.upstream ") {
            status.upstream = Some(rest.to_string());
        } else if let Some(rest) = record.strip_prefix("# branch.ab ") {
            let mut parts = rest.split(' ');
            status.ahead = parts
                .next()
                .and_then(|s| s.trim_start_matches('+').parse().ok())
                .unwrap_or(0);
            status.behind = parts
                .next()
                .and_then(|s| s.trim_start_matches('-').parse().ok())
                .unwrap_or(0);
        } else if let Some(rest) = record.strip_prefix("1 ") {
            // XY sub mH mI mW hH hI path — 8 Felder; der Pfad ist das letzte
            // und darf Leerzeichen enthalten (deshalb -z und exaktes splitn).
            let mut parts = rest.splitn(8, ' ');
            let xy = parts.next().unwrap_or("..");
            let path = parts.nth(6).unwrap_or("").to_string();
            status.entries.push(entry(xy, path, None));
        } else if let Some(rest) = record.strip_prefix("2 ") {
            // XY sub mH mI mW hH hI Xscore path\0origPath — 9 Felder
            let mut parts = rest.splitn(9, ' ');
            let xy = parts.next().unwrap_or("..");
            let path = parts.nth(7).unwrap_or("").to_string();
            let original = fields.next().map(|s| s.to_string());
            status.entries.push(entry(xy, path, original));
        } else if let Some(rest) = record.strip_prefix("u ") {
            // XY sub m1 m2 m3 mW h1 h2 h3 path — 10 Felder
            let mut parts = rest.splitn(10, ' ');
            let xy = parts.next().unwrap_or("UU");
            let path = parts.nth(8).unwrap_or("").to_string();
            let mut item = entry(xy, path, None);
            item.conflicted = true;
            status.entries.push(item);
        } else if let Some(rest) = record.strip_prefix("? ") {
            status.entries.push(GitEntry {
                path: rest.to_string(),
                index: ".".into(),
                worktree: "?".into(),
                untracked: true,
                conflicted: false,
                renamed_from: None,
            });
        }
    }
    status
}

fn entry(xy: &str, path: String, renamed_from: Option<String>) -> GitEntry {
    let mut chars = xy.chars();
    let index = chars.next().unwrap_or('.').to_string();
    let worktree = chars.next().unwrap_or('.').to_string();
    GitEntry {
        path,
        index,
        worktree,
        untracked: false,
        conflicted: false,
        renamed_from,
    }
}

#[tauri::command]
pub fn project_git_status(project: String) -> Result<GitStatus, String> {
    let root = resolve_project_root(&project)?;
    let inside = git(&root, &["rev-parse", "--is-inside-work-tree"])?;
    if inside.code != 0 {
        return Ok(GitStatus {
            repo: false,
            error: Some(inside.stderr.trim().to_string()),
            ..Default::default()
        });
    }
    let output = git(&root, &["status", "--porcelain=v2", "--branch", "-z"])?;
    if output.code != 0 {
        return Ok(GitStatus {
            repo: true,
            error: Some(output.stderr.trim().to_string()),
            ..Default::default()
        });
    }
    Ok(parse_status_v2(&output.stdout))
}

// --- Diff, Stage, Commit, Log ------------------------------------------------

#[tauri::command]
pub fn project_git_diff(project: String, path: String, staged: bool) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    let output = if staged {
        git(&root, &["diff", "--cached", "--no-color", "--", &path])?
    } else {
        git(&root, &["diff", "--no-color", "--", &path])?
    };
    if output.code != 0 {
        return Err(output.stderr.trim().to_string());
    }
    let text = String::from_utf8_lossy(&output.stdout).into_owned();
    if text.is_empty() && !staged {
        // Untracked: gegen „nichts" diffen. Exit 1 heißt hier „Unterschiede".
        let null = if cfg!(windows) { "NUL" } else { "/dev/null" };
        let raw = git(
            &root,
            &["diff", "--no-color", "--no-index", "--", null, &path],
        )?;
        return Ok(String::from_utf8_lossy(&raw.stdout).into_owned());
    }
    Ok(text)
}

#[tauri::command]
pub fn project_git_stage(project: String, paths: Vec<String>, stage: bool) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    if paths.is_empty() {
        return Ok(());
    }
    // Ohne ersten Commit gibt es kein HEAD — dann kann `restore --staged`
    // nichts wiederherstellen; `rm --cached` nimmt die Datei aus dem Index.
    let has_head = git(&root, &["rev-parse", "--verify", "-q", "HEAD"])?.code == 0;
    let mut args: Vec<&str> = if stage {
        vec!["add", "-A", "--"]
    } else if has_head {
        vec!["restore", "--staged", "--"]
    } else {
        vec!["rm", "--cached", "-r", "-q", "--"]
    };
    args.extend(paths.iter().map(String::as_str));
    match git_ok(&root, &args) {
        Ok(_) => Ok(()),
        // Ältere Git-Versionen ohne `restore` (< 2.23): reset als Rückfall.
        Err(message) if !stage && message.contains("is not a git command") => {
            let mut fallback = vec!["reset", "-q", "--"];
            fallback.extend(paths.iter().map(String::as_str));
            git_ok(&root, &fallback).map(|_| ())
        }
        Err(message) => Err(message),
    }
}

#[tauri::command]
pub fn project_git_commit(project: String, message: String) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    if message.trim().is_empty() {
        return Err("Commit-Nachricht fehlt.".into());
    }
    let output = git_ok(&root, &["commit", "-m", &message])?;
    Ok(output.lines().next().unwrap_or("").to_string())
}

#[derive(Serialize, Debug, PartialEq)]
pub struct GitCommit {
    pub hash: String,
    pub short: String,
    pub author: String,
    pub date: String,
    pub subject: String,
}

pub(crate) fn parse_log(text: &str) -> Vec<GitCommit> {
    text.lines()
        .filter_map(|line| {
            let mut parts = line.split('\u{1f}');
            Some(GitCommit {
                hash: parts.next()?.to_string(),
                short: parts.next()?.to_string(),
                author: parts.next()?.to_string(),
                date: parts.next()?.to_string(),
                subject: parts.next().unwrap_or("").to_string(),
            })
        })
        .collect()
}

#[tauri::command]
pub fn project_git_log(project: String, limit: u32) -> Result<Vec<GitCommit>, String> {
    let root = resolve_project_root(&project)?;
    let count = format!("-n{}", limit.clamp(1, 200));
    let output = git(
        &root,
        &["log", "--format=%H%x1f%h%x1f%an%x1f%aI%x1f%s", &count],
    )?;
    if output.code != 0 {
        // Frisches Repo ohne Commit: leeres Log statt Fehler.
        return Ok(Vec::new());
    }
    Ok(parse_log(&String::from_utf8_lossy(&output.stdout)))
}

#[tauri::command]
pub fn project_git_init(project: String) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    git_ok(&root, &["init"]).map(|out| out.trim().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_v2_parses_branch_entries_renames_and_untracked() {
        let raw = concat!(
            "# branch.oid abc\0# branch.head main\0# branch.upstream origin/main\0# branch.ab +2 -1\0",
            "1 .M N... 100644 100644 100644 h1 h2 README.md\0",
            "1 A. N... 000000 100644 100644 h0 h3 new.txt\0",
            "2 R. N... 100644 100644 100644 h1 h1 R100 neu.md\0alt.md\0",
            "u UU N... 100644 100644 100644 100644 h1 h2 h3 conflict.txt\0",
            "? notes/todo.md\0"
        );
        let status = parse_status_v2(raw.as_bytes());
        assert!(status.repo);
        assert_eq!(status.branch.as_deref(), Some("main"));
        assert_eq!(status.upstream.as_deref(), Some("origin/main"));
        assert_eq!((status.ahead, status.behind), (2, 1));
        assert_eq!(status.entries.len(), 5);
        assert_eq!(status.entries[0].path, "README.md");
        assert_eq!(status.entries[0].worktree, "M");
        assert_eq!(status.entries[1].index, "A");
        assert_eq!(status.entries[2].path, "neu.md");
        assert_eq!(status.entries[2].renamed_from.as_deref(), Some("alt.md"));
        assert!(status.entries[3].conflicted);
        assert!(status.entries[4].untracked);
        assert_eq!(status.entries[4].path, "notes/todo.md");
    }

    #[test]
    fn log_lines_split_on_unit_separator() {
        let text =
            "abc123\u{1f}abc\u{1f}Matthias\u{1f}2026-09-06T10:00:00+02:00\u{1f}feat: x\nkaputt\n";
        let log = parse_log(text);
        assert_eq!(log.len(), 1);
        assert_eq!(log[0].short, "abc");
        assert_eq!(log[0].subject, "feat: x");
    }

    #[test]
    fn real_git_roundtrip_in_temp_repo() {
        if Command::new("git").arg("--version").output().is_err() {
            return; // kein Git auf dem Runner
        }
        let dir = std::env::temp_dir().join(format!("speccify-git-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let project = dir.to_string_lossy().into_owned();
        let before = project_git_status(project.clone()).unwrap();
        assert!(!before.repo);
        project_git_init(project.clone()).unwrap();
        git_ok(&dir, &["config", "user.email", "t@example.com"]).unwrap();
        git_ok(&dir, &["config", "user.name", "Test"]).unwrap();
        std::fs::write(dir.join("a.txt"), "hallo\n").unwrap();
        let status = project_git_status(project.clone()).unwrap();
        assert!(status.repo);
        assert_eq!(status.entries.len(), 1);
        assert!(status.entries[0].untracked);
        let diff = project_git_diff(project.clone(), "a.txt".into(), false).unwrap();
        assert!(diff.contains("+hallo"));
        project_git_stage(project.clone(), vec!["a.txt".into()], true).unwrap();
        let staged = project_git_status(project.clone()).unwrap();
        assert_eq!(staged.entries[0].index, "A");
        project_git_stage(project.clone(), vec!["a.txt".into()], false).unwrap();
        assert!(project_git_status(project.clone()).unwrap().entries[0].untracked);
        project_git_stage(project.clone(), vec!["a.txt".into()], true).unwrap();
        let summary = project_git_commit(project.clone(), "erster".into()).unwrap();
        assert!(summary.contains("erster"));
        let log = project_git_log(project.clone(), 10).unwrap();
        assert_eq!(log.len(), 1);
        assert_eq!(log[0].subject, "erster");
        assert!(project_git_status(project).unwrap().entries.is_empty());
    }
}
