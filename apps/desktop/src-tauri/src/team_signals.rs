//! Teamsignale über Git (Spec 030): „neu seit letztem Sync“ aus den Commits
//! des Registers, Fragen an Personen (`an: <email>`) und ein ausgehender
//! Webhook für lokale Ereignisse. Kein eigener Dienst: die Ereignisquelle
//! sind die Commits auf `specs`; der Webhook ist optional und nur ausgehend.

use std::collections::BTreeMap;
use std::path::Path;
use std::time::Duration;

use serde::{Deserialize, Serialize};

use crate::git_cmd::git_ok;
use crate::project_cmd::resolve_project_root;

const SPECS_DIR: &str = ".agent/specs";
const WEBHOOK_TIMEOUT: Duration = Duration::from_secs(10);
pub const WEBHOOK_EVENTS: &[&str] = &["station_changed", "ready", "question", "conflict"];

// --- Neu seit letztem Sync --------------------------------------------------

#[derive(Serialize, Clone, Debug, PartialEq)]
pub struct RegisterCommit {
    pub hash: String,
    pub author: String,
    pub email: String,
    pub date: String,
    pub subject: String,
}

#[derive(Serialize, Clone, Debug, PartialEq)]
pub struct SpecChanges {
    pub spec_id: String,
    pub file: String,
    /// Neueste zuerst.
    pub commits: Vec<RegisterCommit>,
    /// Hash des neuesten fremden Commits — Merker „gesehen“ je Spec.
    pub latest: String,
}

#[derive(Serialize, Clone, Debug, Default)]
pub struct ChangesReport {
    pub head: Option<String>,
    pub me: Option<String>,
    pub specs: Vec<SpecChanges>,
}

/// Fremde Commits auf dem Register seit `since` (Hash) bzw. der letzten Woche,
/// je Spec gruppiert. Eigene Commits (E-Mail der Git-Identität) zählen nicht.
pub(crate) fn changes(root: &Path, since: Option<&str>) -> ChangesReport {
    let wt = root.join(SPECS_DIR);
    if !crate::spec_register::is_mounted(root) {
        return ChangesReport::default();
    }
    let me = crate::spec_owner::identity(root).map(|id| id.email.to_ascii_lowercase());
    let head = git_ok(&wt, &["rev-parse", "HEAD"])
        .ok()
        .map(|s| s.trim().to_string());
    let range = since
        .filter(|s| !s.is_empty() && s.chars().all(|c| c.is_ascii_hexdigit()))
        .map(|s| format!("{s}..HEAD"));
    let mut args = vec![
        "log",
        "--format=%x01%H%x00%an%x00%ae%x00%cI%x00%s",
        "--name-only",
    ];
    let range_arg;
    if let Some(range) = range {
        range_arg = range;
        args.push(&range_arg);
    } else {
        args.push("--since=7.days");
    }
    let Ok(out) = git_ok(&wt, &args) else {
        return ChangesReport {
            head,
            me,
            specs: Vec::new(),
        };
    };
    let mut by_spec: BTreeMap<String, Vec<RegisterCommit>> = BTreeMap::new();
    for block in out.split('\u{1}').filter(|b| !b.trim().is_empty()) {
        let mut lines = block.lines();
        let Some(head_line) = lines.next() else {
            continue;
        };
        let mut parts = head_line.split('\0');
        let (Some(hash), Some(author), Some(email), Some(date), Some(subject)) = (
            parts.next(),
            parts.next(),
            parts.next(),
            parts.next(),
            parts.next(),
        ) else {
            continue;
        };
        if me.as_deref() == Some(&email.to_ascii_lowercase()) {
            continue;
        }
        let commit = RegisterCommit {
            hash: hash.to_string(),
            author: author.to_string(),
            email: email.to_string(),
            date: date.to_string(),
            subject: subject.to_string(),
        };
        let mut seen = std::collections::HashSet::new();
        for path in lines.map(str::trim).filter(|l| !l.is_empty()) {
            let Some(spec_id) = path.split('/').next() else {
                continue;
            };
            if spec_id == ".gitattributes" || spec_id == "archive" {
                continue;
            }
            if seen.insert(spec_id.to_string()) {
                by_spec
                    .entry(spec_id.to_string())
                    .or_default()
                    .push(commit.clone());
            }
        }
    }
    let specs = by_spec
        .into_iter()
        .map(|(spec_id, commits)| SpecChanges {
            file: format!("{SPECS_DIR}/{spec_id}/SPEC.md"),
            latest: commits.first().map(|c| c.hash.clone()).unwrap_or_default(),
            spec_id,
            commits,
        })
        .collect();
    ChangesReport { head, me, specs }
}

