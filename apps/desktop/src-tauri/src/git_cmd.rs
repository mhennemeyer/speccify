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
    git_with_input(root, args, None)
}

/// Wie `git`, optional mit Text auf stdin (`git apply -` für Hunks).
fn git_with_input(root: &Path, args: &[&str], input: Option<&str>) -> Result<GitOutput, String> {
    let mut command = Command::new("git");
    command
        .args(args)
        .current_dir(root)
        .env("GIT_TERMINAL_PROMPT", "0")
        .env("LC_ALL", "C")
        .stdin(if input.is_some() {
            Stdio::piped()
        } else {
            Stdio::null()
        })
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
    if let Some(text) = input {
        if let Some(mut stdin) = child.stdin.take() {
            use std::io::Write;
            let _ = stdin.write_all(text.as_bytes());
            // stdin fällt hier zu — git liest EOF.
        }
    }
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
pub async fn project_git_status(project: String) -> Result<GitStatus, String> {
    tauri::async_runtime::spawn_blocking(move || read_git_status(project))
        .await
        .map_err(|error| error.to_string())?
}

fn read_git_status(project: String) -> Result<GitStatus, String> {
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
pub async fn project_git_log(project: String, limit: u32) -> Result<Vec<GitCommit>, String> {
    tauri::async_runtime::spawn_blocking(move || read_git_log(project, limit))
        .await
        .map_err(|error| error.to_string())?
}

fn read_git_log(project: String, limit: u32) -> Result<Vec<GitCommit>, String> {
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

// --- I3: Datei-Historie, Commit-Details, Hunks, Verwerfen, Branches ---------------

const LOG_FORMAT: &str = "--format=%H%x1f%h%x1f%an%x1f%aI%x1f%s";

/// Commits, die eine Datei berührt haben (folgt Umbenennungen).
#[tauri::command]
pub fn project_git_file_log(
    project: String,
    path: String,
    limit: u32,
) -> Result<Vec<GitCommit>, String> {
    let root = resolve_project_root(&project)?;
    let count = format!("-n{}", limit.clamp(1, 500));
    let output = git(&root, &["log", "--follow", LOG_FORMAT, &count, "--", &path])?;
    if output.code != 0 {
        return Ok(Vec::new());
    }
    Ok(parse_log(&String::from_utf8_lossy(&output.stdout)))
}

#[derive(Serialize, Debug, PartialEq)]
pub struct GitChangedFile {
    pub path: String,
    /// `M`, `A`, `D`, `R`, `C`, `T`
    pub status: String,
    pub renamed_from: Option<String>,
}

#[derive(Serialize, Debug)]
pub struct GitCommitDetail {
    pub hash: String,
    pub short: String,
    pub author: String,
    pub date: String,
    pub subject: String,
    pub body: String,
    pub files: Vec<GitChangedFile>,
}

pub(crate) fn parse_name_status(raw: &[u8]) -> Vec<GitChangedFile> {
    let text = String::from_utf8_lossy(raw);
    let mut fields = text.split('\0');
    let mut files = Vec::new();
    while let Some(status) = fields.next() {
        if status.is_empty() {
            continue;
        }
        let Some(path) = fields.next() else { break };
        let code = status.chars().next().unwrap_or('M').to_string();
        if code == "R" || code == "C" {
            let target = fields.next().unwrap_or("").to_string();
            files.push(GitChangedFile {
                path: target,
                status: code,
                renamed_from: Some(path.to_string()),
            });
        } else {
            files.push(GitChangedFile {
                path: path.to_string(),
                status: code,
                renamed_from: None,
            });
        }
    }
    files
}

/// Ein Commit mit Nachricht und geänderten Dateien (für den Inspektor).
#[tauri::command]
pub fn project_git_commit_detail(
    project: String,
    commit: String,
) -> Result<GitCommitDetail, String> {
    let root = resolve_project_root(&project)?;
    let meta = git_ok(
        &root,
        &[
            "show",
            "-s",
            "--format=%H%x1f%h%x1f%an%x1f%aI%x1f%s%x1f%b",
            &commit,
        ],
    )?;
    let mut parts = meta.trim_end_matches('\n').split('\u{1f}');
    let mut next = || parts.next().unwrap_or("").to_string();
    let (hash, short, author, date, subject) = (next(), next(), next(), next(), next());
    let body = next().trim().to_string();
    let files = git(
        &root,
        &["show", "--format=", "--name-status", "-z", "-M", &commit],
    )?;
    Ok(GitCommitDetail {
        hash,
        short,
        author,
        date,
        subject,
        body,
        files: parse_name_status(&files.stdout),
    })
}

/// Diff eines Commits — ganz oder für eine Datei.
#[tauri::command]
pub fn project_git_commit_diff(
    project: String,
    commit: String,
    path: Option<String>,
) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    let mut args = vec!["show", "--no-color", "--format=", "-M", commit.as_str()];
    if let Some(path) = path.as_deref() {
        args.extend(["--", path]);
    }
    git_ok(&root, &args)
}

/// Einen Patch (Diff-Kopf + ein Hunk, vom Frontend zusammengesetzt) in den
/// Index anwenden — `reverse` nimmt einen gestageten Hunk wieder heraus.
#[tauri::command]
pub fn project_git_apply_patch(
    project: String,
    patch: String,
    reverse: bool,
) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let mut args = vec!["apply", "--cached", "--whitespace=nowarn"];
    if reverse {
        args.push("--reverse");
    }
    args.push("-");
    let text = if patch.ends_with('\n') {
        patch
    } else {
        format!("{patch}\n")
    };
    let output = git_with_input(&root, &args, Some(&text))?;
    if output.code != 0 {
        return Err(output.stderr.trim().to_string());
    }
    Ok(())
}

/// Änderungen im Arbeitsbaum verwerfen: versionierte Dateien zurück auf den
/// Index-/HEAD-Stand, unversionierte löschen. Unumkehrbar — das Frontend fragt.
#[tauri::command]
pub fn project_git_discard(project: String, paths: Vec<String>) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    if paths.is_empty() {
        return Ok(());
    }
    let status = read_git_status(project)?;
    let untracked: Vec<&str> = status
        .entries
        .iter()
        .filter(|entry| entry.untracked && paths.contains(&entry.path))
        .map(|entry| entry.path.as_str())
        .collect();
    let tracked: Vec<&str> = paths
        .iter()
        .map(String::as_str)
        .filter(|path| !untracked.contains(path))
        .collect();
    if !tracked.is_empty() {
        let mut args = vec!["restore", "--worktree", "--"];
        args.extend(tracked.iter().copied());
        if let Err(message) = git_ok(&root, &args) {
            if !message.contains("is not a git command") {
                return Err(message);
            }
            let mut fallback = vec!["checkout", "--"];
            fallback.extend(tracked.iter().copied());
            git_ok(&root, &fallback)?;
        }
    }
    if !untracked.is_empty() {
        let mut args = vec!["clean", "-f", "-q", "--"];
        args.extend(untracked.iter().copied());
        git_ok(&root, &args)?;
    }
    Ok(())
}

