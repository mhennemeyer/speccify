//! Watcher-Basisdienst (Plan projektfenster.md, P5/W2): ein Thread je
//! Projektfenster prüft alle 2 s einen **Fingerprint** (Pfad + mtime +
//! Größe) je UI-Bereich und schickt bei Änderung ein `project-changed`-
//! Event mit den betroffenen Bereichen ans Fenster. Bewusst Poll statt
//! Verzeichnis-Events: Agenten schreiben in place, was ohnehin keinen
//! Verzeichnis-Event erzeugt — der Poll ist der notwendige Mechanismus,
//! Events wären nur Latenz-Optimierung (im Plan als W2-Entscheid notiert).

use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use serde::Serialize;
use tauri::{Emitter, Manager, State};

use crate::project_cmd::resolve_project_root;

use tauri_plugin_notification::NotificationExt;

const POLL_INTERVAL: std::time::Duration = std::time::Duration::from_secs(2);
/// Spec 028: Board-Änderungen werden gebündelt ins Register committet …
const REGISTER_DEBOUNCE: std::time::Duration = std::time::Duration::from_secs(3);
/// … und das Register holt in diesem Raster fremde Änderungen, auch ohne
/// lokale Bewegung.
const REGISTER_PERIOD: std::time::Duration = std::time::Duration::from_secs(60);

/// Fenster, Projektpfad und Lebenszyklus-ID → Stop-Flag des Watcher-Threads.
pub struct ProjectWatchers(Mutex<HashMap<(String, String, String), Arc<AtomicBool>>>);

impl Default for ProjectWatchers {
    fn default() -> Self {
        Self(Mutex::new(HashMap::new()))
    }
}

impl Drop for ProjectWatchers {
    fn drop(&mut self) {
        if let Ok(watchers) = self.0.lock() {
            for stop in watchers.values() {
                stop.store(true, Ordering::Relaxed);
            }
        }
    }
}

/// Was in einem Bereich zur Wahrheit gehört: Verzeichnisse (rekursiv)
/// und/oder Einzeldateien relativ zur Projektwurzel.
struct Area {
    name: &'static str,
    dirs: &'static [&'static str],
    files: &'static [&'static str],
}

const AREAS: &[Area] = &[
    Area {
        name: "board",
        dirs: &[".agent/specs"],
        files: &[],
    },
    Area {
        name: "playbooks",
        dirs: &[".agent/playbooks"],
        files: &[],
    },
    Area {
        name: "skills",
        dirs: &[".agent/skills"],
        files: &[],
    },
    Area {
        name: "tools",
        dirs: &[".agent/tools"],
        files: &[".agent/speccify/expansions.yaml"],
    },
    Area {
        name: "actions",
        dirs: &[],
        files: &[
            ".agent/actions.json",
            ".agent/exec-allowlist.json",
            ".agent/exec-pending.json",
        ],
    },
    Area {
        name: "settings",
        dirs: &[],
        files: &[".agent/settings.json"],
    },
    Area {
        name: "agent",
        dirs: &[],
        files: &["CLAUDE.md", "AGENTS.md", ".agent/agent.md"],
    },
    Area {
        name: "mcps",
        dirs: &[],
        files: &[
            ".mcp.json",
            ".codex/config.toml",
            ".claude/settings.json",
            ".claude/settings.local.json",
        ],
    },
];

fn hash_file(hasher: &mut impl Hasher, path: &Path, relative: &str) {
    if let Ok(meta) = std::fs::metadata(path) {
        relative.hash(hasher);
        meta.len().hash(hasher);
        if let Ok(mtime) = meta.modified() {
            if let Ok(since) = mtime.duration_since(std::time::UNIX_EPOCH) {
                since.as_nanos().hash(hasher);
            }
        }
    }
}

fn hash_dir(hasher: &mut impl Hasher, dir: &Path, prefix: &str) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    let mut paths: Vec<std::path::PathBuf> =
        entries.filter_map(Result::ok).map(|e| e.path()).collect();
    paths.sort();
    for path in paths {
        let name = path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default();
        let relative = format!("{prefix}/{name}");
        if path.is_dir() {
            hash_dir(hasher, &path, &relative);
        } else {
            hash_file(hasher, &path, &relative);
        }
    }
}