#[tauri::command]
pub async fn project_register_changes(
    project: String,
    since: Option<String>,
) -> Result<ChangesReport, String> {
    let root = resolve_project_root(&project)?;
    tauri::async_runtime::spawn_blocking(move || Ok(changes(&root, since.as_deref())))
        .await
        .map_err(|e| e.to_string())?
}

// --- Webhook ------------------------------------------------------------------

#[derive(Serialize, Clone, Debug, PartialEq)]
pub struct WebhookEvent {
    /// `station_changed` | `ready` | `question` | `conflict`
    pub event: String,
    pub spec_id: String,
    pub title: String,
    pub person: String,
    pub project: String,
    pub path: String,
    /// Fertiger Nachrichtentext (Slack/Teams/Mattermost lesen `text`).
    pub text: String,
}

#[derive(Deserialize, Clone, Debug, Default)]
pub struct WebhookConfig {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default)]
    pub events: Vec<String>,
}

/// Projekt-Konfiguration aus `.agent/settings.json` (`webhook.enabled`,
/// `webhook.events`); ohne `events` gelten alle vier.
pub(crate) fn config(root: &Path) -> WebhookConfig {
    let settings =
        crate::workflow_setup::project_settings_get(root.display().to_string()).unwrap_or_default();
    let mut config: WebhookConfig = settings
        .get("webhook")
        .cloned()
        .and_then(|v| serde_json::from_value(v).ok())
        .unwrap_or_default();
    if config.events.is_empty() {
        config.events = WEBHOOK_EVENTS.iter().map(|e| e.to_string()).collect();
    }
    config
}

/// URL nur aus der Rechnerumgebung oder den globalen App-Settings — nie aus
/// einer getrackten Projektdatei.
pub(crate) fn url() -> Option<String> {
    std::env::var("SPECCIFY_WEBHOOK_URL")
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .or_else(|| {
            crate::settings::get_settings()
                .ok()
                .and_then(|s| s.webhook_url)
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
        })
}

pub(crate) fn event(
    kind: &str,
    root: &Path,
    spec_id: &str,
    title: &str,
    file: &str,
    detail: &str,
) -> WebhookEvent {
    let person = crate::spec_owner::identity(root)
        .map(|id| id.label())
        .unwrap_or_else(|| "unbekannt".into());
    let project = root
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default();
    let what = match kind {
        "station_changed" => format!("Station: {detail}"),
        "ready" => "bereit zur Abnahme".to_string(),
        "question" => format!("Frage {detail}"),
        "conflict" => "Register-Konflikt, Entscheidung nötig".to_string(),
        other => other.to_string(),
    };
    WebhookEvent {
        event: kind.into(),
        spec_id: spec_id.into(),
        title: title.into(),
        person: person.clone(),
        project: project.clone(),
        path: file.into(),
        text: format!("[{project}] {spec_id} „{title}“ — {what} · {person}"),
    }
}

/// Blockierender POST mit Zeitlimit; Fehler als Text.
pub(crate) fn post(url: &str, event: &WebhookEvent) -> Result<(), String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(WEBHOOK_TIMEOUT)
        .build()
        .map_err(|e| e.to_string())?;
    let response = client
        .post(url)
        .json(event)
        .send()
        .map_err(|e| format!("Webhook nicht erreichbar: {e}"))?;
    if !response.status().is_success() {
        return Err(format!("Webhook antwortet {}", response.status()));
    }
    Ok(())
}

/// Sendet im Hintergrund, wenn konfiguriert; meldet Fehler über `on_error`.
pub(crate) fn dispatch(
    root: &Path,
    event: WebhookEvent,
    on_error: impl Fn(String) + Send + 'static,
) {
    let config = config(root);
    if !config.enabled || !config.events.iter().any(|e| e == &event.event) {
        return;
    }
    let Some(url) = url() else {
        on_error("Webhook aktiviert, aber keine URL (SPECCIFY_WEBHOOK_URL oder Settings).".into());
        return;
    };
    std::thread::spawn(move || {
        if let Err(error) = post(&url, &event) {
            on_error(error);
        }
    });
}

