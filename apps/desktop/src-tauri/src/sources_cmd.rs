//! Skill-Quellen (Plan skill-quellen-und-export.md, Q1): beliebige Repos —
//! Git-URL oder Ordner — global (`~/.speccify/settings.json` →
//! `skill_sources`) und pro Projekt (`.agent/settings.json` →
//! `speccify.sources`). Git-Quellen werden **einmal geklont** nach
//! `~/.speccify/sources/<slug>/` (System-`git`, Credentials über die
//! vorhandenen Helper, `GIT_TERMINAL_PROMPT=0`) und danach wie eine lokale
//! Bibliothek behandelt: Ids und Versionen aus den SKILL.md-Metadaten, keine
//! Tags nötig (D1). Der Checkout ist Cache — Herkunft ist die URL (D3).

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::Duration;

use serde::Serialize;
use wait_timeout::ChildExt;

use crate::project_cmd::resolve_project_root;

const CLONE_TIMEOUT: Duration = Duration::from_secs(300);

/// Git-URL oder Ordner? Erkannt an Schema/Endung — ein Ordnerpfad, der
/// zufällig auf `.git` endet, wäre ein Bare-Repo und ist ebenfalls Git.
pub(crate) fn is_git_location(location: &str) -> bool {
    let s = location.trim();
    s.starts_with("http://")
        || s.starts_with("https://")
        || s.starts_with("ssh://")
        || s.starts_with("git://")
        || s.starts_with("git@")
        || s.starts_with("file://")
        || s.starts_with("git+")
        || s.ends_with(".git")
}

/// `git+`-Präfix des Core abstreifen — die App klont die nackte URL.
fn plain_url(location: &str) -> &str {
    location
        .trim()
        .strip_prefix("git+")
        .unwrap_or(location.trim())
}

/// Anzeigename: letztes Pfadsegment ohne `.git`, sonst der Ordnername.
pub(crate) fn display_name(location: &str) -> String {
    let s = plain_url(location).trim_end_matches('/');
    let last = s.rsplit(['/', ':']).next().unwrap_or(s);
    let name = last.strip_suffix(".git").unwrap_or(last);
    if name.is_empty() {
        s.to_string()
    } else {
        name.to_string()
    }
}

/// Stabiler Ordnername für den Checkout: Host + Pfad, alles andere `-`.
pub(crate) fn slug(location: &str) -> String {
    let s = plain_url(location);
    let stripped = s
        .strip_prefix("https://")
        .or_else(|| s.strip_prefix("http://"))
        .or_else(|| s.strip_prefix("ssh://"))
        .or_else(|| s.strip_prefix("git://"))
        .or_else(|| s.strip_prefix("file://"))
        .or_else(|| s.strip_prefix("git@"))
        .unwrap_or(s);
    let stripped = stripped.strip_suffix(".git").unwrap_or(stripped);
    let mut out = String::new();
    let mut dash = false;
    for ch in stripped.chars() {
        if ch.is_ascii_alphanumeric() || ch == '.' {
            out.push(ch.to_ascii_lowercase());
            dash = false;
        } else if !dash {
            out.push('-');
            dash = true;
        }
    }
    out.trim_matches('-').to_string()
}

fn sources_root() -> Result<PathBuf, String> {
    Ok(crate::settings::home_dir()?
        .join(".speccify")
        .join("sources"))
}

pub(crate) fn checkout_dir(location: &str) -> Result<PathBuf, String> {
    Ok(sources_root()?.join(slug(location)))
}

fn expand_dir(raw: &str) -> PathBuf {
    let trimmed = raw.trim();
    if let Some(rest) = trimmed.strip_prefix("~/") {
        if let Ok(home) = crate::settings::home_dir() {
            return home.join(rest);
        }
    }
    PathBuf::from(trimmed)
}

/// Wo die Skills einer Quelle liegen — ohne Netz. Git: der Checkout (Fehler,
/// wenn noch nicht geklont); Ordner: der Ordner.
pub(crate) fn resolve_location(location: &str) -> Result<PathBuf, String> {
    if is_git_location(location) {
        let dir = checkout_dir(location)?;
        if !dir.join(".git").exists() {
            return Err(format!(
                "Quelle noch nicht geklont: {} — in der Bibliothek „Aktualisieren“ klicken.",
                location.trim()
            ));
        }
        Ok(dir)
    } else {
        let dir = expand_dir(location);
        if !dir.is_dir() {
            return Err(format!("Keine Quelle: {}", dir.display()));
        }
        Ok(dir)
    }
}

