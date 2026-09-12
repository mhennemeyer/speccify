//! Besitzer und Branch je Spec (Spec 029): `owner` und `branch` im flachen
//! Front Matter, gesetzt beim Übernehmen (Backlog → Doing), zurückgesetzt
//! beim Abgeben. Identität = Git-Identität des Checkouts. Die Beobachtung
//! der Branches (`origin/<branch>`, letzter Autor, Alter, lokaler Checkout)
//! wird angezeigt, nie korrigiert.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde::Serialize;

use crate::git_cmd::{git, git_ok};
use crate::project_cmd::{resolve_project_root, spec_id_of, writable_spec_path};

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Identity {
    pub name: String,
    pub email: String,
}

impl Identity {
    /// `Name <email>` — so steht es in der Front Matter.
    pub fn label(&self) -> String {
        if self.email.is_empty() {
            self.name.clone()
        } else {
            format!("{} <{}>", self.name, self.email)
        }
    }
}

fn is_repo(root: &Path) -> bool {
    git(root, &["rev-parse", "--is-inside-work-tree"])
        .map(|o| o.code == 0)
        .unwrap_or(false)
}

/// Git-Identität des Checkouts; ohne Repository keine Identität (Besitzer und
/// Branch sind Git-Begriffe — Projekte ohne Git bleiben unverändert).
pub(crate) fn identity(root: &Path) -> Option<Identity> {
    if !is_repo(root) {
        return None;
    }
    let name = git_ok(root, &["config", "--get", "user.name"])
        .ok()
        .map(|s| s.trim().to_string())
        .unwrap_or_default();
    let email = git_ok(root, &["config", "--get", "user.email"])
        .ok()
        .map(|s| s.trim().to_string())
        .unwrap_or_default();
    if name.is_empty() && email.is_empty() {
        return None;
    }
    Some(Identity { name, email })
}

/// E-Mail aus `Name <email>`; ohne Klammern der ganze Text.
pub(crate) fn email_of(owner: &str) -> String {
    owner
        .rsplit_once('<')
        .and_then(|(_, rest)| rest.strip_suffix('>'))
        .map(|s| s.trim().to_ascii_lowercase())
        .unwrap_or_else(|| owner.trim().to_ascii_lowercase())
}

fn current_branch(root: &Path) -> Option<String> {
    git_ok(root, &["symbolic-ref", "--short", "-q", "HEAD"])
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
}

/// Vorschlag beim Übernehmen: der aktuelle Feature-Branch, sonst
/// `spec/<id>`; `main`/`master` sind kein Arbeitsbranch.
pub(crate) fn suggested_branch(root: &Path, spec_id: &str) -> String {
    match current_branch(root) {
        Some(branch)
            if !["main", "master", crate::spec_register::BRANCH].contains(&branch.as_str()) =>
        {
            branch
        }
        _ => format!("spec/{spec_id}"),
    }
}

/// Setzt, ersetzt oder entfernt (`None`) Front-Matter-Zeilen; alles andere
/// bleibt byte-stabil. Neue Zeilen kommen vor das schließende `---`.
pub(crate) fn set_fields(text: &str, updates: &[(&str, Option<String>)]) -> Result<String, String> {
    let mut lines = text.split_inclusive('\n');
    let first = lines.next().ok_or("Leere Datei")?;
    if first.trim_end() != "---" {
        return Err("Kein Frontmatter".into());
    }
    let ending = if first.ends_with("\r\n") {
        "\r\n"
    } else {
        "\n"
    };
    let mut out = String::with_capacity(text.len() + 64);
    out.push_str(first);
    let mut pending: Vec<(&str, Option<String>)> = updates.to_vec();
    let mut closed = false;
    for line in lines {
        if !closed && line.trim_end() == "---" {
            for (key, value) in &pending {
                if let Some(value) = value {
                    out.push_str(&format!("{key}: {value}{ending}"));
                }
            }
            pending.clear();
            closed = true;
            out.push_str(line);
            continue;
        }
        if !closed {
            if let Some((key, _)) = line.split_once(':') {
                let key = key.trim();
                if let Some(index) = pending
                    .iter()
                    .position(|(k, _)| k.eq_ignore_ascii_case(key))
                {
                    let (k, value) = pending.remove(index);
                    if let Some(value) = value {
                        out.push_str(&format!("{k}: {value}{ending}"));
                    }
                    continue;
                }
            }
        }
        out.push_str(line);
    }
    if !closed {
        return Err("Frontmatter nicht geschlossen".into());
    }
    Ok(out)
}

