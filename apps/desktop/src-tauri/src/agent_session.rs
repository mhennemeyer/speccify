//! Session identity for the agent terminal (Spec 009, D4/D5/D6).
//!
//! The app knows a session only when the host lets it choose the id at start
//! (Claude Code: `--session-id`). Resuming then targets exactly that session
//! (`--resume <id>`) after checking the host's own session store. Codex assigns
//! its ids itself, so the visible picker (`codex resume`, filtered by the host
//! to the current directory) is the explicit choice; `--last`/`--continue`
//! remain a labelled convenience and are never started automatically. Free
//! shell commands never get a resume flag appended.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AgentSession {
    pub host: String,
    /// `None`: the host did not expose an id at start (Codex).
    pub id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Deserialize)]
#[serde(tag = "mode", rename_all = "lowercase")]
pub enum SessionRequest {
    /// Fresh session; known hosts get an app-generated identity where possible.
    New,
    /// Exactly this session; fails visibly when it is unknown or gone.
    Resume { host: String, id: Option<String> },
    /// The host's interactive picker.
    Pick,
    /// The host's "most recent session" convenience — not this session.
    Latest,
}

impl Default for SessionRequest {
    fn default() -> Self {
        Self::New
    }
}

/// Host name of a plain agent command (`claude`, `codex`), `None` for a free
/// shell command or an empty command.
pub fn host_of(command: &str) -> Option<String> {
    let argv = crate::agent_startup::known_host(command)?;
    let name = argv
        .first()?
        .rsplit(['/', '\\'])
        .next()?
        .trim_end_matches(".cmd")
        .trim_end_matches(".exe")
        .to_owned();
    Some(name)
}

fn has_resume_option(argv: &[String]) -> bool {
    argv.iter().skip(1).any(|arg| {
        matches!(
            arg.as_str(),
            "--continue" | "-c" | "--resume" | "-r" | "--session-id" | "resume" | "fork"
        ) || arg.starts_with("--resume=")
            || arg.starts_with("--session-id=")
    })
}

fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 64
        && id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
}

/// Builds the launch line for `request` on top of the diagnosed `launch`
/// (already quoted, executable resolved). `command` is the user's original
/// command and decides host and free-command handling. Returns the launch
/// line and the identity the app will remember.
pub fn session_launch(
    command: &str,
    launch: &str,
    request: &SessionRequest,
    home: &Path,
) -> Result<(String, Option<AgentSession>), String> {
    let argv = crate::agent_startup::known_host(command);
    let Some(argv) = argv else {
        return match request {
            SessionRequest::New => Ok((launch.to_owned(), None)),
            _ => Err("Freies Shell-Kommando: kein automatisches Fortsetzen. Resume-Option selbst ins Kommando schreiben oder ein Host-Kommando (claude, codex) wählen.".into()),
        };
    };
    let host = host_of(command).unwrap_or_default();
    if has_resume_option(&argv) {
        return match request {
            SessionRequest::New => Ok((launch.to_owned(), None)),
            _ => Err(format!("Das Kommando enthält bereits eine Sitzungsoption ({}); die App hängt keine zweite an.", argv[1..].join(" "))),
        };
    }
    match request {
        SessionRequest::New => Ok(match host.as_str() {
            "claude" => {
                let id = uuid::Uuid::new_v4().to_string();
                (
                    format!("{launch} --session-id {id}"),
                    Some(AgentSession {
                        host,
                        id: Some(id),
                    }),
                )
            }
            _ => (launch.to_owned(), Some(AgentSession { host, id: None })),
        }),
        SessionRequest::Resume {
            host: wanted,
            id: Some(id),
        } => {
            if *wanted != host {
                return Err(format!(
                    "Die gemerkte Sitzung gehört zu {wanted}, das Kommando startet {host}. Sitzung auswählen oder neu starten."
                ));
            }
            if !valid_id(id) {
                return Err("Ungültige Sitzungs-ID im Merker. Sitzung auswählen oder neu starten.".into());
            }
            if !session_exists(&host, id, home) {
                return Err(format!(
                    "Die gemerkte Sitzung {} wurde im Speicher von {host} nicht gefunden. Sitzung auswählen oder neu starten.",
                    short_id(id)
                ));
            }
            let line = match host.as_str() {
                "claude" => format!("{launch} --resume {id}"),
                _ => format!("{launch} resume {id}"),
            };
            Ok((
                line,
                Some(AgentSession {
                    host,
                    id: Some(id.clone()),
                }),
            ))
        }
        SessionRequest::Resume { host: wanted, .. } if *wanted != host => Err(format!(
            "Die gemerkte Sitzung gehört zu {wanted}, das Kommando startet {host}. Sitzung auswählen oder neu starten."
        )),
        SessionRequest::Resume { .. } | SessionRequest::Pick => Ok((
            match host.as_str() {
                "claude" => format!("{launch} --resume"),
                _ => format!("{launch} resume"),
            },
            Some(AgentSession { host, id: None }),
        )),
        SessionRequest::Latest => Ok((
            match host.as_str() {
                "claude" => format!("{launch} --continue"),
                _ => format!("{launch} resume --last"),
            },
            Some(AgentSession { host, id: None }),
        )),
    }
}