#[derive(Serialize, Debug, PartialEq, Clone)]
pub struct BlameLine {
    pub line: u64,
    pub short: String,
    pub author: String,
    /// ISO-Datum (aus author-time), nur Tag.
    pub date: String,
    pub summary: String,
    /// Noch nicht committet (Hash aus Nullen).
    pub uncommitted: bool,
}

/// `git blame --line-porcelain` parsen: je Zeile ein Kopf `<hash> <orig> <final>
/// [n]`, dann Schlüssel-Zeilen, dann die Inhaltszeile mit Tab.
pub(crate) fn parse_blame(text: &str) -> Vec<BlameLine> {
    let mut out = Vec::new();
    let mut known: std::collections::HashMap<String, (String, String, String)> =
        std::collections::HashMap::new();
    let mut lines = text.lines().peekable();
    while let Some(head) = lines.next() {
        let mut parts = head.split(' ');
        let Some(hash) = parts.next() else { continue };
        if hash.len() < 7 || !hash.chars().all(|c| c.is_ascii_hexdigit()) {
            continue;
        }
        let final_line: u64 = parts.nth(1).and_then(|s| s.parse().ok()).unwrap_or(0);
        let mut author = String::new();
        let mut date = String::new();
        let mut summary = String::new();
        for line in lines.by_ref() {
            if line.starts_with('\t') {
                break;
            }
            if let Some(rest) = line.strip_prefix("author ") {
                author = rest.to_string();
            } else if let Some(rest) = line.strip_prefix("author-time ") {
                if let Ok(secs) = rest.parse::<i64>() {
                    date = time::OffsetDateTime::from_unix_timestamp(secs)
                        .map(|t| t.date().to_string())
                        .unwrap_or_default();
                }
            } else if let Some(rest) = line.strip_prefix("summary ") {
                summary = rest.to_string();
            }
        }
        // Wiederholte Commits nennen author/summary nicht noch einmal.
        if author.is_empty() {
            if let Some((a, d, s)) = known.get(hash) {
                author = a.clone();
                date = d.clone();
                summary = s.clone();
            }
        } else {
            known.insert(
                hash.to_string(),
                (author.clone(), date.clone(), summary.clone()),
            );
        }
        let uncommitted = hash.chars().all(|c| c == '0');
        out.push(BlameLine {
            line: final_line,
            short: hash[..7].to_string(),
            author: if uncommitted { "—".into() } else { author },
            date,
            summary: if uncommitted {
                "nicht committet".into()
            } else {
                summary
            },
            uncommitted,
        });
    }
    out
}