fn field(text: &str, key: &str) -> Option<String> {
    let (fields, _) = crate::project_cmd::parse_flat_frontmatter(text)?;
    fields
        .iter()
        .find(|(k, _)| k.eq_ignore_ascii_case(key))
        .map(|(_, v)| v.trim().to_string())
        .filter(|v| !v.is_empty() && v != "null")
}

/// Übernahme-Regeln bei einem Stationswechsel: nach Doing ohne Besitzer →
/// Besitzer und Branch setzen; Doing → Backlog → Besitzer zurücksetzen.
/// Liefert den geänderten Text und einen Zusatz für die History.
pub(crate) fn apply_move(
    root: &Path,
    spec_id: &str,
    text: &str,
    old_station: &str,
    new_station: &str,
) -> Result<(String, String), String> {
    let owner = field(text, "owner");
    if new_station == "Doing" && owner.is_none() {
        let Some(me) = identity(root) else {
            return Ok((text.to_string(), String::new()));
        };
        let branch = field(text, "branch").unwrap_or_else(|| suggested_branch(root, spec_id));
        let out = set_fields(
            text,
            &[
                ("owner", Some(me.label())),
                ("branch", Some(branch.clone())),
            ],
        )?;
        return Ok((
            out,
            format!(" · übernommen von {} · Branch {branch}", me.label()),
        ));
    }
    if old_station == "Doing" && new_station == "Backlog" && owner.is_some() {
        let out = set_fields(text, &[("owner", None)])?;
        return Ok((
            out,
            format!(" · abgegeben von {}", owner.unwrap_or_default()),
        ));
    }
    Ok((text.to_string(), String::new()))
}

#[derive(Serialize)]
pub struct TakeResult {
    pub owner: String,
    pub branch: String,
}

/// Übernehmen: Station Doing, Besitzer = Git-Identität, Branch = Vorgabe
/// oder Vorschlag. Kein Branchwechsel — den entscheidet die Person.
#[tauri::command]
pub fn project_spec_take(
    project: String,
    file: String,
    branch: Option<String>,
) -> Result<TakeResult, String> {
    let root = resolve_project_root(&project)?;
    let path = writable_spec_path(&root, &file)?;
    let text = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let me = identity(&root).ok_or("Keine Git-Identität (user.name/user.email) im Projekt.")?;
    let spec_id = spec_id_of(&root, &path);
    let branch = branch
        .map(|b| b.trim().to_string())
        .filter(|b| !b.is_empty())
        .or_else(|| field(&text, "branch"))
        .unwrap_or_else(|| suggested_branch(&root, &spec_id));
    let old_station = field(&text, "station").unwrap_or_else(|| "Backlog".into());
    let out = set_fields(
        &text,
        &[
            ("station", Some("Doing".into())),
            ("owner", Some(me.label())),
            ("branch", Some(branch.clone())),
        ],
    )?;
    std::fs::write(&path, out).map_err(|e| e.to_string())?;
    crate::board_cmd::log_user_event(
        &root,
        &spec_id,
        "station_changed",
        format!(
            "{old_station} -> Doing · übernommen von {} · Branch {branch}",
            me.label()
        ),
    );
    Ok(TakeResult {
        owner: me.label(),
        branch,
    })
}

/// Abgeben: Besitzer entfernen, zurück ins Backlog; `branch` bleibt als Spur.
#[tauri::command]
pub fn project_spec_release(project: String, file: String) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let path = writable_spec_path(&root, &file)?;
    let text = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let spec_id = spec_id_of(&root, &path);
    let owner = field(&text, "owner").unwrap_or_default();
    let old_station = field(&text, "station").unwrap_or_else(|| "Doing".into());
    let out = set_fields(
        &text,
        &[("station", Some("Backlog".into())), ("owner", None)],
    )?;
    std::fs::write(&path, out).map_err(|e| e.to_string())?;
    crate::board_cmd::log_user_event(
        &root,
        &spec_id,
        "station_changed",
        format!("{old_station} -> Backlog · abgegeben von {owner}"),
    );
    Ok(())
}