#[tauri::command]
pub async fn project_webhook_test(project: String) -> Result<String, String> {
    let root = resolve_project_root(&project)?;
    tauri::async_runtime::spawn_blocking(move || {
        let url = url().ok_or("Keine Webhook-URL (SPECCIFY_WEBHOOK_URL oder Settings).")?;
        let event = event("test", &root, "test", "Testnachricht aus Speccify", "", "");
        post(&url, &event)?;
        Ok(format!("Testnachricht gesendet an {}", redact(&url)))
    })
    .await
    .map_err(|e| e.to_string())?
}

fn redact(url: &str) -> String {
    let short: String = url.chars().take(32).collect();
    if url.len() > 32 {
        format!("{short}…")
    } else {
        short
    }
}

// --- Board-Diff für lokale Ereignisse ------------------------------------------

#[derive(Clone, Debug, PartialEq)]
pub struct Snapshot {
    pub spec_id: String,
    pub file: String,
    pub title: String,
    pub station: String,
    pub ready: bool,
    pub open_question: Option<String>,
}

pub(crate) fn snapshot(root: &Path) -> Vec<Snapshot> {
    crate::project_cmd::read_project_board(root.display().to_string())
        .unwrap_or_default()
        .into_iter()
        .filter(|entry| !entry.archived)
        .map(|entry| Snapshot {
            spec_id: entry.id.clone(),
            file: entry.file.clone(),
            title: entry.title.clone(),
            station: entry.station.clone(),
            ready: entry.ready,
            open_question: entry.open_question.clone(),
        })
        .collect()
}

/// Ereignisse zwischen zwei Board-Ständen: (Art, Spec, Detail).
pub(crate) fn diff(previous: &[Snapshot], next: &[Snapshot]) -> Vec<(String, Snapshot, String)> {
    let mut events = Vec::new();
    for spec in next {
        let Some(before) = previous.iter().find(|p| p.spec_id == spec.spec_id) else {
            continue;
        };
        if before.station != spec.station {
            events.push((
                "station_changed".to_string(),
                spec.clone(),
                format!("{} → {}", before.station, spec.station),
            ));
        }
        if !before.ready && spec.ready {
            events.push(("ready".to_string(), spec.clone(), String::new()));
        }
        if spec.open_question.is_some() && before.open_question != spec.open_question {
            events.push((
                "question".to_string(),
                spec.clone(),
                spec.open_question.clone().unwrap_or_default(),
            ));
        }
    }
    events
}