/// Blame je Zeile (Rand im Editor).
#[tauri::command]
pub fn project_git_blame(project: String, path: String) -> Result<Vec<BlameLine>, String> {
    let root = resolve_project_root(&project)?;
    let output = git(&root, &["blame", "--line-porcelain", "--", &path])?;
    if output.code != 0 {
        let message = output.stderr.trim();
        if message.contains("no such path") || message.contains("outside repository") {
            return Ok(Vec::new());
        }
        return Err(message.to_string());
    }
    Ok(parse_blame(&String::from_utf8_lossy(&output.stdout)))
}

#[derive(Serialize, Debug, PartialEq)]
pub struct GitBranch {
    pub name: String,
    pub current: bool,
    pub upstream: Option<String>,
    pub remote: bool,
    pub worktree: Option<String>,
}

#[tauri::command]
pub async fn project_git_branches(project: String) -> Result<Vec<GitBranch>, String> {
    tauri::async_runtime::spawn_blocking(move || read_git_branches(project))
        .await
        .map_err(|error| error.to_string())?
}

fn read_git_branches(project: String) -> Result<Vec<GitBranch>, String> {
    let root = resolve_project_root(&project)?;
    let output = git(
        &root,
        &[
            "for-each-ref",
            "--sort=refname",
            "--format=%(refname)%1f%(HEAD)%1f%(upstream:short)%1f%(symref)%1f%(worktreepath)",
            "refs/heads/",
            "refs/remotes/",
        ],
    )?;
    if output.code != 0 {
        return Err(output.stderr.trim().to_string());
    }
    Ok(String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| {
            let mut parts = line.split('\u{1f}');
            let reference = parts.next()?;
            let remote = reference.starts_with("refs/remotes/");
            let name = reference
                .strip_prefix(if remote {
                    "refs/remotes/"
                } else {
                    "refs/heads/"
                })?
                .to_string();
            let current = parts.next().unwrap_or("").trim() == "*";
            let upstream = parts
                .next()
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(String::from);
            if !parts.next().unwrap_or("").is_empty() {
                return None; // Remote-HEAD is a symbolic alias, not a branch.
            }
            let worktree = parts.next().filter(|s| !s.is_empty()).map(String::from);
            Some(GitBranch {
                name,
                current,
                upstream,
                remote,
                worktree,
            })
        })
        .collect())
}

fn validate_branch(root: &Path, name: &str) -> Result<(), String> {
    // Full refs reject revision shorthands such as @{-1}; reject argv options too.
    if name.is_empty()
        || name.starts_with('-')
        || name == "HEAD"
        || name.trim() != name
        || git(root, &["check-ref-format", &format!("refs/heads/{name}")])?.code != 0
    {
        return Err("Ungültiger lokaler Branch-Name.".into());
    }
    Ok(())
}

fn require_local_branch(root: &Path, name: &str) -> Result<(), String> {
    validate_branch(root, name)?;
    git_ok(
        root,
        &["show-ref", "--verify", &format!("refs/heads/{name}")],
    )?;
    Ok(())
}