#[derive(Serialize, Clone, Debug, Default, PartialEq)]
pub struct BranchObservation {
    pub file: String,
    pub spec_id: String,
    pub branch: String,
    pub local: bool,
    pub remote: bool,
    pub last_author: Option<String>,
    pub last_email: Option<String>,
    pub last_date: Option<String>,
    /// Tage seit dem letzten Commit auf dem Branch (Remote vor lokal).
    pub stale_days: Option<u32>,
    /// Der lokale Checkout steht auf diesem Branch.
    pub current: bool,
}

#[derive(Serialize, Clone, Debug, Default)]
pub struct BranchReport {
    pub current: Option<String>,
    pub me: Option<Identity>,
    pub fetched: bool,
    pub specs: Vec<BranchObservation>,
}

static LAST_FETCH: Mutex<Option<HashMap<PathBuf, Instant>>> = Mutex::new(None);
const FETCH_PERIOD: Duration = Duration::from_secs(60);

/// Best-effort `git fetch --prune origin`, höchstens einmal pro Minute je Repo.
fn fetch_if_due(root: &Path) -> bool {
    let due = {
        let mut guard = LAST_FETCH.lock().unwrap_or_else(|e| e.into_inner());
        let map = guard.get_or_insert_with(HashMap::new);
        match map.get(root) {
            Some(at) if at.elapsed() < FETCH_PERIOD => false,
            _ => {
                map.insert(root.to_path_buf(), Instant::now());
                true
            }
        }
    };
    if !due {
        return false;
    }
    git(root, &["fetch", "--quiet", "--prune", "origin"])
        .map(|o| o.code == 0)
        .unwrap_or(false)
}

fn last_commit(root: &Path, reference: &str) -> Option<(String, String, String)> {
    let out = git_ok(
        root,
        &["log", "-1", "--format=%an%x00%ae%x00%cI", reference, "--"],
    )
    .ok()?;
    let mut parts = out.trim().split('\0');
    Some((
        parts.next()?.to_string(),
        parts.next()?.to_string(),
        parts.next()?.to_string(),
    ))
}

fn days_since(iso: &str) -> Option<u32> {
    let when =
        time::OffsetDateTime::parse(iso, &time::format_description::well_known::Rfc3339).ok()?;
    let now = time::OffsetDateTime::now_utc();
    let seconds = (now - when).whole_seconds().max(0);
    Some((seconds / 86_400) as u32)
}

pub(crate) fn observe(root: &Path, specs: &[(String, String, String)]) -> BranchReport {
    let fetched = if specs.is_empty() {
        false
    } else {
        fetch_if_due(root)
    };
    let current = current_branch(root);
    let mut report = BranchReport {
        current: current.clone(),
        me: identity(root),
        fetched,
        specs: Vec::new(),
    };
    for (file, spec_id, branch) in specs {
        let local = git(
            root,
            &[
                "rev-parse",
                "--verify",
                "--quiet",
                &format!("refs/heads/{branch}"),
            ],
        )
        .map(|o| o.code == 0)
        .unwrap_or(false);
        let remote = git(
            root,
            &[
                "rev-parse",
                "--verify",
                "--quiet",
                &format!("refs/remotes/origin/{branch}"),
            ],
        )
        .map(|o| o.code == 0)
        .unwrap_or(false);
        let commit = if remote {
            last_commit(root, &format!("refs/remotes/origin/{branch}"))
        } else if local {
            last_commit(root, &format!("refs/heads/{branch}"))
        } else {
            None
        };
        report.specs.push(BranchObservation {
            file: file.clone(),
            spec_id: spec_id.clone(),
            branch: branch.clone(),
            local,
            remote,
            last_author: commit.as_ref().map(|c| c.0.clone()),
            last_email: commit.as_ref().map(|c| c.1.clone()),
            stale_days: commit.as_ref().and_then(|c| days_since(&c.2)),
            last_date: commit.map(|c| c.2),
            current: current.as_deref() == Some(branch.as_str()),
        });
    }
    report
}