pub fn short_id(id: &str) -> String {
    id.chars().take(8).collect()
}

/// Whether the host's own session store holds `id`. Claude Code keeps
/// `~/.claude/projects/<encoded cwd>/<id>.jsonl`; the encoding is the host's
/// business, so every project folder is searched. Codex keeps
/// `~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<id>.jsonl`.
pub fn session_exists(host: &str, id: &str, home: &Path) -> bool {
    if !valid_id(id) {
        return false;
    }
    match host {
        "claude" => {
            let file = format!("{id}.jsonl");
            read_dir(&home.join(".claude").join("projects"))
                .iter()
                .any(|dir| dir.join(&file).is_file())
        }
        "codex" => {
            let suffix = format!("-{id}.jsonl");
            any_file(&home.join(".codex").join("sessions"), &suffix, 4)
        }
        _ => false,
    }
}

fn read_dir(dir: &Path) -> Vec<PathBuf> {
    std::fs::read_dir(dir)
        .map(|entries| entries.flatten().map(|entry| entry.path()).collect())
        .unwrap_or_default()
}

fn any_file(dir: &Path, suffix: &str, depth: usize) -> bool {
    read_dir(dir).iter().any(|path| {
        if path.is_dir() {
            depth > 0 && any_file(path, suffix, depth - 1)
        } else {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.ends_with(suffix))
        }
    })
}

/// Read-only probe for the UI before it offers "resume".
#[tauri::command]
pub fn agent_session_check(host: String, id: String) -> Result<bool, String> {
    let home = crate::settings::home_dir()?;
    Ok(session_exists(&host, &id, &home))
}

/// Incremental UTF-8 decoder for PTY output (Spec 009, D6): a multi-byte
/// character split across two reads is reassembled; invalid bytes become
/// U+FFFD; an incomplete tail at process end is flushed as U+FFFD.
#[derive(Default)]
pub struct Utf8Chunker {
    pending: Vec<u8>,
}

impl Utf8Chunker {
    pub fn push(&mut self, bytes: &[u8]) -> String {
        self.pending.extend_from_slice(bytes);
        let mut out = String::with_capacity(self.pending.len());
        let mut input: &[u8] = &self.pending;
        loop {
            match std::str::from_utf8(input) {
                Ok(text) => {
                    out.push_str(text);
                    input = &[];
                    break;
                }
                Err(error) => {
                    let valid = error.valid_up_to();
                    out.push_str(std::str::from_utf8(&input[..valid]).unwrap_or_default());
                    match error.error_len() {
                        Some(skip) => {
                            out.push('\u{FFFD}');
                            input = &input[valid + skip..];
                        }
                        None => {
                            input = &input[valid..];
                            break;
                        }
                    }
                }
            }
        }
        self.pending = input.to_vec();
        out
    }

