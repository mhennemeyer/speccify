//! Befehls-Allowlist (Sicherheitsmodell des Exec-MCP), 1:1 nach der
//! dotagent-Referenz (`docs/exec-mcp-contract.md`): nur explizit
//! freigegebene Befehle laufen, Matching per **Token-Präfix** (shlex),
//! `permanent: false` = Einmal-Freigabe (nach Lauf konsumiert), abgelehnte
//! Befehle landen dedupliziert als Pending-Request.

use std::path::{Path, PathBuf};

use serde_json::{Value, json};

pub const ALLOWLIST_FILE: &str = "exec-allowlist.json";
pub const PENDING_FILE: &str = "exec-pending.json";

#[derive(Clone)]
pub struct Entry {
    pub pattern: String,
    pub permanent: bool,
}

pub struct Allowlist {
    agent_dir: PathBuf,
}

impl Allowlist {
    pub fn new(agent_dir: PathBuf) -> Self {
        Self { agent_dir }
    }

    fn allowlist_path(&self) -> PathBuf {
        self.agent_dir.join(ALLOWLIST_FILE)
    }

    fn pending_path(&self) -> PathBuf {
        self.agent_dir.join(PENDING_FILE)
    }

    pub fn entries(&self) -> Vec<Entry> {
        let Ok(text) = std::fs::read_to_string(self.allowlist_path()) else {
            return Vec::new();
        };
        let Ok(Value::Array(items)) = serde_json::from_str::<Value>(&text) else {
            return Vec::new();
        };
        items
            .into_iter()
            .filter_map(|item| {
                let pattern = item.get("pattern")?.as_str()?.to_string();
                let permanent = item
                    .get("permanent")
                    .and_then(Value::as_bool)
                    .unwrap_or(true);
                Some(Entry { pattern, permanent })
            })
            .collect()
    }

    fn save_entries(&self, entries: &[Entry]) -> std::io::Result<()> {
        std::fs::create_dir_all(&self.agent_dir)?;
        let payload = Value::Array(
            entries
                .iter()
                .map(|entry| json!({"pattern": entry.pattern, "permanent": entry.permanent}))
                .collect(),
        );
        let json = serde_json::to_string_pretty(&payload).unwrap_or_else(|_| "[]".into());
        std::fs::write(self.allowlist_path(), json + "\n")
    }

    /// Erster Eintrag, dessen Token-Präfix `command` matcht.
    fn matched(&self, command: &str) -> Option<Entry> {
        let command_tokens = shlex::split(command)?;
        for entry in self.entries() {
            let Some(pattern_tokens) = shlex::split(&entry.pattern) else {
                continue;
            };
            if pattern_tokens.is_empty() {
                continue;
            }
            if command_tokens.len() >= pattern_tokens.len()
                && command_tokens[..pattern_tokens.len()] == pattern_tokens[..]
            {
                return Some(entry);
            }
        }
        None
    }

    pub fn is_allowed(&self, command: &str) -> bool {
        self.matched(command).is_some()
    }

    /// Entfernt einen passenden Einmal-Eintrag (`permanent: false`) nach
    /// erfolgreichem Lauf. Permanente Einträge bleiben.
    pub fn consume(&self, command: &str) {
        let Some(entry) = self.matched(command) else {
            return;
        };
        if entry.permanent {
            return;
        }
        let remaining: Vec<Entry> = self
            .entries()
            .into_iter()
            .filter(|candidate| !(candidate.pattern == entry.pattern && !candidate.permanent))
            .collect();
        let _ = self.save_entries(&remaining);
    }

    /// Notiert einen abgelehnten Befehl zur Freigabe — dedupliziert nach
    /// Befehlstext (kein Spam bei Agent-Retries).
    pub fn record_pending(&self, command: &str) {
        let path = self.pending_path();
        let mut pending = match std::fs::read_to_string(&path) {
            Ok(text) => match serde_json::from_str::<Value>(&text) {
                Ok(Value::Array(items)) => items,
                _ => Vec::new(),
            },
            Err(_) => Vec::new(),
        };
        if pending
            .iter()
            .any(|item| item.get("command").and_then(Value::as_str) == Some(command))
        {
            return;
        }
        pending.push(json!({"command": command, "requested_at": utc_now_iso()}));
        if std::fs::create_dir_all(&self.agent_dir).is_err() {
            return;
        }
        let json =
            serde_json::to_string_pretty(&Value::Array(pending)).unwrap_or_else(|_| "[]".into());
        let _ = std::fs::write(path, json + "\n");
    }
}

/// UTC-Zeitstempel `YYYY-MM-DDTHH:MM:SSZ` (dependency-frei, Civil-from-days).
fn utc_now_iso() -> String {
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let days = (secs / 86_400) as i64;
    let rem = secs % 86_400;
    let (hour, minute, second) = (rem / 3600, (rem % 3600) / 60, rem % 60);
    // Howard Hinnant's civil_from_days.
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let year = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = if month <= 2 { year + 1 } else { year };
    format!("{year:04}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}Z")
}

/// Hilfsfunktion für die Datei-Pfade (Tests/Server).
pub fn agent_dir(project_root: &Path) -> PathBuf {
    project_root.join(".agent")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_agent(label: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-allow-{label}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn token_prefix_matching() {
        let dir = temp_agent("match");
        std::fs::write(
            dir.join(ALLOWLIST_FILE),
            r#"[{"pattern":"npm test","permanent":true}]"#,
        )
        .unwrap();
        let allow = Allowlist::new(dir.clone());
        assert!(allow.is_allowed("npm test"));
        assert!(allow.is_allowed("npm test --watchAll=false"));
        assert!(!allow.is_allowed("npm testfoo"));
        assert!(!allow.is_allowed("npm install"));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn consume_removes_only_oneshot() {
        let dir = temp_agent("consume");
        std::fs::write(
            dir.join(ALLOWLIST_FILE),
            r#"[{"pattern":"echo","permanent":true},{"pattern":"printf","permanent":false}]"#,
        )
        .unwrap();
        let allow = Allowlist::new(dir.clone());
        allow.consume("printf hi");
        let patterns: Vec<String> = allow.entries().into_iter().map(|e| e.pattern).collect();
        assert_eq!(patterns, vec!["echo"]);
        allow.consume("echo hi"); // permanent → bleibt
        assert_eq!(allow.entries().len(), 1);
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn pending_dedupes() {
        let dir = temp_agent("pending");
        let allow = Allowlist::new(dir.clone());
        allow.record_pending("git status");
        allow.record_pending("git status");
        let text = std::fs::read_to_string(dir.join(PENDING_FILE)).unwrap();
        let items: Value = serde_json::from_str(&text).unwrap();
        assert_eq!(items.as_array().unwrap().len(), 1);
        assert_eq!(items[0]["command"], "git status");
        assert!(items[0]["requested_at"].is_string());
        let _ = std::fs::remove_dir_all(&dir);
    }
}