/// Nur Änderungen, die hier entstanden sind, lösen den Webhook aus: im
/// Register erkennbar an noch nicht committeten Dateien der Spec; ohne
/// Register ist jede Änderung lokal.
pub(crate) fn locally_originated(root: &Path, spec_id: &str) -> bool {
    if !crate::spec_register::is_mounted(root) {
        return true;
    }
    git_ok(
        &root.join(SPECS_DIR),
        &["status", "--porcelain", "--", spec_id],
    )
    .map(|out| !out.trim().is_empty())
    .unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn snap(id: &str, station: &str, ready: bool, question: Option<&str>) -> Snapshot {
        Snapshot {
            spec_id: id.into(),
            file: format!(".agent/specs/{id}/SPEC.md"),
            title: id.to_uppercase(),
            station: station.into(),
            ready,
            open_question: question.map(str::to_string),
        }
    }

    #[test]
    fn diff_reports_station_ready_and_new_questions_only() {
        let before = vec![
            snap("a", "Backlog", false, None),
            snap("b", "Doing", false, Some("Q1")),
            snap("c", "Doing", true, None),
        ];
        let after = vec![
            snap("a", "Doing", false, None),
            snap("b", "Doing", true, Some("Q2")),
            snap("c", "Doing", true, None),
            snap("new", "Backlog", false, None),
        ];
        let events = diff(&before, &after);
        let kinds: Vec<(String, String, String)> = events
            .iter()
            .map(|(k, s, d)| (k.clone(), s.spec_id.clone(), d.clone()))
            .collect();
        assert_eq!(
            kinds,
            vec![
                (
                    "station_changed".into(),
                    "a".into(),
                    "Backlog → Doing".into()
                ),
                ("ready".into(), "b".into(), String::new()),
                ("question".into(), "b".into(), "Q2".into()),
            ]
        );
        assert!(diff(&after, &after).is_empty());
    }

    #[test]
    fn event_text_and_config_defaults() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let event = event(
            "station_changed",
            root,
            "012-x",
            "Titel",
            ".agent/specs/012-x/SPEC.md",
            "Backlog → Doing",
        );
        assert!(event
            .text
            .contains("012-x „Titel“ — Station: Backlog → Doing"));
        assert_eq!(event.person, "unbekannt", "kein Git-Repo, keine Identität");
        let cfg = config(root);
        assert!(!cfg.enabled);
        assert_eq!(cfg.events, WEBHOOK_EVENTS);
        std::fs::create_dir_all(root.join(".agent")).unwrap();
        std::fs::write(
            root.join(".agent/settings.json"),
            r#"{"webhook":{"enabled":true,"events":["ready"]}}"#,
        )
        .unwrap();
        let cfg = config(root);
        assert!(cfg.enabled);
        assert_eq!(cfg.events, vec!["ready"]);
        assert!(locally_originated(root, "012-x"), "ohne Register lokal");
    }

    #[test]
    fn foreign_register_commits_are_grouped_per_spec() {
        // Register-Fixture über spec_register::migrate, dann ein fremder Commit im Klon.
        let dir = tempfile::tempdir().unwrap();
        let base = crate::project_cmd::strip_verbatim(dir.path().canonicalize().unwrap());
        let run = |root: &Path, args: &[&str]| {
            let out = crate::git_cmd::git_run(root, args, &[], None).unwrap();
            assert_eq!(out.code, 0, "git {}: {}", args.join(" "), out.stderr);
            String::from_utf8_lossy(&out.stdout).into_owned()
        };
        let origin = base.join("origin.git");
        std::fs::create_dir_all(&origin).unwrap();
        run(&origin, &["init", "-q", "--bare", "-b", "main"]);
        let a = base.join("A");
        std::fs::create_dir_all(a.join(".agent/specs/001-x")).unwrap();
        run(&a, &["init", "-q", "-b", "main"]);
        run(&a, &["config", "user.name", "anna"]);
        run(&a, &["config", "user.email", "anna@example.invalid"]);
        run(&a, &["remote", "add", "origin", origin.to_str().unwrap()]);
        std::fs::write(
            a.join(".agent/specs/001-x/SPEC.md"),
            "---\nstation: Backlog\n---\n# X\n",
        )
        .unwrap();
        run(&a, &["add", "-A"]);
        run(&a, &["commit", "-q", "-m", "init"]);
        run(&a, &["push", "-q", "-u", "origin", "main"]);
        crate::spec_register::migrate(&a).unwrap();
        let b = base.join("B");
        run(&base, &["clone", "-q", origin.to_str().unwrap(), "B"]);
        run(&b, &["config", "user.name", "ben"]);
        run(&b, &["config", "user.email", "ben@example.invalid"]);
        crate::spec_register::mount(&b).unwrap();
        let head_before = changes(&a, None).head.unwrap();
        std::fs::write(
            b.join(".agent/specs/001-x/SPEC.md"),
            "---\nstation: Doing\n---\n# X\n",
        )
        .unwrap();
        std::fs::create_dir_all(b.join(".agent/specs/002-y")).unwrap();
        std::fs::write(
            b.join(".agent/specs/002-y/SPEC.md"),
            "---\nstation: Backlog\n---\n# Y\n",
        )
        .unwrap();
        crate::spec_register::sync(&b).unwrap();
        crate::spec_register::sync(&a).unwrap();
        let report = changes(&a, Some(&head_before));
        assert_eq!(report.me.as_deref(), Some("anna@example.invalid"));
        let ids: Vec<&str> = report.specs.iter().map(|s| s.spec_id.as_str()).collect();
        assert_eq!(ids, vec!["001-x", "002-y"]);
        assert_eq!(report.specs[0].commits[0].author, "ben");
        assert_eq!(
            report.specs[0].commits[0].subject,
            "spec(001-x, 002-y): aktualisiert"
        );
        assert_eq!(report.specs[0].latest, report.specs[0].commits[0].hash);
        // Eigene Commits zählen nicht; B sieht nichts Fremdes seit seinem Stand.
        assert!(changes(&b, report.head.as_deref()).specs.is_empty());
        assert!(
            changes(&b, Some(&head_before)).specs.is_empty(),
            "B hat selbst geschrieben"
        );
        assert!(
            !locally_originated(&a, "001-x"),
            "nach dem Sync nichts Uncommittetes"
        );
    }
}