#[tauri::command]
pub fn project_git_branch_rename(
    project: String,
    branch: String,
    name: String,
) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    require_local_branch(&root, &branch)?;
    validate_branch(&root, &name)?;
    if read_git_branches(project)?.iter().any(|entry| {
        !entry.remote && entry.name == branch && !entry.current && entry.worktree.is_some()
    }) {
        return Err("Branch ist in einem anderen Worktree geöffnet.".into());
    }
    // No -M: an existing destination is never overwritten.
    git_ok(&root, &["branch", "-m", "--", &branch, &name])?;
    Ok(format!("Branch {branch} → {name} umbenannt."))
}

#[tauri::command]
pub fn project_git_branch_delete(project: String, branch: String) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    require_local_branch(&root, &branch)?;
    let reference = format!("refs/heads/{branch}");
    if git_ok(&root, &["symbolic-ref", "-q", "HEAD"])
        .ok()
        .as_deref()
        .map(str::trim)
        == Some(reference.as_str())
    {
        return Err("Der aktuelle Branch kann nicht gelöscht werden.".into());
    }
    // `branch -d` alone can allow upstream-merged branches not merged into HEAD.
    if git(&root, &["merge-base", "--is-ancestor", &reference, "HEAD"])?.code != 0 {
        return Err(
            "Branch ist nicht vollständig in den aktuellen HEAD integriert. Kein Force-Delete."
                .into(),
        );
    }
    // Git additionally protects branches checked out in another worktree.
    git_ok(&root, &["branch", "-d", "--", &branch])?;
    Ok(format!(
        "Lokalen Branch {branch} gelöscht. Remote bleibt unverändert."
    ))
}