/// Fingerprints aller Bereiche — rein und damit testbar.
fn area_fingerprints(root: &Path) -> Vec<(&'static str, u64)> {
    AREAS
        .iter()
        .map(|area| {
            let mut hasher = std::collections::hash_map::DefaultHasher::new();
            for dir in area.dirs {
                hash_dir(&mut hasher, &root.join(dir), dir);
            }
            for file in area.files {
                hash_file(&mut hasher, &root.join(file), file);
            }
            (area.name, hasher.finish())
        })
        .collect()
}

fn changed_areas(
    previous: &[(&'static str, u64)],
    next: &[(&'static str, u64)],
) -> Vec<&'static str> {
    previous
        .iter()
        .zip(next)
        .filter(|(old, new)| old.1 != new.1)
        .map(|(_, new)| new.0)
        .collect()
}

#[derive(Clone, Serialize)]
struct ProjectChanged {
    project: String,
    areas: Vec<&'static str>,
}

#[derive(Clone, Serialize)]
struct RegisterChanged {
    project: String,
    status: crate::spec_register::RegisterStatus,
}

/// Startet den Poll fürs aufrufende Fenster (ersetzt einen laufenden).
/// Der Thread endet, sobald das Fenster verschwindet oder `stop` gesetzt ist.
#[tauri::command]
pub fn project_watch_start(
    window: tauri::WebviewWindow,
    state: State<ProjectWatchers>,
    project: String,
    watcher_id: Option<String>,
) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let label = window.label().to_string();
    let stop = Arc::new(AtomicBool::new(false));
    let project = root.display().to_string();
    {
        let mut watchers = state.0.lock().unwrap();
        watchers.retain(|(owner, path, _), old| {
            if owner == &label && path == &project {
                old.store(true, Ordering::Relaxed);
                false
            } else {
                true
            }
        });
        watchers.insert(
            (
                label.clone(),
                project.clone(),
                watcher_id.unwrap_or_default(),
            ),
            stop.clone(),
        );
    }
    let app = window.app_handle().clone();
    std::thread::spawn(move || {
        // Erster Lauf primt nur — kein Meldungsschwall beim Öffnen (auch
        // für offene Rückfragen: Bestand beim Start wird nicht gemeldet).
        let mut previous = area_fingerprints(&root);
        let mut seen_questions: std::collections::HashSet<String> =
            crate::board_cmd::scan_open_questions(&root)
                .into_iter()
                .map(|question| question.key)
                .collect();
        // Register-Sync (028): fällig nach Board-Ruhe oder im Periodenraster.
        let mut register_due: Option<std::time::Instant> = None;
        let mut register_last = std::time::Instant::now();
        loop {
            std::thread::sleep(POLL_INTERVAL);
            if stop.load(Ordering::Relaxed) {
                break;
            }
            let Some(window) = app.get_webview_window(&label) else {
                break; // Fenster zu → Watcher stirbt mit.
            };
            if crate::spec_register::is_mounted(&root) {
                let now = std::time::Instant::now();
                let due = register_due.is_some_and(|at| at <= now)
                    || now.duration_since(register_last) >= REGISTER_PERIOD;
                if due {
                    register_due = None;
                    register_last = now;
                    if let Ok(status) = crate::spec_register::sync(&root) {
                        let _ = window.emit(
                            "register-changed",
                            RegisterChanged {
                                project: project.clone(),
                                status,
                            },
                        );
                    }
                    // Der Sync selbst kann Dateien ändern (Rebase); das
                    // meldet der nächste Fingerprint-Vergleich regulär.
                }
            }
            let next = area_fingerprints(&root);
            let areas = changed_areas(&previous, &next);
            previous = next;
            if areas.is_empty() {
                continue;
            }
            if areas.contains(&"board") && crate::spec_register::is_mounted(&root) {
                register_due = Some(std::time::Instant::now() + REGISTER_DEBOUNCE);
            }
            let _ = window.emit(
                "project-changed",
                ProjectChanged {
                    project: project.clone(),
                    areas: areas.clone(),
                },
            );
            if areas.contains(&"board") {
                // Neue offene Rückfragen ⇒ System-Notification (dedupe
                // über den Schlüssel, unabhängig vom aktiven Tab).
                for question in crate::board_cmd::scan_open_questions(&root) {
                    if !seen_questions.insert(question.key.clone()) {
                        continue;
                    }
                    let _ = app
                        .notification()
                        .builder()
                        .title(format!("Frage zu „{}“", question.title))
                        .body(if question.text.is_empty() {
                            "Der Agent wartet auf eine Antwort.".to_string()
                        } else {
                            question.text.clone()
                        })
                        .show();
                    let _ = window.emit("open-question", question);
                }
            }
        }
    });
    Ok(())
}

#[tauri::command]
pub fn project_watch_stop(
    window: tauri::WebviewWindow,
    state: State<ProjectWatchers>,
    project: Option<String>,
    watcher_id: Option<String>,
) {
    stop_watchers(
        &mut state.0.lock().unwrap(),
        window.label(),
        project.as_deref(),
        watcher_id.as_deref(),
    );
}

fn stop_watchers(
    watchers: &mut HashMap<(String, String, String), Arc<AtomicBool>>,
    window: &str,
    project: Option<&str>,
    lease: Option<&str>,
) {
    watchers.retain(|(owner, path, id), stop| {
        if owner == window
            && project.is_none_or(|value| value == path)
            && lease.is_none_or(|value| value == id)
        {
            stop.store(true, Ordering::Relaxed);
            false
        } else {
            true
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stopping_a_workspace_watch_preserves_other_roots_windows_and_new_leases() {
        let mut watchers = HashMap::new();
        let flags: Vec<_> = (0..4).map(|_| Arc::new(AtomicBool::new(false))).collect();
        for (index, (window, project, lease)) in [
            ("workspace", "api", "old"),
            ("workspace", "api", "new"),
            ("workspace", "web", "web"),
            ("single", "api", ""),
        ]
        .iter()
        .enumerate()
        {
            watchers.insert(
                (window.to_string(), project.to_string(), lease.to_string()),
                flags[index].clone(),
            );
        }
        stop_watchers(&mut watchers, "workspace", Some("api"), Some("old"));
        assert!(flags[0].load(Ordering::Relaxed));
        assert!(flags[1..].iter().all(|flag| !flag.load(Ordering::Relaxed)));
        stop_watchers(&mut watchers, "workspace", None, None);
        assert!(flags[..3].iter().all(|flag| flag.load(Ordering::Relaxed)));
        assert!(!flags[3].load(Ordering::Relaxed));
    }

    #[test]
    fn fingerprints_react_to_create_change_and_delete() {
        let dir = std::env::temp_dir().join(format!("speccify-watch-test-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join(".agent/specs")).unwrap();
        std::fs::create_dir_all(dir.join(".agent/plans")).unwrap();

        let base = area_fingerprints(&dir);
        // Unverändert ⇒ stabil.
        assert!(changed_areas(&base, &area_fingerprints(&dir)).is_empty());

        // Neue Datei ⇒ nur der Board-Bereich meldet sich.
        std::fs::write(
            dir.join(".agent/specs/t-1.md"),
            "---\nstation: Backlog\n---\n",
        )
        .unwrap();
        let created = area_fingerprints(&dir);
        assert_eq!(changed_areas(&base, &created), vec!["board"]);

        // In-place-Änderung (andere Länge ⇒ unabhängig von mtime-Auflösung).
        std::fs::write(
            dir.join(".agent/specs/t-1.md"),
            "---\nstation: Doing\n---\nmehr\n",
        )
        .unwrap();
        let edited = area_fingerprints(&dir);
        assert_eq!(changed_areas(&created, &edited), vec!["board"]);

        // Datei in einem Unterverzeichnis (History) zählt mit.
        std::fs::create_dir_all(dir.join(".agent/specs/history/t-1")).unwrap();
        std::fs::write(dir.join(".agent/specs/history/t-1/index.jsonl"), "{}\n").unwrap();
        let history = area_fingerprints(&dir);
        assert_eq!(changed_areas(&edited, &history), vec!["board"]);

        // Einzeldatei-Bereich (agent) reagiert auf CLAUDE.md.
        std::fs::write(dir.join("CLAUDE.md"), "# x\n").unwrap();
        let agent = area_fingerprints(&dir);
        assert_eq!(changed_areas(&history, &agent), vec!["agent"]);

        // Löschen ⇒ wieder nur board.
        std::fs::remove_file(dir.join(".agent/specs/t-1.md")).unwrap();
        let deleted = area_fingerprints(&dir);
        assert_eq!(changed_areas(&agent, &deleted), vec!["board"]);

        let _ = std::fs::remove_dir_all(&dir);
    }
}