    pub fn finish(&mut self) -> String {
        if self.pending.is_empty() {
            return String::new();
        }
        self.pending.clear();
        "\u{FFFD}".into()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chunker_reassembles_characters_split_across_reads() {
        let text = "ä€😀 ok";
        let bytes = text.as_bytes();
        for split in 1..bytes.len() {
            let mut chunker = Utf8Chunker::default();
            let mut joined = chunker.push(&bytes[..split]);
            joined.push_str(&chunker.push(&bytes[split..]));
            joined.push_str(&chunker.finish());
            assert_eq!(joined, text, "split at {split}");
        }
    }

    #[test]
    fn chunker_replaces_invalid_bytes_and_flushes_incomplete_tail() {
        let mut chunker = Utf8Chunker::default();
        assert_eq!(chunker.push(b"a\xffb"), "a\u{FFFD}b");
        assert_eq!(chunker.push(&"€".as_bytes()[..2]), "");
        assert_eq!(chunker.finish(), "\u{FFFD}");
        assert_eq!(chunker.finish(), "");
        // Escape sequences are plain ASCII and pass through untouched.
        assert_eq!(chunker.push(b"\x1b[31mrot\x1b[0m"), "\x1b[31mrot\x1b[0m");
    }

    fn store() -> tempfile::TempDir {
        let home = tempfile::tempdir().unwrap();
        let claude = home
            .path()
            .join(".claude/projects/-Users-me-Desktop-Work-app");
        std::fs::create_dir_all(&claude).unwrap();
        std::fs::write(
            claude.join("11111111-2222-4333-8444-555555555555.jsonl"),
            "{}",
        )
        .unwrap();
        let codex = home.path().join(".codex/sessions/2026/09/12");
        std::fs::create_dir_all(&codex).unwrap();
        std::fs::write(
            codex.join("rollout-2026-09-12T08-00-00-01a0aaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee.jsonl"),
            "{}",
        )
        .unwrap();
        home
    }

    #[test]
    fn session_store_lookup_per_host() {
        let home = store();
        assert!(session_exists(
            "claude",
            "11111111-2222-4333-8444-555555555555",
            home.path()
        ));
        assert!(!session_exists(
            "claude",
            "01a0aaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee",
            home.path()
        ));
        assert!(session_exists(
            "codex",
            "01a0aaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee",
            home.path()
        ));
        assert!(!session_exists("codex", "missing", home.path()));
        assert!(!session_exists("claude", "../../etc/passwd", home.path()));
        assert!(!session_exists("other", "x", home.path()));
    }

    #[test]
    fn new_sessions_get_an_identity_only_where_the_host_accepts_one() {
        let home = store();
        let (line, session) = session_launch(
            "claude",
            "/opt/bin/claude",
            &SessionRequest::New,
            home.path(),
        )
        .unwrap();
        let session = session.unwrap();
        assert_eq!(session.host, "claude");
        let id = session.id.unwrap();
        assert_eq!(id.len(), 36);
        assert_eq!(line, format!("/opt/bin/claude --session-id {id}"));

        let (line, session) =
            session_launch("codex", "/opt/bin/codex", &SessionRequest::New, home.path()).unwrap();
        assert_eq!(line, "/opt/bin/codex");
        assert_eq!(
            session,
            Some(AgentSession {
                host: "codex".into(),
                id: None
            })
        );

        for free in ["", "my-host", "claude && echo hi", "claude --continue"] {
            let (line, session) =
                session_launch(free, free, &SessionRequest::New, home.path()).unwrap();
            assert_eq!(line, free);
            assert!(session.is_none(), "{free}");
        }
    }

    #[test]
    fn resume_targets_exactly_the_known_session() {
        let home = store();
        let request = SessionRequest::Resume {
            host: "claude".into(),
            id: Some("11111111-2222-4333-8444-555555555555".into()),
        };
        let (line, session) = session_launch(
            "claude --model opus",
            "/opt/bin/claude --model opus",
            &request,
            home.path(),
        )
        .unwrap();
        assert_eq!(
            line,
            "/opt/bin/claude --model opus --resume 11111111-2222-4333-8444-555555555555"
        );
        assert_eq!(
            session.unwrap().id.as_deref(),
            Some("11111111-2222-4333-8444-555555555555")
        );

        let codex = SessionRequest::Resume {
            host: "codex".into(),
            id: Some("01a0aaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee".into()),
        };
        let (line, _) = session_launch("codex", "/opt/bin/codex", &codex, home.path()).unwrap();
        assert_eq!(
            line,
            "/opt/bin/codex resume 01a0aaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee"
        );
    }

    #[test]
    fn resume_fails_visibly_instead_of_appending_blindly() {
        let home = store();
        let known = SessionRequest::Resume {
            host: "claude".into(),
            id: Some("11111111-2222-4333-8444-555555555555".into()),
        };
        let gone = SessionRequest::Resume {
            host: "claude".into(),
            id: Some("99999999-2222-4333-8444-555555555555".into()),
        };
        // Host changed since the session was recorded.
        let error = session_launch("codex", "/opt/bin/codex", &known, home.path()).unwrap_err();
        assert!(error.contains("gehört zu claude"), "{error}");
        // Session vanished from the host store.
        let error = session_launch("claude", "/opt/bin/claude", &gone, home.path()).unwrap_err();
        assert!(error.contains("nicht gefunden"), "{error}");
        // Command already carries a session option.
        let error = session_launch(
            "claude --continue",
            "/opt/bin/claude --continue",
            &known,
            home.path(),
        )
        .unwrap_err();
        assert!(error.contains("bereits"), "{error}");
        // Free command: nothing is appended.
        let error = session_launch(
            "claude && echo hi",
            "claude && echo hi",
            &known,
            home.path(),
        )
        .unwrap_err();
        assert!(error.contains("Freies Shell-Kommando"), "{error}");
        assert!(session_launch("", "", &SessionRequest::Latest, home.path()).is_err());
    }

    #[test]
    fn picker_and_latest_are_labelled_conveniences_without_identity() {
        let home = store();
        let legacy = SessionRequest::Resume {
            host: "codex".into(),
            id: None,
        };
        let (line, session) =
            session_launch("codex", "/opt/bin/codex", &legacy, home.path()).unwrap();
        assert_eq!(line, "/opt/bin/codex resume");
        assert_eq!(session.unwrap().id, None);
        let (line, _) = session_launch(
            "claude",
            "/opt/bin/claude",
            &SessionRequest::Pick,
            home.path(),
        )
        .unwrap();
        assert_eq!(line, "/opt/bin/claude --resume");
        let (line, _) = session_launch(
            "claude",
            "/opt/bin/claude",
            &SessionRequest::Latest,
            home.path(),
        )
        .unwrap();
        assert_eq!(line, "/opt/bin/claude --continue");
        let (line, _) = session_launch(
            "codex",
            "/opt/bin/codex",
            &SessionRequest::Latest,
            home.path(),
        )
        .unwrap();
        assert_eq!(line, "/opt/bin/codex resume --last");
        assert_eq!(host_of("claude.cmd --model x").as_deref(), Some("claude"));
        assert_eq!(host_of("claude | tee log"), None);
    }
}