/// Branch wechseln oder (mit `create`) anlegen und wechseln.
#[tauri::command]
pub fn project_git_switch(project: String, branch: String, create: bool) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    let name = branch.as_str();
    validate_branch(&root, name)?;
    if !create {
        require_local_branch(&root, name)?;
    }
    let args: Vec<&str> = if create {
        vec!["switch", "--no-guess", "-c", name, "--"]
    } else {
        vec!["switch", "--no-guess", name, "--"]
    };
    match git_ok(&root, &args) {
        Ok(_) => Ok(name.to_string()),
        Err(message) if message.contains("is not a git command") => {
            let fallback: Vec<&str> = if create {
                vec!["checkout", "-b", name, "--"]
            } else {
                vec!["checkout", name, "--"]
            };
            git_ok(&root, &fallback).map(|_| name.to_string())
        }
        Err(message) => Err(message),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TestRepo(std::path::PathBuf);
    impl TestRepo {
        fn new() -> Self {
            let nonce = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos();
            let dir = std::env::temp_dir().join(format!(
                "speccify-git-workspace-{}-{nonce}",
                std::process::id()
            ));
            std::fs::create_dir(&dir).unwrap();
            let repo = Self(dir);
            project_git_init(repo.project()).unwrap();
            git_ok(&repo.0, &["config", "user.email", "test@example.com"]).unwrap();
            git_ok(&repo.0, &["config", "user.name", "Test"]).unwrap();
            git_ok(&repo.0, &["config", "commit.gpgsign", "false"]).unwrap();
            // Tests must not execute global/local hooks or depend on the user's default branch.
            std::fs::create_dir(repo.0.join("empty-hooks")).unwrap();
            git_ok(&repo.0, &["config", "core.hooksPath", "empty-hooks"]).unwrap();
            git_ok(&repo.0, &["symbolic-ref", "HEAD", "refs/heads/main"]).unwrap();
            std::fs::write(repo.0.join("tracked.txt"), "base\n").unwrap();
            project_git_stage(repo.project(), vec!["tracked.txt".into()], true).unwrap();
            project_git_commit(repo.project(), "initial".into()).unwrap();
            repo
        }
        fn project(&self) -> String {
            self.0.to_string_lossy().into_owned()
        }
    }
    impl Drop for TestRepo {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn git_workspace_commit_and_branches_are_scoped_and_safe() {
        let a = TestRepo::new();
        let b = TestRepo::new();
        let b_head = git_ok(&b.0, &["rev-parse", "HEAD"]).unwrap();
        std::fs::write(b.0.join("tracked.txt"), "b staged\n").unwrap();
        project_git_stage(b.project(), vec!["tracked.txt".into()], true).unwrap();
        std::fs::write(b.0.join("tracked.txt"), "b unstaged\n").unwrap();
        std::fs::write(b.0.join("untracked.txt"), "b private\n").unwrap();
        let b_status = git_ok(&b.0, &["status", "--porcelain=v2"]).unwrap();
        let b_diff = git_ok(&b.0, &["diff", "--cached"]).unwrap();
        std::fs::write(a.0.join("tracked.txt"), "a staged\n").unwrap();
        project_git_stage(a.project(), vec!["tracked.txt".into()], true).unwrap();
        std::fs::write(a.0.join("tracked.txt"), "a unstaged\n").unwrap();
        std::fs::write(a.0.join("untracked.txt"), "a private\n").unwrap();
        assert!(project_git_commit(a.project(), "  \n".into()).is_err());
        project_git_commit(
            a.project(),
            "feat: scoped\n\nDetailed body\nsecond line".into(),
        )
        .unwrap();
        assert_eq!(
            git_ok(&a.0, &["show", "HEAD:tracked.txt"]).unwrap(),
            "a staged\n"
        );
        assert_eq!(
            std::fs::read_to_string(a.0.join("tracked.txt")).unwrap(),
            "a unstaged\n"
        );
        assert!(read_git_status(a.project())
            .unwrap()
            .entries
            .iter()
            .any(|e| e.path == "untracked.txt" && e.untracked));
        assert!(git_ok(&a.0, &["log", "-1", "--format=%B"])
            .unwrap()
            .contains("Detailed body\nsecond line"));
        assert!(project_git_commit(a.project(), "no staged files".into()).is_err());
        // Feature diverges; switching back into its edited file must not discard work.
        project_git_switch(a.project(), "feature/safe".into(), true).unwrap();
        project_git_stage(a.project(), vec!["tracked.txt".into()], true).unwrap();
        project_git_commit(a.project(), "feature".into()).unwrap();
        project_git_switch(a.project(), "main".into(), false).unwrap();
        std::fs::write(a.0.join("tracked.txt"), "do not lose\n").unwrap();
        assert!(project_git_switch(a.project(), "feature/safe".into(), false).is_err());
        assert_eq!(
            std::fs::read_to_string(a.0.join("tracked.txt")).unwrap(),
            "do not lose\n"
        );
        assert_eq!(
            read_git_status(a.project()).unwrap().branch.as_deref(),
            Some("main")
        );
        assert!(git_ok(&a.0, &["stash", "list"]).unwrap().is_empty());
        assert!(project_git_branch_delete(a.project(), "main".into()).is_err());
        assert!(
            project_git_branch_delete(a.project(), "feature/safe".into())
                .unwrap_err()
                .contains("integriert")
        );
        project_git_branch_rename(a.project(), "feature/safe".into(), "feature/renamed".into())
            .unwrap();
        assert!(
            project_git_branch_rename(a.project(), "feature/renamed".into(), "main".into())
                .is_err()
        );
        git_ok(&a.0, &["branch", "merged"]).unwrap();
        project_git_branch_delete(a.project(), "merged".into()).unwrap();
        for invalid in [
            "--discard-changes",
            "-f",
            "@{-1}",
            "HEAD~1",
            "bad name",
            "HEAD",
            "",
        ] {
            assert!(
                project_git_switch(a.project(), invalid.into(), false).is_err(),
                "{invalid}"
            );
            assert!(
                project_git_switch(a.project(), invalid.into(), true).is_err(),
                "{invalid}"
            );
            assert!(
                project_git_branch_rename(a.project(), "main".into(), invalid.into()).is_err(),
                "{invalid}"
            );
            assert!(
                project_git_branch_delete(a.project(), invalid.into()).is_err(),
                "{invalid}"
            );
        }
        // Remote refs are display-only, with distinct identity and no synthetic HEAD row.
        git_ok(&a.0, &["update-ref", "refs/remotes/origin/main", "HEAD"]).unwrap();
        git_ok(
            &a.0,
            &[
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
                "refs/remotes/origin/main",
            ],
        )
        .unwrap();
        let branches = read_git_branches(a.project()).unwrap();
        assert!(branches.iter().any(|b| b.remote && b.name == "origin/main"));
        assert!(!branches.iter().any(|b| b.name == "origin/HEAD"));
        assert!(project_git_switch(a.project(), "origin/main".into(), false).is_err());
        assert!(project_git_branch_delete(a.project(), "origin/main".into()).is_err());
        // A branch checked out elsewhere is not a safe mutation target.
        let worktree = a.0.join("other-worktree");
        git_ok(
            &a.0,
            &[
                "worktree",
                "add",
                "-b",
                "occupied",
                worktree.to_str().unwrap(),
                "HEAD",
            ],
        )
        .unwrap();
        assert!(read_git_branches(a.project())
            .unwrap()
            .iter()
            .any(|b| b.name == "occupied" && b.worktree.is_some()));
        assert!(project_git_branch_delete(a.project(), "occupied".into()).is_err());
        assert!(project_git_branch_rename(a.project(), "occupied".into(), "moved".into()).is_err());
        assert!(project_git_switch(a.project(), "occupied".into(), false).is_err());
        assert_eq!(git_ok(&b.0, &["rev-parse", "HEAD"]).unwrap(), b_head);
        assert_eq!(
            git_ok(&b.0, &["status", "--porcelain=v2"]).unwrap(),
            b_status
        );
        assert_eq!(git_ok(&b.0, &["diff", "--cached"]).unwrap(), b_diff);
        assert_eq!(
            std::fs::read_to_string(b.0.join("tracked.txt")).unwrap(),
            "b unstaged\n"
        );
        assert_eq!(
            std::fs::read_to_string(b.0.join("untracked.txt")).unwrap(),
            "b private\n"
        );
    }

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
        let before = tauri::async_runtime::block_on(project_git_status(project.clone())).unwrap();
        assert!(!before.repo);
        project_git_init(project.clone()).unwrap();
        git_ok(&dir, &["config", "user.email", "t@example.com"]).unwrap();
        git_ok(&dir, &["config", "user.name", "Test"]).unwrap();
        std::fs::write(dir.join("a.txt"), "hallo\n").unwrap();
        let status = read_git_status(project.clone()).unwrap();
        assert!(status.repo);
        assert_eq!(status.entries.len(), 1);
        assert!(status.entries[0].untracked);
        let diff = project_git_diff(project.clone(), "a.txt".into(), false).unwrap();
        assert!(diff.contains("+hallo"));
        project_git_stage(project.clone(), vec!["a.txt".into()], true).unwrap();
        let staged = read_git_status(project.clone()).unwrap();
        assert_eq!(staged.entries[0].index, "A");
        project_git_stage(project.clone(), vec!["a.txt".into()], false).unwrap();
        assert!(read_git_status(project.clone()).unwrap().entries[0].untracked);
        project_git_stage(project.clone(), vec!["a.txt".into()], true).unwrap();
        let summary = project_git_commit(project.clone(), "erster".into()).unwrap();
        assert!(summary.contains("erster"));
        let log = tauri::async_runtime::block_on(project_git_log(project.clone(), 10)).unwrap();
        assert_eq!(log.len(), 1);
        assert_eq!(log[0].subject, "erster");
        assert!(read_git_status(project.clone()).unwrap().entries.is_empty());

        // I3: zwei getrennte Hunks, nur den ersten stagen.
        let lines: Vec<String> = (1..=12).map(|n| format!("zeile {n}")).collect();
        std::fs::write(dir.join("b.txt"), lines.join("\n") + "\n").unwrap();
        project_git_stage(project.clone(), vec!["b.txt".into()], true).unwrap();
        project_git_commit(project.clone(), "b".into()).unwrap();
        let mut changed = lines.clone();
        changed[0] = "ZEILE 1".into();
        changed[11] = "ZEILE 12".into();
        std::fs::write(dir.join("b.txt"), changed.join("\n") + "\n").unwrap();
        let diff = project_git_diff(project.clone(), "b.txt".into(), false).unwrap();
        let header_end = diff.find("@@").unwrap();
        let header = &diff[..header_end];
        let hunks: Vec<&str> = diff[header_end..].split_inclusive("\n@@").collect();
        assert_eq!(hunks.len(), 2, "{diff}");
        let first = hunks[0].trim_end_matches("@@");
        project_git_apply_patch(project.clone(), format!("{header}{first}"), false).unwrap();
        let status = read_git_status(project.clone()).unwrap();
        let entry = status.entries.iter().find(|e| e.path == "b.txt").unwrap();
        assert_eq!((entry.index.as_str(), entry.worktree.as_str()), ("M", "M"));
        // … und wieder heraus.
        project_git_apply_patch(project.clone(), format!("{header}{first}"), true).unwrap();
        let entry = read_git_status(project.clone()).unwrap().entries.remove(0);
        assert_eq!((entry.index.as_str(), entry.worktree.as_str()), (".", "M"));

        // Datei-Historie, Commit-Details, Diff eines Commits.
        let history = project_git_file_log(project.clone(), "b.txt".into(), 10).unwrap();
        assert_eq!(history.len(), 1);
        assert_eq!(history[0].subject, "b");
        let detail = project_git_commit_detail(project.clone(), history[0].hash.clone()).unwrap();
        assert_eq!(detail.subject, "b");
        assert_eq!(
            detail.files,
            vec![GitChangedFile {
                path: "b.txt".into(),
                status: "A".into(),
                renamed_from: None
            }]
        );
        let commit_diff = project_git_commit_diff(
            project.clone(),
            history[0].hash.clone(),
            Some("b.txt".into()),
        )
        .unwrap();
        assert!(commit_diff.contains("+zeile 1"));

        // Verwerfen: versioniert zurück, unversioniert weg.
        std::fs::write(dir.join("neu.txt"), "x\n").unwrap();
        project_git_discard(project.clone(), vec!["b.txt".into(), "neu.txt".into()]).unwrap();
        assert!(read_git_status(project.clone()).unwrap().entries.is_empty());
        assert!(!dir.join("neu.txt").exists());

        // Branches.
        let created = project_git_switch(project.clone(), "feature/x".into(), true).unwrap();
        assert_eq!(created, "feature/x");
        let branches =
            tauri::async_runtime::block_on(project_git_branches(project.clone())).unwrap();
        assert!(branches.iter().any(|b| b.name == "feature/x" && b.current));
        assert_eq!(branches.iter().filter(|b| b.current).count(), 1);
        let main = branches.iter().find(|b| !b.current).unwrap().name.clone();
        project_git_switch(project.clone(), main.clone(), false).unwrap();
        assert_eq!(
            read_git_status(project).unwrap().branch.as_deref(),
            Some(main.as_str())
        );
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn blame_porcelain_parses_lines_and_reuses_commit_details() {
        let text = concat!(
            "abc1234abc1234abc1234abc1234abc1234abc12 1 1 2\n",
            "author Matthias\nauthor-mail <m@example.com>\nauthor-time 1757152800\nauthor-tz +0200\n",
            "committer Matthias\ncommitter-mail <m@example.com>\ncommitter-time 1757152800\ncommitter-tz +0200\n",
            "summary feat: x\nfilename a.txt\n\tzeile eins\n",
            "abc1234abc1234abc1234abc1234abc1234abc12 2 2\n",
            "\tzeile zwei\n",
            "0000000000000000000000000000000000000000 3 3 1\n",
            "author Not Committed Yet\nauthor-mail <not.committed.yet>\nauthor-time 1757152800\nauthor-tz +0200\n",
            "committer Not Committed Yet\ncommitter-mail <not.committed.yet>\ncommitter-time 1757152800\ncommitter-tz +0200\n",
            "summary Version of a.txt from a.txt\nprevious abc1234abc1234abc1234abc1234abc1234abc12 a.txt\nfilename a.txt\n\tneu\n",
        );
        let blame = parse_blame(text);
        assert_eq!(blame.len(), 3);
        assert_eq!(blame[0].short, "abc1234");
        assert_eq!(blame[0].author, "Matthias");
        assert_eq!(blame[0].date, "2025-09-06");
        assert_eq!(blame[1].line, 2);
        assert_eq!(blame[1].summary, "feat: x");
        assert!(blame[2].uncommitted);
        assert_eq!(blame[2].summary, "nicht committet");
    }

    #[test]
    fn name_status_z_parses_renames() {
        let raw = b"M\0a.txt\0R100\0alt.md\0neu.md\0A\0x y.txt\0";
        let files = parse_name_status(raw);
        assert_eq!(files.len(), 3);
        assert_eq!(files[1].status, "R");
        assert_eq!(files[1].path, "neu.md");
        assert_eq!(files[1].renamed_from.as_deref(), Some("alt.md"));
        assert_eq!(files[2].path, "x y.txt");
    }
}