/// Beobachtung aller Doing-Specs mit `branch`.
#[tauri::command]
pub async fn project_spec_branches(project: String) -> Result<BranchReport, String> {
    let root = resolve_project_root(&project)?;
    tauri::async_runtime::spawn_blocking(move || {
        let board = crate::project_cmd::read_project_board(root.display().to_string())?;
        let specs: Vec<(String, String, String)> = board
            .iter()
            .filter(|spec| spec.station == "Doing")
            .filter_map(|spec| {
                spec.branch
                    .clone()
                    .map(|branch| (spec.file.clone(), spec.id.clone(), branch))
            })
            .collect();
        Ok(observe(&root, &specs))
    })
    .await
    .map_err(|e| e.to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn run(root: &Path, args: &[&str]) -> String {
        let out = crate::git_cmd::git_run(root, args, &[], None).unwrap();
        assert_eq!(out.code, 0, "git {}: {}", args.join(" "), out.stderr);
        String::from_utf8_lossy(&out.stdout).into_owned()
    }

    fn project() -> (tempfile::TempDir, PathBuf) {
        let dir = tempfile::tempdir().unwrap();
        // Eigener Unterordner: Nachbarn (origin.git, other) bleiben im Tempdir.
        let root =
            crate::project_cmd::strip_verbatim(dir.path().canonicalize().unwrap()).join("repo");
        fs::create_dir_all(&root).unwrap();
        run(&root, &["init", "-q", "-b", "main"]);
        run(&root, &["config", "user.name", "Anna Beispiel"]);
        run(&root, &["config", "user.email", "anna@example.invalid"]);
        let spec = root.join(".agent/specs/012-demo");
        fs::create_dir_all(&spec).unwrap();
        fs::write(
            spec.join("SPEC.md"),
            "---\nstation: Backlog\norder: 3\nparent: null\n---\n# Demo\n\n## Tasks\n\n- [ ] eins\n",
        )
        .unwrap();
        fs::write(root.join("README.md"), "x\n").unwrap();
        run(&root, &["add", "-A"]);
        run(&root, &["commit", "-q", "-m", "init"]);
        (dir, root)
    }

    #[test]
    fn set_fields_replaces_inserts_and_removes_byte_stable() {
        let text = "---\r\nstation: Backlog\r\norder: 3\r\n---\r\n# T\r\n\r\nBody\r\n";
        let out = set_fields(
            text,
            &[
                ("station", Some("Doing".into())),
                ("owner", Some("A <a@x>".into())),
            ],
        )
        .unwrap();
        assert_eq!(
            out,
            "---\r\nstation: Doing\r\norder: 3\r\nowner: A <a@x>\r\n---\r\n# T\r\n\r\nBody\r\n"
        );
        let out = set_fields(&out, &[("owner", None), ("order", None)]).unwrap();
        assert_eq!(out, "---\r\nstation: Doing\r\n---\r\n# T\r\n\r\nBody\r\n");
        assert!(set_fields("# no frontmatter\n", &[]).is_err());
        assert!(set_fields("---\nstation: x\n", &[]).is_err());
        assert_eq!(
            email_of("Anna <Anna@Example.invalid>"),
            "anna@example.invalid"
        );
        assert_eq!(email_of("anna"), "anna");
    }

    #[test]
    fn take_release_and_move_rules() {
        let (_dir, root) = project();
        let project = root.display().to_string();
        let file = ".agent/specs/012-demo/SPEC.md";
        let result = project_spec_take(project.clone(), file.into(), None).unwrap();
        assert_eq!(result.owner, "Anna Beispiel <anna@example.invalid>");
        assert_eq!(
            result.branch, "spec/012-demo",
            "main ist kein Arbeitsbranch"
        );
        let text = fs::read_to_string(root.join(file)).unwrap();
        assert!(text.starts_with("---\nstation: Doing\norder: 3\nparent: null\nowner: Anna Beispiel <anna@example.invalid>\nbranch: spec/012-demo\n---\n"), "{text}");
        let history = fs::read_to_string(root.join(".agent/specs/012-demo/history.jsonl")).unwrap();
        assert!(
            history.contains("übernommen von Anna Beispiel"),
            "{history}"
        );
        assert!(history.contains("Branch spec/012-demo"));

        // Auf einem Feature-Branch wird dieser vorgeschlagen; ein gesetzter Branch bleibt.
        run(&root, &["switch", "-q", "-c", "feature/x"]);
        assert_eq!(suggested_branch(&root, "012-demo"), "feature/x");
        project_spec_release(project.clone(), file.into()).unwrap();
        let text = fs::read_to_string(root.join(file)).unwrap();
        assert!(text.contains("station: Backlog\n"));
        assert!(!text.contains("owner:"));
        assert!(
            text.contains("branch: spec/012-demo\n"),
            "Branch bleibt als Spur: {text}"
        );
        let history = fs::read_to_string(root.join(".agent/specs/012-demo/history.jsonl")).unwrap();
        assert!(history.contains("abgegeben von Anna Beispiel"));

        // Drag nach Doing übernimmt (Branch aus der Spur), zurück gibt ab.
        crate::project_cmd::project_board_move(project.clone(), file.into(), "Doing".into())
            .unwrap();
        let text = fs::read_to_string(root.join(file)).unwrap();
        assert!(
            text.contains("owner: Anna Beispiel <anna@example.invalid>\n"),
            "{text}"
        );
        assert!(text.contains("branch: spec/012-demo\n"));
        crate::project_cmd::project_board_move(project.clone(), file.into(), "Done".into())
            .unwrap();
        assert!(
            fs::read_to_string(root.join(file))
                .unwrap()
                .contains("owner:"),
            "Done behält den Besitzer"
        );
        crate::project_cmd::project_board_move(project.clone(), file.into(), "Doing".into())
            .unwrap();
        crate::project_cmd::project_board_move(project.clone(), file.into(), "Backlog".into())
            .unwrap();
        let text = fs::read_to_string(root.join(file)).unwrap();
        assert!(!text.contains("owner:"), "{text}");
        assert!(text.contains("station: Backlog\n"));
        assert!(text.contains("order: 3\n"), "andere Felder unverändert");

        // Übernehmen mit ausdrücklichem Branch.
        project_spec_take(project.clone(), file.into(), Some("team/topic".into())).unwrap();
        let board = crate::project_cmd::read_project_board(project).unwrap();
        let entry = board.iter().find(|s| s.id == "012-demo").unwrap();
        assert_eq!(
            entry.owner.as_deref(),
            Some("Anna Beispiel <anna@example.invalid>")
        );
        assert_eq!(entry.branch.as_deref(), Some("team/topic"));
        assert_eq!(entry.station, "Doing");
    }

    #[test]
    fn branch_observation_reports_remote_author_age_and_checkout() {
        let (_dir, root) = project();
        let origin = root.parent().unwrap().join("origin.git");
        fs::create_dir_all(&origin).unwrap();
        run(&origin, &["init", "-q", "--bare", "-b", "main"]);
        run(
            &root,
            &["remote", "add", "origin", origin.to_str().unwrap()],
        );
        run(&root, &["push", "-q", "-u", "origin", "main"]);
        // Kollegin pusht auf spec/012-demo.
        let other = root.parent().unwrap().join("other");
        run(
            root.parent().unwrap(),
            &["clone", "-q", origin.to_str().unwrap(), "other"],
        );
        run(&other, &["config", "user.name", "Ben"]);
        run(&other, &["config", "user.email", "ben@example.invalid"]);
        run(&other, &["switch", "-q", "-c", "spec/012-demo"]);
        fs::write(other.join("work.txt"), "w\n").unwrap();
        run(&other, &["add", "-A"]);
        run(&other, &["commit", "-q", "-m", "work"]);
        run(&other, &["push", "-q", "-u", "origin", "spec/012-demo"]);

        let specs = vec![
            (
                ".agent/specs/012-demo/SPEC.md".to_string(),
                "012-demo".to_string(),
                "spec/012-demo".to_string(),
            ),
            (
                ".agent/specs/013-x/SPEC.md".to_string(),
                "013-x".to_string(),
                "spec/013-x".to_string(),
            ),
        ];
        let report = observe(&root, &specs);
        assert!(report.fetched, "erster Aufruf holt");
        assert_eq!(report.current.as_deref(), Some("main"));
        assert_eq!(report.me.as_ref().unwrap().email, "anna@example.invalid");
        let demo = &report.specs[0];
        assert!(demo.remote && !demo.local && !demo.current, "{demo:?}");
        assert_eq!(demo.last_author.as_deref(), Some("Ben"));
        assert_eq!(demo.last_email.as_deref(), Some("ben@example.invalid"));
        assert_eq!(demo.stale_days, Some(0));
        let missing = &report.specs[1];
        assert!(!missing.remote && !missing.local && missing.last_date.is_none());
        // Zweiter Aufruf innerhalb der Minute holt nicht erneut; Checkout wird erkannt.
        run(&root, &["switch", "-q", "-c", "spec/013-x"]);
        let report = observe(&root, &specs);
        assert!(!report.fetched);
        assert!(report.specs[1].current && report.specs[1].local);
    }
}
