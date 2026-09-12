//! Gemeinsames Spec-Register (Spec 028, D-TEAM-02): der Branch `specs` des
//! Code-Repositories liegt als Git-Worktree unter `.agent/specs`. Board und
//! Agenten arbeiten auf demselben Pfad wie bisher; Commits dort landen auf
//! `specs`, unabhängig vom ausgecheckten Code-Branch. Die App synchronisiert
//! (commit → fetch → rebase → push, nie Force). `history.jsonl` mergt per
//! `merge=union`; Konflikte in `SPEC.md` bleiben als gestoppter Rebase
//! sichtbar, bis eine Person entscheidet.

use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::git_cmd::{git, git_ok, git_ok_env, git_run};
use crate::project_cmd::resolve_project_root;

pub const BRANCH: &str = "specs";
const SPECS_DIR: &str = ".agent/specs";
const IGNORE_LINE: &str = ".agent/specs/";
const ATTRIBUTES: &str = "*.jsonl merge=union\n";

#[derive(Serialize, Clone, Debug, Default, PartialEq)]
pub struct RegisterConflict {
    pub file: String,
    pub spec_id: String,
    /// Stand des Teams (`origin/specs`, während des Rebase die Basis).
    pub team: String,
    /// Eigener Stand (der lokale Commit, der gerade eingespielt wird).
    pub mine: String,
}

#[derive(Serialize, Clone, Debug, Default, PartialEq)]
pub struct RegisterStatus {
    /// `none` (kein Register, lokale Specs im Code-Branch) · `migratable`
    /// (Repo mit Remote, `.agent/specs` im Code getrackt, noch kein Register) ·
    /// `detached` (Branch `specs` existiert, Worktree fehlt) · `blocked`
    /// (Register existiert, aber der Code-Branch trackt `.agent/specs` noch) ·
    /// `mounted` (Worktree eingehängt).
    pub mode: String,
    pub branch: String,
    pub remote: bool,
    pub code_branch: Option<String>,
    pub tracked_in_code: bool,
    pub ahead: u32,
    pub behind: u32,
    /// Geänderte, noch nicht committete Dateien im Register.
    pub unsent: u32,
    pub rebasing: bool,
    pub conflicts: Vec<RegisterConflict>,
    pub last_sync: Option<String>,
    pub last_error: Option<String>,
    /// Erklärung zum Zustand bzw. was „Einrichten“ tun würde.
    pub reason: Option<String>,
}

fn worktree_dir(root: &Path) -> PathBuf {
    root.join(SPECS_DIR)
}

/// Ein eingehängter Worktree trägt eine `.git`-Datei (gitdir-Verweis), kein
/// Verzeichnis.
pub(crate) fn is_mounted(root: &Path) -> bool {
    worktree_dir(root).join(".git").is_file()
}

fn is_repo(root: &Path) -> bool {
    git(root, &["rev-parse", "--is-inside-work-tree"])
        .map(|o| o.code == 0)
        .unwrap_or(false)
}

fn ref_exists(root: &Path, reference: &str) -> bool {
    git(root, &["rev-parse", "--verify", "--quiet", reference])
        .map(|o| o.code == 0)
        .unwrap_or(false)
}

fn has_origin(root: &Path) -> bool {
    git_ok(root, &["remote"])
        .map(|out| out.lines().any(|line| line.trim() == "origin"))
        .unwrap_or(false)
}