fn git(cwd: Option<&Path>, args: &[&str]) -> Result<String, String> {
    let mut command = Command::new("git");
    command
        .args(args)
        .env("GIT_TERMINAL_PROMPT", "0")
        .env("LC_ALL", "C")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    if let Some(dir) = cwd {
        command.current_dir(dir);
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    let mut child = command
        .spawn()
        .map_err(|e| format!("git nicht startbar ({e}) — ist Git installiert und im PATH?"))?;
    let stdout_pipe = child.stdout.take();
    let stderr_pipe = child.stderr.take();
    let reader = std::thread::spawn(move || {
        use std::io::Read;
        let mut out = String::new();
        let mut err = String::new();
        if let Some(mut pipe) = stdout_pipe {
            let _ = pipe.read_to_string(&mut out);
        }
        if let Some(mut pipe) = stderr_pipe {
            let _ = pipe.read_to_string(&mut err);
        }
        (out, err)
    });
    let status = match child
        .wait_timeout(CLONE_TIMEOUT)
        .map_err(|e| e.to_string())?
    {
        Some(status) => status,
        None => {
            let _ = child.kill();
            let _ = child.wait();
            return Err(format!(
                "git {} hat nach 5 Minuten nicht geantwortet.",
                args.join(" ")
            ));
        }
    };
    let (out, err) = reader
        .join()
        .map_err(|_| "git-Ausgabe verloren".to_string())?;
    if !status.success() {
        let message = err.trim();
        return Err(if message.is_empty() {
            format!(
                "git {} → Exit {}",
                args.join(" "),
                status.code().unwrap_or(-1)
            )
        } else {
            // Anmeldefehler bekommen den Hinweis, wie man sich anmeldet (D5).
            if message.contains("Authentication failed")
                || message.contains("could not read Username")
                || message.contains("Permission denied")
                || message.contains("terminal prompts disabled")
            {
                format!(
                    "{message}\n\nZugang fehlt: Für HTTPS einen Credential-Helper mit Token einrichten (macOS Keychain / Windows Credential Manager), für SSH den Schlüssel im Agent — die App nutzt dasselbe git wie das Terminal."
                )
            } else {
                message.to_string()
            }
        });
    }
    Ok(out)
}

/// Klonen, wenn nötig; `refresh` zieht nach (`pull --ff-only`).
pub(crate) fn ensure_checkout(location: &str, refresh: bool) -> Result<PathBuf, String> {
    let dir = checkout_dir(location)?;
    if dir.join(".git").exists() {
        if refresh {
            git(Some(&dir), &["pull", "--ff-only", "--quiet"])?;
        }
        return Ok(dir);
    }
    if let Some(parent) = dir.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let target = dir.to_string_lossy().into_owned();
    git(None, &["clone", "--quiet", plain_url(location), &target])?;
    Ok(dir)
}

#[derive(Serialize, Clone, Debug, PartialEq)]
pub struct SourceInfo {
    pub name: String,
    pub location: String,
    /// `git` oder `dir`
    pub kind: String,
    /// `global` oder `project`
    pub scope: String,
    /// Wo die Skills liegen (Checkout oder Ordner), wenn vorhanden.
    pub path: Option<String>,
    /// `ready` | `missing` | `error`
    pub state: String,
    pub detail: Option<String>,
}

fn describe(location: &str, scope: &str) -> SourceInfo {
    let kind = if is_git_location(location) {
        "git"
    } else {
        "dir"
    };
    let (path, state, detail) = match resolve_location(location) {
        Ok(dir) => (Some(dir.display().to_string()), "ready", None),
        Err(message) => (None, "missing", Some(message)),
    };
    SourceInfo {
        name: display_name(location),
        location: location.trim().to_string(),
        kind: kind.into(),
        scope: scope.into(),
        path,
        state: state.into(),
        detail,
    }
}

fn project_locations(project: &str) -> Result<Vec<String>, String> {
    let settings = crate::workflow_setup::project_settings_get(project.to_string())?;
    Ok(settings
        .get("speccify")
        .and_then(|s| s.get("sources"))
        .and_then(|s| s.as_array())
        .map(|entries| {
            entries
                .iter()
                .filter_map(|entry| {
                    entry.as_str().map(str::to_string).or_else(|| {
                        entry
                            .get("location")
                            .and_then(|l| l.as_str())
                            .map(str::to_string)
                    })
                })
                .collect()
        })
        .unwrap_or_default())
}

/// Wirksame Quellen: Projekt zuerst, dann global (Duplikate entfernt).
#[tauri::command]
pub fn sources_list(project: Option<String>) -> Result<Vec<SourceInfo>, String> {
    let mut out: Vec<SourceInfo> = Vec::new();
    if let Some(project) = project.as_deref().filter(|p| !p.trim().is_empty()) {
        let root = resolve_project_root(project)?;
        for location in project_locations(&root.display().to_string())? {
            out.push(describe(&location, "project"));
        }
    }
    for location in crate::settings::get_settings()?.skill_sources {
        if out.iter().any(|known| known.location == location.trim()) {
            continue;
        }
        out.push(describe(&location, "global"));
    }
    Ok(out)
}

/// Quelle hinzufügen — Git wird geklont (Netz), Ordner geprüft; dann in den
/// globalen oder Projekt-Settings gemerkt.
#[tauri::command]
pub fn source_add(project: Option<String>, location: String) -> Result<SourceInfo, String> {
    let location = location.trim().to_string();
    if location.is_empty() {
        return Err("Keine Quelle angegeben.".into());
    }
    if is_git_location(&location) {
        ensure_checkout(&location, false)?;
    } else if !expand_dir(&location).is_dir() {
        return Err(format!("Kein Ordner: {location}"));
    }
    match project.as_deref().filter(|p| !p.trim().is_empty()) {
        Some(project) => {
            let root = resolve_project_root(project)?;
            let key = root.display().to_string();
            let mut list = project_locations(&key)?;
            if !list.contains(&location) {
                list.push(location.clone());
            }
            crate::workflow_setup::project_settings_set(
                key,
                "speccify.sources".into(),
                serde_json::json!(list),
            )?;
            Ok(describe(&location, "project"))
        }
        None => {
            let mut settings = crate::settings::get_settings()?;
            if !settings.skill_sources.contains(&location) {
                settings.skill_sources.push(location.clone());
            }
            crate::settings::save_settings(settings)?;
            Ok(describe(&location, "global"))
        }
    }
}

/// Quelle aus den Settings nehmen; der Checkout bleibt (Cache, kein Löschen).
#[tauri::command]
pub fn source_remove(project: Option<String>, location: String) -> Result<(), String> {
    let location = location.trim().to_string();
    match project.as_deref().filter(|p| !p.trim().is_empty()) {
        Some(project) => {
            let root = resolve_project_root(project)?;
            let key = root.display().to_string();
            let list: Vec<String> = project_locations(&key)?
                .into_iter()
                .filter(|known| known != &location)
                .collect();
            crate::workflow_setup::project_settings_set(
                key,
                "speccify.sources".into(),
                if list.is_empty() {
                    serde_json::Value::Null
                } else {
                    serde_json::json!(list)
                },
            )?;
        }
        None => {
            let mut settings = crate::settings::get_settings()?;
            settings.skill_sources.retain(|known| known != &location);
            crate::settings::save_settings(settings)?;
        }
    }
    Ok(())
}

/// Git: klonen oder `pull --ff-only`; Ordner: nur neu beschreiben.
#[tauri::command]
pub fn source_refresh(location: String, scope: Option<String>) -> Result<SourceInfo, String> {
    if is_git_location(&location) {
        ensure_checkout(&location, true)?;
    }
    Ok(describe(&location, scope.as_deref().unwrap_or("global")))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_git_locations_and_names() {
        assert!(is_git_location("https://github.com/acme/skills"));
        assert!(is_git_location("git@gitlab.itsd.example:team/skills.git"));
        assert!(is_git_location("git+https://github.com/acme/skills"));
        assert!(!is_git_location("~/Desktop/Work/speccify/skills"));
        assert_eq!(display_name("https://github.com/acme/skills.git"), "skills");
        assert_eq!(
            display_name("git@gitlab.example:team/itsd-skills.git"),
            "itsd-skills"
        );
        assert_eq!(display_name("~/Work/speccify/skills/"), "skills");
        assert_eq!(
            slug("https://github.com/acme/Skills.git"),
            "github.com-acme-skills"
        );
        assert_eq!(
            slug("git@gitlab.example:team/x.git"),
            "gitlab.example-team-x"
        );
    }

    #[test]
    fn clones_a_local_git_repo_and_refreshes() {
        if Command::new("git").arg("--version").output().is_err() {
            return;
        }
        let base = std::env::temp_dir().join(format!("speccify-sources-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        let upstream = base.join("upstream");
        std::fs::create_dir_all(upstream.join("skills/hello")).unwrap();
        std::fs::write(
            upstream.join("skills/hello/SKILL.md"),
            "---\nname: hello\nmetadata:\n  speccify.scope: acme\n---\n# Hello\n",
        )
        .unwrap();
        for args in [
            vec!["init", "-q", "-b", "main"],
            vec!["config", "user.email", "t@example.com"],
            vec!["config", "user.name", "Test"],
            vec!["add", "-A"],
            vec!["commit", "-q", "-m", "init"],
        ] {
            git(Some(&upstream), &args).unwrap();
        }
        // Checkout-Wurzel in den Temp-Ordner umbiegen: HOME überschreiben.
        let home = base.join("home");
        std::fs::create_dir_all(&home).unwrap();
        let previous = std::env::var("HOME").ok();
        std::env::set_var("HOME", &home);
        let location = format!("file://{}", upstream.display());
        let dir = ensure_checkout(&location, false).unwrap();
        assert!(dir.join("skills/hello/SKILL.md").is_file());
        assert!(dir.starts_with(home.join(".speccify/sources")));
        let info = describe(&location, "global");
        assert_eq!((info.kind.as_str(), info.state.as_str()), ("git", "ready"));
        assert_eq!(info.name, "upstream");
        // Upstream ändert sich → refresh zieht nach.
        std::fs::write(
            upstream.join("skills/hello/SKILL.md"),
            "---\nname: hello\n---\n# Hello v2\n",
        )
        .unwrap();
        git(Some(&upstream), &["commit", "-q", "-am", "v2"]).unwrap();
        ensure_checkout(&location, true).unwrap();
        assert!(std::fs::read_to_string(dir.join("skills/hello/SKILL.md"))
            .unwrap()
            .contains("v2"));
        if let Some(value) = previous {
            std::env::set_var("HOME", value);
        }
    }
}