fn current_branch(root: &Path) -> Option<String> {
    git_ok(root, &["symbolic-ref", "--short", "-q", "HEAD"])
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

fn tracked_in_code(root: &Path) -> bool {
    git_ok(root, &["ls-files", "--", SPECS_DIR])
        .map(|out| !out.trim().is_empty())
        .unwrap_or(false)
}

fn dir_has_content(dir: &Path) -> bool {
    std::fs::read_dir(dir)
        .map(|mut entries| entries.next().is_some())
        .unwrap_or(false)
}

fn count_lines(text: &str) -> u32 {
    text.lines().filter(|l| !l.trim().is_empty()).count() as u32
}

fn now_iso() -> String {
    time::OffsetDateTime::now_utc()
        .format(&time::format_description::well_known::Rfc3339)
        .unwrap_or_default()
}

/// Zustand ohne Netzwerk (kein Fetch).
pub(crate) fn status(root: &Path) -> RegisterStatus {
    let mut st = RegisterStatus {
        branch: BRANCH.into(),
        ..Default::default()
    };
    if !is_repo(root) {
        st.mode = "none".into();
        return st;
    }
    st.remote = has_origin(root);
    st.code_branch = current_branch(root);
    st.tracked_in_code = tracked_in_code(root);
    let local = ref_exists(root, &format!("refs/heads/{BRANCH}"));
    let remote = ref_exists(root, &format!("refs/remotes/origin/{BRANCH}"));
    if is_mounted(root) {
        fill_worktree_status(root, &mut st, remote);
        if st.tracked_in_code {
            // Git überschreibt ignorierte Dateien beim Checkout eines Branches,
            // der `.agent/specs` noch trackt: der Worktree zeigt dann dessen
            // alten Stand. Kein Sync, bis der Code-Branch zurückgewechselt ist.
            st.mode = "blocked".into();
            st.reason = Some(format!(
                "Der Code-Branch `{}` trackt `.agent/specs` noch und hat die Register-Dateien überschrieben. Zurück auf main wechseln; der nächste Sync stellt das Register wieder her. Den Branch auf main rebasen.",
                st.code_branch.clone().unwrap_or_else(|| "HEAD".into())
            ));
        } else {
            st.mode = "mounted".into();
        }
        return st;
    }
    if local || remote {
        if st.tracked_in_code {
            st.mode = "blocked".into();
            st.reason = Some(format!(
                "Der Branch `{}` trackt `.agent/specs` noch, obwohl das Register `{BRANCH}` existiert. Branch auf main rebasen; erst dann lässt sich der Worktree einhängen.",
                st.code_branch.clone().unwrap_or_else(|| "HEAD".into())
            ));
        } else {
            st.mode = "detached".into();
            st.reason = Some("Register `specs` vorhanden, aber nicht eingehängt. Einrichten legt den Worktree `.agent/specs` an.".into());
        }
        return st;
    }
    if st.remote && st.tracked_in_code {
        st.mode = "migratable".into();
        st.reason = Some("Specs liegen im Code-Branch. Einrichten verschiebt sie in den Branch `specs` (Worktree `.agent/specs`), committet die Ignore-Regel und pusht das Register.".into());
        return st;
    }
    st.mode = "none".into();
    st
}

fn fill_worktree_status(root: &Path, st: &mut RegisterStatus, remote: bool) {
    let wt = worktree_dir(root);
    if let Ok(out) = git_ok(&wt, &["status", "--porcelain", "--untracked-files=all"]) {
        st.unsent = count_lines(&out);
    }
    st.rebasing = git_ok(&wt, &["rev-parse", "--git-path", "rebase-merge"])
        .map(|p| wt.join(p.trim()).exists())
        .unwrap_or(false)
        || git_ok(&wt, &["rev-parse", "--git-path", "rebase-apply"])
            .map(|p| wt.join(p.trim()).exists())
            .unwrap_or(false);
    if remote {
        if let Ok(out) = git_ok(
            &wt,
            &[
                "rev-list",
                "--left-right",
                "--count",
                &format!("HEAD...origin/{BRANCH}"),
            ],
        ) {
            let mut parts = out.split_whitespace();
            st.ahead = parts.next().and_then(|n| n.parse().ok()).unwrap_or(0);
            st.behind = parts.next().and_then(|n| n.parse().ok()).unwrap_or(0);
        }
    }
    if st.rebasing {
        if let Ok(out) = git_ok(&wt, &["diff", "--name-only", "--diff-filter=U"]) {
            for file in out.lines().map(str::trim).filter(|l| !l.is_empty()) {
                // Rebase: Stufe 2 = Basis (Team, origin/specs), Stufe 3 = eigener Commit.
                let team = git_ok(&wt, &["show", &format!(":2:{file}")]).unwrap_or_default();
                let mine = git_ok(&wt, &["show", &format!(":3:{file}")]).unwrap_or_default();
                st.conflicts.push(RegisterConflict {
                    file: format!("{SPECS_DIR}/{file}"),
                    spec_id: file.split('/').next().unwrap_or(file).to_string(),
                    team,
                    mine,
                });
            }
        }
    }
}

/// Migration: Branch `specs` aus dem getrackten `.agent/specs` bauen, im
/// Code-Branch entfernen und ignorieren, Worktree einhängen, Register pushen.
pub(crate) fn migrate(root: &Path) -> Result<RegisterStatus, String> {
    if !has_origin(root) {
        return Err("Kein Remote `origin` — das Register braucht ein gemeinsames Remote.".into());
    }
    if ref_exists(root, &format!("refs/heads/{BRANCH}"))
        || ref_exists(root, &format!("refs/remotes/origin/{BRANCH}"))
    {
        return Err(format!(
            "Branch `{BRANCH}` existiert bereits; stattdessen einhängen."
        ));
    }
    let branch = current_branch(root).ok_or("Kein Branch ausgecheckt (detached HEAD).")?;
    if !["main", "master"].contains(&branch.as_str()) {
        return Err(format!(
            "Die Migration läuft nur auf main/master, nicht auf `{branch}`: offene Branches, die `.agent/specs` tracken, lassen sich danach nicht mehr auschecken, bevor sie rebased sind."
        ));
    }
    if !tracked_in_code(root) {
        return Err(
            "`.agent/specs` ist im Code-Branch nicht getrackt — nichts zu migrieren.".into(),
        );
    }
    let dirty = git_ok(root, &["status", "--porcelain", "--", SPECS_DIR])?;
    if !dirty.trim().is_empty() {
        return Err(
            "Uncommittete Änderungen in `.agent/specs` zuerst committen oder verwerfen.".into(),
        );
    }
    let tree = git_ok(root, &["rev-parse", &format!("HEAD:{SPECS_DIR}")])?
        .trim()
        .to_string();
    // Temporärer Index: Specs-Baum + .gitattributes, ohne den Arbeitsbaum anzufassen.
    let index = tempfile::NamedTempFile::new().map_err(|e| e.to_string())?;
    let index_path = index.path().to_string_lossy().into_owned();
    let envs = [("GIT_INDEX_FILE", index_path.as_str())];
    git_ok_env(root, &["read-tree", &tree], &envs)?;
    let blob = git_run(
        root,
        &["hash-object", "-w", "--stdin"],
        &[],
        Some(ATTRIBUTES),
    )?;
    if blob.code != 0 {
        return Err(blob.stderr);
    }
    let blob = String::from_utf8_lossy(&blob.stdout).trim().to_string();
    git_ok_env(
        root,
        &[
            "update-index",
            "--add",
            "--cacheinfo",
            &format!("100644,{blob},.gitattributes"),
        ],
        &envs,
    )?;
    let new_tree = git_ok_env(root, &["write-tree"], &envs)?.trim().to_string();
    let commit = git_ok(
        root,
        &[
            "commit-tree",
            &new_tree,
            "-m",
            &format!("specs: Register aus {branch} übernommen (Spec 028)"),
        ],
    )?
    .trim()
    .to_string();
    git_ok(root, &["branch", BRANCH, &commit])?;
    // Code-Branch: Specs entfernen, ignorieren, committen.
    git_ok(root, &["rm", "-r", "-q", "--", SPECS_DIR])?;
    let _ = std::fs::remove_dir_all(worktree_dir(root));
    let ignore = root.join(".gitignore");
    let mut text = std::fs::read_to_string(&ignore).unwrap_or_default();
    if !text.lines().any(|l| l.trim() == IGNORE_LINE) {
        if !text.is_empty() && !text.ends_with('\n') {
            text.push('\n');
        }
        text.push_str("# Spec-Register: Worktree des Branch specs (Spec 028)\n");
        text.push_str(IGNORE_LINE);
        text.push('\n');
        std::fs::write(&ignore, text).map_err(|e| e.to_string())?;
    }
    git_ok(root, &["add", "--", ".gitignore"])?;
    git_ok(
        root,
        &[
            "commit",
            "-q",
            "-m",
            &format!("chore: .agent/specs wird Worktree des Branch {BRANCH} (Spec 028)"),
        ],
    )?;
    git_ok(root, &["worktree", "add", SPECS_DIR, BRANCH])?;
    let mut st = status(root);
    let mut errors = Vec::new();
    if let Err(e) = git_ok(root, &["push", "-u", "origin", BRANCH]) {
        errors.push(format!("Register nicht gepusht: {e}"));
    }
    if let Err(e) = git_ok(root, &["push", "origin", &branch]) {
        errors.push(format!("{branch} nicht gepusht (Ignore-Regel): {e}"));
    }
    if !errors.is_empty() {
        st.last_error = Some(errors.join(" · "));
    }
    st.last_sync = Some(now_iso());
    Ok(st)
}

/// Frischer Klon: Worktree für den vorhandenen Branch `specs` anlegen.
pub(crate) fn mount(root: &Path) -> Result<RegisterStatus, String> {
    if is_mounted(root) {
        return Ok(status(root));
    }
    if tracked_in_code(root) {
        return Err(
            "Der aktuelle Branch trackt `.agent/specs` noch; erst auf main rebasen.".into(),
        );
    }
    let dir = worktree_dir(root);
    if dir.exists() && dir_has_content(&dir) {
        return Err(
            "`.agent/specs` ist nicht leer; Inhalt sichern und Ordner entfernen, dann einhängen."
                .into(),
        );
    }
    if has_origin(root) {
        let _ = git(root, &["fetch", "--quiet", "origin", BRANCH]);
    }
    if ref_exists(root, &format!("refs/heads/{BRANCH}")) {
        git_ok(root, &["worktree", "add", SPECS_DIR, BRANCH])?;
    } else if ref_exists(root, &format!("refs/remotes/origin/{BRANCH}")) {
        git_ok(
            root,
            &[
                "worktree",
                "add",
                "--track",
                "-b",
                BRANCH,
                SPECS_DIR,
                &format!("origin/{BRANCH}"),
            ],
        )?;
    } else {
        return Err(format!(
            "Weder `{BRANCH}` noch `origin/{BRANCH}` vorhanden."
        ));
    }
    Ok(status(root))
}

fn changed_spec_ids(wt: &Path) -> Vec<String> {
    let mut ids: Vec<String> = git_ok(wt, &["diff", "--cached", "--name-only"])
        .unwrap_or_default()
        .lines()
        .filter_map(|l| l.trim().split('/').next().map(str::to_string))
        .filter(|s| !s.is_empty())
        .collect();
    ids.sort();
    ids.dedup();
    ids
}

/// Nach dem Wechsel von einem alten Branch (der `.agent/specs` trackte) zurück
/// auf main hat Git die Register-Dateien aus dem Worktree entfernt. Das ist
/// keine Löschabsicht: alle getrackten Dateien fehlen → wiederherstellen,
/// nie als Löschung committen.
fn repair_clobbered(wt: &Path) -> Result<Option<String>, String> {
    // Maßstab sind die Spec-Dateien: fehlen alle getrackten SPEC.md, war es
    // der Checkout, keine Bearbeitung.
    let tracked = git_ok(wt, &["ls-files"])?
        .lines()
        .filter(|l| l.trim().ends_with("SPEC.md"))
        .count();
    if tracked == 0 {
        return Ok(None);
    }
    let porcelain = git_ok(wt, &["status", "--porcelain", "--untracked-files=no"])?;
    let deleted = porcelain
        .lines()
        .filter(|l| (l.starts_with(" D") || l.starts_with("D ")) && l.trim().ends_with("SPEC.md"))
        .count();
    if deleted < tracked {
        return Ok(None);
    }
    git_ok(wt, &["checkout", "--", "."])?;
    Ok(Some("Register-Dateien waren durch einen Branchwechsel entfernt und wurden aus dem Branch specs wiederhergestellt.".into()))
}

/// Sync: lokale Änderungen committen, fetch, rebase auf `origin/specs`, push.
/// Ein Konflikt lässt den Rebase gestoppt stehen (Status zeigt ihn).
pub(crate) fn sync(root: &Path) -> Result<RegisterStatus, String> {
    if !is_mounted(root) {
        return Err("Register nicht eingehängt.".into());
    }
    let wt = worktree_dir(root);
    let mut st = status(root);
    if st.mode == "blocked" {
        return Ok(st);
    }
    let repair_note = repair_clobbered(&wt)?;
    if repair_note.is_some() {
        st = status(root);
    }
    if st.rebasing {
        st.reason = Some("Konflikt offen — erst entscheiden, dann läuft der Sync weiter.".into());
        return Ok(st);
    }
    let mut errors = Vec::new();
    if st.unsent > 0 {
        git_ok(&wt, &["add", "-A"])?;
        let ids = changed_spec_ids(&wt);
        let subject = match ids.len() {
            0 => "spec: aktualisiert".to_string(),
            1..=4 => format!("spec({}): aktualisiert", ids.join(", ")),
            n => format!("spec: {n} Specs aktualisiert"),
        };
        if let Err(e) = git_ok(&wt, &["commit", "-q", "-m", &subject]) {
            errors.push(format!("Commit: {e}"));
        }
    }
    if has_origin(root) {
        match git(&wt, &["fetch", "--quiet", "origin", BRANCH]) {
            Ok(out) if out.code == 0 => {
                let remote_ref = format!("origin/{BRANCH}");
                let behind = git_ok(
                    &wt,
                    &["rev-list", "--count", &format!("HEAD..{remote_ref}")],
                )
                .ok()
                .and_then(|n| n.trim().parse::<u32>().ok())
                .unwrap_or(0);
                if behind > 0 {
                    let rebase = git_run(
                        &wt,
                        &["rebase", "--quiet", &remote_ref],
                        &[("GIT_EDITOR", "true")],
                        None,
                    )?;
                    if rebase.code != 0 {
                        let mut st = status(root);
                        if !st.rebasing {
                            // Kein Konflikt, sondern ein anderer Fehler: Stand bleibt lokal.
                            st.last_error = Some(format!("Rebase: {}", rebase.stderr.trim()));
                        } else {
                            st.reason = Some("Konflikt: dieselben Zeilen wurden im Team und hier geändert. Bitte je Datei entscheiden.".into());
                        }
                        return Ok(st);
                    }
                }
                let ahead = git_ok(
                    &wt,
                    &["rev-list", "--count", &format!("{remote_ref}..HEAD")],
                )
                .ok()
                .and_then(|n| n.trim().parse::<u32>().ok())
                .unwrap_or(0);
                if ahead > 0 {
                    if let Err(e) = git_ok(&wt, &["push", "--quiet", "origin", BRANCH]) {
                        errors.push(format!("Push: {e}"));
                    }
                }
            }
            Ok(out) => errors.push(format!(
                "Fetch: {}",
                out.stderr
                    .lines()
                    .last()
                    .unwrap_or("Remote nicht erreichbar")
                    .trim()
            )),
            Err(e) => errors.push(format!("Fetch: {e}")),
        }
    }
    let mut st = status(root);
    st.last_sync = Some(now_iso());
    if !errors.is_empty() {
        st.last_error = Some(errors.join(" · "));
    }
    if st.reason.is_none() {
        st.reason = repair_note;
    }
    Ok(st)
}

/// Konfliktentscheidung je Datei: `team` (origin/specs), `mine` (eigener
/// Commit) oder `edited` (Datei wurde von Hand bereinigt). Ohne offene
/// Konflikte läuft der Rebase weiter und pusht.
pub(crate) fn resolve(root: &Path, file: &str, choice: &str) -> Result<RegisterStatus, String> {
    let wt = worktree_dir(root);
    let rel = file
        .strip_prefix(&format!("{SPECS_DIR}/"))
        .unwrap_or(file)
        .to_string();
    if rel.contains("..") || rel.starts_with('/') {
        return Err(format!("Ungültiger Pfad: {file}"));
    }
    match choice {
        // Rebase: --ours = Basis (Team), --theirs = eigener Commit.
        "team" => {
            git_ok(&wt, &["checkout", "--ours", "--", &rel])?;
        }
        "mine" => {
            git_ok(&wt, &["checkout", "--theirs", "--", &rel])?;
        }
        "edited" => {
            let text = std::fs::read_to_string(wt.join(&rel)).map_err(|e| e.to_string())?;
            if text.contains("<<<<<<< ") || text.contains(">>>>>>> ") {
                return Err("Die Datei enthält noch Konfliktmarker.".into());
            }
        }
        other => return Err(format!("Unbekannte Entscheidung: {other}")),
    }
    git_ok(&wt, &["add", "--", &rel])?;
    let remaining = git_ok(&wt, &["diff", "--name-only", "--diff-filter=U"])?;
    if remaining.trim().is_empty() {
        let out = git_run(
            &wt,
            &["rebase", "--continue"],
            &[("GIT_EDITOR", "true")],
            None,
        )?;
        if out.code != 0 {
            let mut st = status(root);
            if !st.rebasing {
                st.last_error = Some(format!("Rebase: {}", out.stderr.trim()));
            }
            return Ok(st);
        }
        return sync(root);
    }
    Ok(status(root))
}

pub(crate) fn abort(root: &Path) -> Result<RegisterStatus, String> {
    let wt = worktree_dir(root);
    git_ok(&wt, &["rebase", "--abort"])?;
    Ok(status(root))
}

/// Höchste Spec-Nummer im Team-Register (`origin/specs`, ohne Fetch).
pub(crate) fn remote_max_number(root: &Path) -> Option<u32> {
    if !is_mounted(root) {
        return None;
    }
    let wt = worktree_dir(root);
    let out = git_ok(
        &wt,
        &["ls-tree", "--name-only", &format!("origin/{BRANCH}")],
    )
    .ok()?;
    out.lines()
        .filter_map(|name| crate::project_cmd::spec_number_of(name.trim()))
        .max()
}

#[tauri::command]
pub async fn project_register_status(project: String) -> Result<RegisterStatus, String> {
    let root = resolve_project_root(&project)?;
    tauri::async_runtime::spawn_blocking(move || Ok(status(&root)))
        .await
        .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn project_register_setup(project: String) -> Result<RegisterStatus, String> {
    let root = resolve_project_root(&project)?;
    tauri::async_runtime::spawn_blocking(move || match status(&root).mode.as_str() {
        "migratable" => migrate(&root),
        "detached" => mount(&root),
        "mounted" => Ok(status(&root)),
        "blocked" => Err(status(&root).reason.unwrap_or_default()),
        _ => Err("Kein Git-Remote oder keine getrackten Specs — nichts einzurichten.".into()),
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn project_register_sync(project: String) -> Result<RegisterStatus, String> {
    let root = resolve_project_root(&project)?;
    tauri::async_runtime::spawn_blocking(move || sync(&root))
        .await
        .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn project_register_resolve(
    project: String,
    file: String,
    choice: String,
) -> Result<RegisterStatus, String> {
    let root = resolve_project_root(&project)?;
    tauri::async_runtime::spawn_blocking(move || resolve(&root, &file, &choice))
        .await
        .map_err(|e| e.to_string())?
}

#[tauri::command]
pub async fn project_register_abort(project: String) -> Result<RegisterStatus, String> {
    let root = resolve_project_root(&project)?;
    tauri::async_runtime::spawn_blocking(move || abort(&root))
        .await
        .map_err(|e| e.to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn run(root: &Path, args: &[&str]) -> String {
        let out = git_run(root, args, &[], None).unwrap();
        assert_eq!(out.code, 0, "git {}: {}", args.join(" "), out.stderr);
        String::from_utf8_lossy(&out.stdout).into_owned()
    }

    fn identity(root: &Path, name: &str) {
        run(root, &["config", "user.name", name]);
        run(
            root,
            &["config", "user.email", &format!("{name}@example.invalid")],
        );
    }

    struct Team {
        _dir: tempfile::TempDir,
        origin: PathBuf,
        a: PathBuf,
    }

    /// Repo A mit getrackten Specs auf main, gepusht nach origin.
    fn team() -> Team {
        let dir = tempfile::tempdir().unwrap();
        let base = crate::project_cmd::strip_verbatim(dir.path().canonicalize().unwrap());
        let origin = base.join("origin.git");
        fs::create_dir_all(&origin).unwrap();
        run(&origin, &["init", "-q", "--bare", "-b", "main"]);
        let a = base.join("A");
        fs::create_dir_all(&a).unwrap();
        run(&a, &["init", "-q", "-b", "main"]);
        identity(&a, "anna");
        run(&a, &["remote", "add", "origin", origin.to_str().unwrap()]);
        let spec = a.join(".agent/specs/001-x");
        fs::create_dir_all(&spec).unwrap();
        fs::write(
            spec.join("SPEC.md"),
            "---\nstation: Backlog\norder: 1\n---\n# X\n\n## Tasks\n\n- [ ] eins\n- [ ] zwei\n",
        )
        .unwrap();
        fs::write(
            spec.join("history.jsonl"),
            "{\"timestamp\":\"t0\",\"spec_id\":\"001-x\",\"event_type\":\"spec_created\",\"actor\":\"user\",\"summary\":\"angelegt\"}\n",
        )
        .unwrap();
        fs::create_dir_all(a.join(".agent/playbooks")).unwrap();
        fs::write(a.join(".agent/playbooks/release.md"), "# Release\n").unwrap();
        fs::write(a.join("main.rs"), "code\n").unwrap();
        run(&a, &["add", "-A"]);
        run(&a, &["commit", "-q", "-m", "vor Migration"]);
        run(&a, &["push", "-q", "-u", "origin", "main"]);
        Team {
            _dir: dir,
            origin,
            a,
        }
    }

    fn clone(team: &Team, name: &str) -> PathBuf {
        let target = team.a.parent().unwrap().join(name);
        run(
            team.a.parent().unwrap(),
            &["clone", "-q", team.origin.to_str().unwrap(), name],
        );
        identity(&target, name);
        target
    }

    fn spec_text(root: &Path) -> String {
        fs::read_to_string(root.join(".agent/specs/001-x/SPEC.md")).unwrap()
    }

    #[test]
    fn migration_builds_register_branch_and_keeps_code_checkout_clean() {
        let team = team();
        let a = &team.a;
        let before = status(a);
        assert_eq!(before.mode, "migratable", "{before:?}");
        assert!(before.tracked_in_code);

        let st = migrate(a).unwrap();
        assert_eq!(st.mode, "mounted", "{st:?}");
        assert_eq!(st.last_error, None);
        assert!(is_mounted(a));
        assert_eq!(run(a, &["status", "--porcelain"]).trim(), "");
        assert!(run(a, &["ls-files", ".agent/specs"]).trim().is_empty());
        assert!(fs::read_to_string(a.join(".gitignore"))
            .unwrap()
            .contains(".agent/specs/"));
        assert!(a.join(".agent/specs/.gitattributes").is_file());
        assert!(a.join(".agent/specs/001-x/SPEC.md").is_file());
        assert!(a.join(".agent/playbooks/release.md").is_file());
        assert_eq!(
            run(a, &["-C", ".agent/specs", "branch", "--show-current"]).trim(),
            "specs"
        );
        assert!(ref_exists(a, "refs/remotes/origin/specs"));
        // Idempotent: nochmals einrichten ändert nichts.
        assert!(migrate(a).is_err());
        assert_eq!(status(a).mode, "mounted");
    }

    #[test]
    fn migration_refuses_feature_branch_dirty_specs_and_missing_remote() {
        let team = team();
        let a = &team.a;
        run(a, &["switch", "-q", "-c", "spec/001-x"]);
        assert!(migrate(a).unwrap_err().contains("main/master"));
        run(a, &["switch", "-q", "main"]);
        fs::write(a.join(".agent/specs/001-x/SPEC.md"), "geändert").unwrap();
        assert!(migrate(a).unwrap_err().contains("Uncommittete"));
        run(a, &["checkout", "--", ".agent/specs"]);
        run(a, &["remote", "remove", "origin"]);
        assert_eq!(status(a).mode, "none");
        assert!(migrate(a).unwrap_err().contains("origin"));
    }

    #[test]
    fn two_clones_sync_without_code_merges_union_history_and_show_conflicts() {
        let team = team();
        let a = &team.a;
        migrate(a).unwrap();
        run(a, &["push", "-q", "origin", "main"]);

        // Frischer Klon B: Worktree fehlt → detached → mount.
        let b = clone(&team, "B");
        let st = status(&b);
        assert_eq!(st.mode, "detached", "{st:?}");
        let st = mount(&b).unwrap();
        assert_eq!(st.mode, "mounted", "{st:?}");
        assert!(b.join(".agent/specs/001-x/SPEC.md").is_file());
        assert_eq!(run(&b, &["status", "--porcelain"]).trim(), "");

        // A arbeitet auf einem Feature-Branch und tickt eine Task; nur das Register wandert.
        run(a, &["switch", "-q", "-c", "spec/001-x"]);
        let text = spec_text(a)
            .replace("- [ ] eins", "- [x] eins")
            .replace("station: Backlog", "station: Doing");
        fs::write(a.join(".agent/specs/001-x/SPEC.md"), text).unwrap();
        let mut hist = fs::OpenOptions::new()
            .append(true)
            .open(a.join(".agent/specs/001-x/history.jsonl"))
            .unwrap();
        use std::io::Write;
        writeln!(hist, "{{\"timestamp\":\"t1\",\"spec_id\":\"001-x\",\"event_type\":\"station_changed\",\"actor\":\"anna\",\"summary\":\"Doing\"}}").unwrap();
        drop(hist);
        assert_eq!(status(a).unsent, 2);
        let st = sync(a).unwrap();
        assert_eq!((st.unsent, st.ahead, st.behind), (0, 0, 0), "{st:?}");
        assert_eq!(st.last_error, None);
        assert_eq!(run(a, &["branch", "--show-current"]).trim(), "spec/001-x");
        assert_eq!(run(a, &["status", "--porcelain"]).trim(), "");
        let subject = run(a, &["-C", ".agent/specs", "log", "-1", "--format=%s"]);
        assert_eq!(subject.trim(), "spec(001-x): aktualisiert");

        let st = sync(&b).unwrap();
        assert_eq!(st.behind, 0, "{st:?}");
        assert!(spec_text(&b).contains("- [x] eins"));
        assert!(spec_text(&b).contains("station: Doing"));
        assert_eq!(run(&b, &["branch", "--show-current"]).trim(), "main");

        // Gleichzeitig: beide hängen History an, ändern verschiedene Zeilen.
        fs::write(
            b.join(".agent/specs/001-x/SPEC.md"),
            spec_text(&b).replace("- [ ] zwei", "- [x] zwei"),
        )
        .unwrap();
        let mut hist = fs::OpenOptions::new()
            .append(true)
            .open(b.join(".agent/specs/001-x/history.jsonl"))
            .unwrap();
        writeln!(hist, "{{\"timestamp\":\"t2\",\"spec_id\":\"001-x\",\"event_type\":\"agent_run\",\"actor\":\"B\",\"summary\":\"zwei\"}}").unwrap();
        drop(hist);
        sync(&b).unwrap();
        fs::write(
            a.join(".agent/specs/001-x/SPEC.md"),
            spec_text(a).replace("order: 1", "order: 2"),
        )
        .unwrap();
        let mut hist = fs::OpenOptions::new()
            .append(true)
            .open(a.join(".agent/specs/001-x/history.jsonl"))
            .unwrap();
        writeln!(hist, "{{\"timestamp\":\"t3\",\"spec_id\":\"001-x\",\"event_type\":\"spec_edited\",\"actor\":\"anna\",\"summary\":\"order\"}}").unwrap();
        drop(hist);
        let st = sync(a).unwrap();
        assert!(!st.rebasing, "{st:?}");
        assert_eq!((st.ahead, st.behind), (0, 0), "{st:?}");
        let history = fs::read_to_string(a.join(".agent/specs/001-x/history.jsonl")).unwrap();
        assert_eq!(history.lines().count(), 4, "{history}");
        assert!(spec_text(a).contains("- [x] zwei"));
        assert!(spec_text(a).contains("order: 2"));

        // Konflikt: dieselbe Zeile in beiden Klonen.
        sync(&b).unwrap();
        fs::write(
            b.join(".agent/specs/001-x/SPEC.md"),
            spec_text(&b).replace("station: Doing", "station: Done"),
        )
        .unwrap();
        sync(&b).unwrap();
        fs::write(
            a.join(".agent/specs/001-x/SPEC.md"),
            spec_text(a).replace("station: Doing", "station: Backlog"),
        )
        .unwrap();
        let st = sync(a).unwrap();
        assert!(st.rebasing, "{st:?}");
        assert_eq!(st.conflicts.len(), 1);
        let conflict = &st.conflicts[0];
        assert_eq!(conflict.spec_id, "001-x");
        assert_eq!(conflict.file, ".agent/specs/001-x/SPEC.md");
        assert!(conflict.team.contains("station: Done"), "{conflict:?}");
        assert!(conflict.mine.contains("station: Backlog"), "{conflict:?}");
        assert!(spec_text(a).contains("<<<<<<<"));
        // Sync ohne Entscheidung ändert nichts.
        assert!(sync(a).unwrap().rebasing);
        assert_eq!(run(a, &["status", "--porcelain"]).trim(), "");

        // Entscheidung: Team-Fassung übernehmen → Rebase läuft weiter, Push.
        let st = resolve(a, ".agent/specs/001-x/SPEC.md", "team").unwrap();
        assert!(!st.rebasing, "{st:?}");
        assert_eq!((st.ahead, st.behind, st.unsent), (0, 0, 0), "{st:?}");
        assert!(spec_text(a).contains("station: Done"));
        assert!(!spec_text(a).contains("<<<<<<<"));
        sync(&b).unwrap();
        assert!(spec_text(&b).contains("station: Done"));

        // Eigene Fassung behalten: zweiter Konflikt.
        fs::write(
            b.join(".agent/specs/001-x/SPEC.md"),
            spec_text(&b).replace("order: 2", "order: 5"),
        )
        .unwrap();
        sync(&b).unwrap();
        fs::write(
            a.join(".agent/specs/001-x/SPEC.md"),
            spec_text(a).replace("order: 2", "order: 7"),
        )
        .unwrap();
        assert!(sync(a).unwrap().rebasing);
        let st = resolve(a, ".agent/specs/001-x/SPEC.md", "mine").unwrap();
        assert!(!st.rebasing, "{st:?}");
        assert!(spec_text(a).contains("order: 7"));
        sync(&b).unwrap();
        assert!(spec_text(&b).contains("order: 7"));

        // Abbrechen stellt den lokalen Commit wieder her.
        fs::write(
            b.join(".agent/specs/001-x/SPEC.md"),
            spec_text(&b).replace("order: 7", "order: 8"),
        )
        .unwrap();
        sync(&b).unwrap();
        fs::write(
            a.join(".agent/specs/001-x/SPEC.md"),
            spec_text(a).replace("order: 7", "order: 9"),
        )
        .unwrap();
        assert!(sync(a).unwrap().rebasing);
        let st = abort(a).unwrap();
        assert!(!st.rebasing);
        assert_eq!((st.ahead, st.behind), (1, 1), "{st:?}");
        assert!(spec_text(a).contains("order: 9"));

        // Höchste Team-Nummer aus origin/specs.
        assert_eq!(remote_max_number(a), Some(1));
        assert_eq!(remote_max_number(&b), Some(1));
    }

    #[test]
    fn offline_keeps_local_commits_and_does_not_duplicate_after_reconnect() {
        let team = team();
        let a = &team.a;
        migrate(a).unwrap();
        let b = clone(&team, "B");
        mount(&b).unwrap();
        // B geht offline.
        let url = run(&b, &["remote", "get-url", "origin"]).trim().to_string();
        run(
            &b,
            &["remote", "set-url", "origin", "/nonexistent/origin.git"],
        );
        fs::write(
            b.join(".agent/specs/001-x/SPEC.md"),
            spec_text(&b).replace("- [ ] eins", "- [x] eins"),
        )
        .unwrap();
        let st = sync(&b).unwrap();
        assert_eq!(st.unsent, 0);
        assert!(
            st.last_error.as_deref().unwrap_or("").contains("Fetch"),
            "{st:?}"
        );
        assert!(st.ahead >= 1, "{st:?}");
        let st = sync(&b).unwrap();
        assert_eq!(
            run(&b, &["-C", ".agent/specs", "rev-list", "--count", "HEAD"]).trim(),
            "2",
            "kein zweiter Commit ohne Änderung"
        );
        assert!(st.last_error.is_some());
        run(&b, &["remote", "set-url", "origin", &url]);
        let st = sync(&b).unwrap();
        assert_eq!((st.ahead, st.behind, st.unsent), (0, 0, 0), "{st:?}");
        assert_eq!(st.last_error, None);
        sync(a).unwrap();
        assert!(spec_text(a).contains("- [x] eins"));
        let history = fs::read_to_string(a.join(".agent/specs/001-x/history.jsonl")).unwrap();
        assert_eq!(history.lines().count(), 1);
    }

    #[test]
    fn old_branch_tracking_specs_is_blocked_until_rebased() {
        let team = team();
        let a = &team.a;
        run(a, &["branch", "-q", "old", "HEAD"]);
        migrate(a).unwrap();
        let commits_before = run(a, &["-C", ".agent/specs", "rev-list", "--count", "HEAD"]);
        // Git hält ignorierte Dateien für entbehrlich: der Checkout des alten
        // Branches gelingt und überschreibt den Worktree mit dem alten Stand.
        run(a, &["switch", "-q", "old"]);
        let st = status(a);
        assert_eq!(st.mode, "blocked", "{st:?}");
        assert!(st.reason.as_deref().unwrap_or("").contains("überschrieben"));
        assert_eq!(
            sync(a).unwrap().mode,
            "blocked",
            "kein Commit im blockierten Zustand"
        );
        // Zurück auf main: Git entfernt die alten getrackten Dateien aus dem
        // Worktree. Der Sync erkennt die Totalräumung und stellt das Register
        // her, statt Löschungen zu committen.
        run(a, &["switch", "-q", "main"]);
        assert!(!a.join(".agent/specs/001-x/SPEC.md").exists());
        let st = sync(a).unwrap();
        assert_eq!(st.mode, "mounted", "{st:?}");
        assert!(
            st.reason
                .as_deref()
                .unwrap_or("")
                .contains("wiederhergestellt"),
            "{st:?}"
        );
        assert!(a.join(".agent/specs/001-x/SPEC.md").is_file());
        assert_eq!(st.unsent, 0);
        assert_eq!(
            run(a, &["-C", ".agent/specs", "rev-list", "--count", "HEAD"]),
            commits_before,
            "keine Löschung committet"
        );
        // Ein zweiter Worktree auf dem alten Branch: Register existiert, Code
        // trackt die Specs → blocked, Einhängen verweigert.
        let old = a.parent().unwrap().join("A-old");
        run(a, &["worktree", "add", "-q", old.to_str().unwrap(), "old"]);
        let st = status(&old);
        assert_eq!(st.mode, "blocked", "{st:?}");
        assert!(mount(&old).is_err());
    }
}
