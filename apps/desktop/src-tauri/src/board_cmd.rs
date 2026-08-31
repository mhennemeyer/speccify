//! Ticket-Lifecycle + History + KPIs (Plan projektfenster.md, P5/W3, D27).
//!
//! Die App schreibt Tickets **byte-stabil**: bekannte Frontmatter-Zeilen
//! werden ersetzt oder ergänzt, unbekannte bleiben in Reihenfolge erhalten
//! (agentgeschriebene Felder überleben jede UI-Aktion). Jede App-Änderung
//! loggt eine Zeile in `.agent/board/history/<id>/index.jsonl` mit
//! `actor: "user"` — `agent_run`-Zeilen schreibt der Agent selbst (D26);
//! die KPI-Kopfzeile rechnet daraus. Effektiver Input = tokens_in +
//! cache_read + cache_write (sonst „mehr out als in", iKanban-Befund).

use std::hash::{Hash, Hasher};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::project_cmd::{resolve_project_root, safe_project_path, BOARD_STATIONS};

fn now_iso() -> String {
    time::OffsetDateTime::now_utc()
        .replace_nanosecond(0)
        .unwrap_or_else(|_| time::OffsetDateTime::now_utc())
        .format(&time::format_description::well_known::Rfc3339)
        .unwrap_or_default()
}

fn write_atomic(path: &Path, content: &str) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let tmp = path.with_extension("tmp-speccify");
    std::fs::write(&tmp, content).map_err(|e| format!("{}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, path).map_err(|e| format!("{}: {e}", path.display()))
}

// --- History (append-only JSONL) ---------------------------------------------

#[derive(Serialize, Deserialize, Clone)]
pub struct HistoryEvent {
    pub timestamp: String,
    pub ticket_id: String,
    pub event_type: String,
    pub actor: String,
    pub summary: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tokens_in: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tokens_out: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tokens_cache_read: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tokens_cache_write: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub duration_ms: Option<u64>,
}

fn history_dir(root: &Path, ticket_id: &str) -> PathBuf {
    root.join(".agent/board/history").join(ticket_id)
}

/// Hängt ein User-Event an — Fehler beim Loggen brechen die eigentliche
/// Aktion nicht ab (History ist Protokoll, nicht Transaktion).
pub(crate) fn log_user_event(root: &Path, ticket_id: &str, event_type: &str, summary: String) {
    let event = HistoryEvent {
        timestamp: now_iso(),
        ticket_id: ticket_id.into(),
        event_type: event_type.into(),
        actor: "user".into(),
        summary,
        tokens_in: None,
        tokens_out: None,
        tokens_cache_read: None,
        tokens_cache_write: None,
        duration_ms: None,
    };
    let dir = history_dir(root, ticket_id);
    if std::fs::create_dir_all(&dir).is_err() {
        return;
    }
    if let Ok(line) = serde_json::to_string(&event) {
        use std::io::Write;
        if let Ok(mut file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(dir.join("index.jsonl"))
        {
            let _ = writeln!(file, "{line}");
        }
    }
}

fn read_history(root: &Path, ticket_id: &str) -> Vec<HistoryEvent> {
    let Ok(text) = std::fs::read_to_string(history_dir(root, ticket_id).join("index.jsonl")) else {
        return Vec::new();
    };
    // Tolerant: korrupte Zeilen überspringen (der Agent tippt das von Hand).
    text.lines()
        .filter_map(|line| serde_json::from_str(line).ok())
        .collect()
}

/// History eines Tickets, neueste zuerst (die UI deckelt die Anzeige).
#[tauri::command]
pub fn project_ticket_history(
    project: String,
    ticket_id: String,
) -> Result<Vec<HistoryEvent>, String> {
    if ticket_id.contains('/') || ticket_id.contains('\\') || ticket_id.contains("..") {
        return Err(format!("Keine Ticket-Id: {ticket_id}"));
    }
    let root = resolve_project_root(&project)?;
    let mut events = read_history(&root, &ticket_id);
    events.reverse();
    Ok(events)
}

// --- KPIs aus agent_run-Events ------------------------------------------------

#[derive(Serialize)]
pub struct RunEntry {
    ticket_id: String,
    timestamp: String,
    summary: String,
    /// Effektiver Input: in + cache_read + cache_write.
    tokens_in: u64,
    tokens_out: u64,
    duration_ms: u64,
}

#[derive(Serialize)]
pub struct KpiSummary {
    run_count: u64,
    tokens_in: u64,
    tokens_out: u64,
    duration_ms: u64,
    /// Letzte Läufe, neueste zuerst (gedeckelt).
    recent: Vec<RunEntry>,
}

#[tauri::command]
pub fn project_board_kpis(project: String) -> Result<KpiSummary, String> {
    let root = resolve_project_root(&project)?;
    let mut runs: Vec<RunEntry> = Vec::new();
    if let Ok(entries) = std::fs::read_dir(root.join(".agent/board/history")) {
        for entry in entries.filter_map(Result::ok) {
            let ticket_id = entry.file_name().to_string_lossy().into_owned();
            for event in read_history(&root, &ticket_id) {
                if event.event_type != "agent_run" {
                    continue;
                }
                runs.push(RunEntry {
                    ticket_id: event.ticket_id,
                    timestamp: event.timestamp,
                    summary: event.summary,
                    tokens_in: event.tokens_in.unwrap_or(0)
                        + event.tokens_cache_read.unwrap_or(0)
                        + event.tokens_cache_write.unwrap_or(0),
                    tokens_out: event.tokens_out.unwrap_or(0),
                    duration_ms: event.duration_ms.unwrap_or(0),
                });
            }
        }
    }
    runs.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
    let summary = KpiSummary {
        run_count: runs.len() as u64,
        tokens_in: runs.iter().map(|r| r.tokens_in).sum(),
        tokens_out: runs.iter().map(|r| r.tokens_out).sum(),
        duration_ms: runs.iter().map(|r| r.duration_ms).sum(),
        recent: runs.into_iter().take(20).collect(),
    };
    Ok(summary)
}

// --- Byte-stabile Frontmatter-Updates -----------------------------------------

/// Ersetzt/ergänzt bekannte Frontmatter-Zeilen; `None` entfernt die Zeile.
/// Unbekannte Zeilen bleiben in Reihenfolge erhalten. Optional neuer Body.
/// (Generisch für flaches `---`-Frontmatter — auch Pläne nutzen es, W6.)
pub(crate) fn update_ticket_text(
    text: &str,
    updates: &[(&str, Option<String>)],
    new_body: Option<&str>,
) -> Result<String, String> {
    let mut lines = text.split_inclusive('\n');
    if lines.next().map(str::trim_end) != Some("---") {
        return Err("Kein Frontmatter (erste Zeile ist kein ---).".into());
    }
    let mut frontmatter: Vec<String> = Vec::new();
    let mut consumed = text.find('\n').unwrap_or(0) + 1;
    let mut body_start = None;
    for line in lines {
        consumed += line.len();
        if line.trim_end() == "---" {
            body_start = Some(consumed);
            break;
        }
        frontmatter.push(line.trim_end_matches(['\n', '\r']).to_string());
    }
    let Some(body_start) = body_start else {
        return Err("Frontmatter-Endmarker --- fehlt.".into());
    };

    let mut remaining: Vec<(&str, Option<String>)> = updates.to_vec();
    let mut kept: Vec<String> = Vec::new();
    for line in frontmatter {
        let key = line.split(':').next().unwrap_or("").trim().to_string();
        if let Some(position) = remaining
            .iter()
            .position(|(k, _)| k.eq_ignore_ascii_case(&key))
        {
            let (name, value) = remaining.remove(position);
            match value {
                Some(value) => kept.push(format!("{name}: {value}")),
                None => {} // Zeile entfernen
            }
        } else {
            kept.push(line);
        }
    }
    for (name, value) in remaining {
        if let Some(value) = value {
            kept.push(format!("{name}: {value}"));
        }
    }

    let body = match new_body {
        Some(body) => {
            let mut body = body.to_string();
            if !body.is_empty() && !body.ends_with('\n') {
                body.push('\n');
            }
            body
        }
        None => text[body_start..].to_string(),
    };
    Ok(format!("---\n{}\n---\n{}", kept.join("\n"), body))
}

// --- Ticket-Mutationen ---------------------------------------------------------

fn slugify(title: &str) -> String {
    let mut slug = String::new();
    for ch in title.to_lowercase().chars() {
        if ch.is_ascii_alphanumeric() {
            slug.push(ch);
        } else if !slug.ends_with('-') && !slug.is_empty() {
            slug.push('-');
        }
    }
    let slug = slug.trim_matches('-').to_string();
    if slug.is_empty() {
        "ticket".into()
    } else {
        slug.chars().take(48).collect()
    }
}

fn short_suffix(seed: &str) -> String {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    seed.hash(&mut hasher);
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0)
        .hash(&mut hasher);
    format!("{:04x}", hasher.finish() & 0xffff)
}

#[tauri::command]
pub fn project_ticket_create(
    project: String,
    title: String,
    station: String,
    body: String,
    needs_human: bool,
    plan: Option<String>,
    order: Option<i64>,
) -> Result<String, String> {
    if !BOARD_STATIONS.contains(&station.as_str()) {
        return Err(format!("Unbekannte Station: {station}"));
    }
    let title = title.trim();
    if title.is_empty() {
        return Err("Titel fehlt.".into());
    }
    let root = resolve_project_root(&project)?;
    let board = root.join(".agent/board");
    let base = slugify(title);
    let mut id = format!("{base}-{}", short_suffix(title));
    for _ in 0..8 {
        if !board.join(format!("{id}.md")).exists() {
            break;
        }
        id = format!("{base}-{}", short_suffix(&id));
    }

    let mut frontmatter = vec![
        format!("id: {id}"),
        format!("title: {title}"),
        format!("station: {station}"),
    ];
    if let Some(order) = order {
        frontmatter.push(format!("order: {order}"));
    }
    if let Some(plan) = plan.as_deref().map(str::trim).filter(|p| !p.is_empty()) {
        frontmatter.push(format!("plan: {plan}"));
    }
    if needs_human {
        frontmatter.push("needs_human: true".into());
    }
    frontmatter.push(format!("created: {}", now_iso()));

    let mut body = body;
    if !body.is_empty() && !body.ends_with('\n') {
        body.push('\n');
    }
    let text = format!("---\n{}\n---\n{}", frontmatter.join("\n"), body);
    let file = board.join(format!("{id}.md"));
    write_atomic(&file, &text)?;
    log_user_event(
        &root,
        &id,
        "ticket_created",
        format!("Ticket angelegt: {title}"),
    );

    Ok(file
        .strip_prefix(&root)
        .unwrap_or(&file)
        .to_string_lossy()
        .into_owned())
}

#[derive(Deserialize)]
pub struct TicketPatch {
    title: String,
    station: String,
    ready: bool,
    needs_human: bool,
    order: Option<i64>,
    body: String,
}

/// Speichert das Editor-Sheet in einem Rutsch; loggt `station_changed`
/// und/oder `ticket_edited`, je nachdem, was sich wirklich geändert hat.
#[tauri::command]
pub fn project_ticket_save(
    project: String,
    file: String,
    patch: TicketPatch,
) -> Result<(), String> {
    if !BOARD_STATIONS.contains(&patch.station.as_str()) {
        return Err(format!("Unbekannte Station: {}", patch.station));
    }
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    if !path.starts_with(root.join(".agent/board")) {
        return Err(format!("Kein Board-Ticket: {file}"));
    }
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;

    let old_station = text
        .lines()
        .find_map(|line| line.strip_prefix("station:"))
        .map(str::trim)
        .unwrap_or("")
        .to_string();
    let ticket_id = text
        .lines()
        .find_map(|line| line.strip_prefix("id:"))
        .map(str::trim)
        .map(str::to_string)
        .unwrap_or_else(|| {
            path.file_stem()
                .map(|stem| stem.to_string_lossy().into_owned())
                .unwrap_or_default()
        });

    let updates: Vec<(&str, Option<String>)> = vec![
        ("title", Some(patch.title.trim().to_string())),
        ("station", Some(patch.station.clone())),
        ("ready", patch.ready.then(|| "true".into())),
        ("needs_human", patch.needs_human.then(|| "true".into())),
        ("order", patch.order.map(|order| order.to_string())),
    ];
    let updated = update_ticket_text(&text, &updates, Some(&patch.body))?;
    if updated == text {
        return Ok(());
    }
    write_atomic(&path, &updated)?;

    if old_station != patch.station {
        log_user_event(
            &root,
            &ticket_id,
            "station_changed",
            format!("{old_station} -> {}", patch.station),
        );
    }
    log_user_event(
        &root,
        &ticket_id,
        "ticket_edited",
        "Im Editor gespeichert".into(),
    );
    Ok(())
}

#[tauri::command]
pub fn project_ticket_delete(project: String, file: String) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    if !path.starts_with(root.join(".agent/board")) || path.extension().is_none_or(|e| e != "md") {
        return Err(format!("Kein Board-Ticket: {file}"));
    }
    std::fs::remove_file(&path).map_err(|e| format!("{}: {e}", path.display()))
}

// --- Q&A-Protokoll (P5/W4, D27) ------------------------------------------------
// `## Questions` im Ticket-Body: `### Q<n> · open · <ts>` fragt der Agent,
// `### A<n> · bo · <ts>` antwortet der Mensch. Tolerant lesen (Trenner ·,
// - oder |, Marker optional — der Agent tippt das von Hand), kanonisch
// schreiben. `open_question` im Frontmatter zeigt immer auf die älteste
// offene Frage; `needs_human` bleibt davon getrennt (Antworten dürfen die
// Abnahme-Markierung nicht löschen).

#[derive(Serialize, Clone)]
pub struct TicketQuestion {
    pub number: u32,
    pub open: bool,
    pub asked_at: Option<String>,
    pub text: String,
    pub answer: Option<String>,
    pub answered_at: Option<String>,
}

/// Kopfzeile `Q3 · open · 2026-…` → (ist_frage, nummer, timestamp).
fn parse_entry_head(head: &str) -> Option<(bool, u32, Option<String>)> {
    let mut parts = head.split(['·', '-', '|']).map(str::trim);
    let first = parts.next()?;
    let (kind, digits) = first.split_at(1);
    let is_question = match kind {
        "Q" | "q" => true,
        "A" | "a" => false,
        _ => return None,
    };
    let number: u32 = digits.trim().parse().ok()?;
    // Marker (open/bo) und Timestamp sind optional; der Timestamp ist das
    // erste Teilstück, das wie eine Jahreszahl beginnt. (Der `-`-Trenner
    // zerlegt ISO-Daten — dann bleibt eben nur das Jahr; tolerant genug.)
    let timestamp = parts
        .map(str::to_string)
        .find(|part| part.len() >= 4 && part.chars().take(4).all(|c| c.is_ascii_digit()));
    Some((is_question, number, timestamp))
}

/// Fragen samt Antworten aus einem Ticket-Body, älteste zuerst.
pub(crate) fn parse_questions(body: &str) -> Vec<TicketQuestion> {
    let mut questions: Vec<TicketQuestion> = Vec::new();
    let mut answers: Vec<(u32, String, Option<String>)> = Vec::new();
    let mut in_section = false;
    let mut current: Option<(bool, u32, Option<String>, Vec<String>)> = None;

    let mut finish = |entry: Option<(bool, u32, Option<String>, Vec<String>)>| {
        if let Some((is_question, number, timestamp, lines)) = entry {
            let text = lines.join("\n").trim().to_string();
            if is_question {
                questions.push(TicketQuestion {
                    number,
                    open: true,
                    asked_at: timestamp,
                    text,
                    answer: None,
                    answered_at: None,
                });
            } else {
                answers.push((number, text, timestamp));
            }
        }
    };

    for line in body.lines() {
        let trimmed = line.trim();
        if trimmed.eq_ignore_ascii_case("## questions") {
            in_section = true;
            continue;
        }
        if !in_section {
            continue;
        }
        if trimmed.starts_with("## ") {
            break; // nächster Abschnitt beendet die Sektion
        }
        if let Some(head) = trimmed.strip_prefix("###") {
            finish(current.take());
            if let Some((is_question, number, timestamp)) = parse_entry_head(head.trim()) {
                current = Some((is_question, number, timestamp, Vec::new()));
            }
            continue;
        }
        if let Some(entry) = current.as_mut() {
            entry.3.push(line.to_string());
        }
    }
    finish(current.take());

    for (number, text, timestamp) in answers {
        if let Some(question) = questions.iter_mut().find(|q| q.number == number) {
            question.open = false;
            question.answer = Some(text);
            question.answered_at = timestamp;
        }
    }
    questions.sort_by_key(|question| question.number);
    questions
}

fn oldest_open(questions: &[TicketQuestion]) -> Option<u32> {
    questions
        .iter()
        .find(|question| question.open)
        .map(|q| q.number)
}

#[tauri::command]
pub fn project_ticket_questions(
    project: String,
    file: String,
) -> Result<Vec<TicketQuestion>, String> {
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    let body = text
        .find("\n---")
        .and_then(|end| text.get(end + 4..))
        .unwrap_or(&text);
    Ok(parse_questions(body))
}

/// Beantwortet Frage `number`: hängt den kanonischen `### A<n>`-Block ans
/// Ende der Questions-Sektion und rückt `open_question` auf die nächste
/// älteste offene Frage weiter (oder entfernt die Zeile).
#[tauri::command]
pub fn project_ticket_answer(
    project: String,
    file: String,
    number: u32,
    text: String,
) -> Result<(), String> {
    let answer_text = text.trim();
    if answer_text.is_empty() {
        return Err("Leere Antwort.".into());
    }
    let root = resolve_project_root(&project)?;
    let path = safe_project_path(&root, &file)?;
    if !path.starts_with(root.join(".agent/board")) {
        return Err(format!("Kein Board-Ticket: {file}"));
    }
    let full = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    let body_offset = full
        .find("\n---")
        .map(|end| {
            let mut offset = end + 4;
            if full[offset..].starts_with('\n') {
                offset += 1;
            }
            offset
        })
        .ok_or("Kein Frontmatter.")?;
    let body = &full[body_offset..];

    let questions = parse_questions(body);
    let Some(question) = questions.iter().find(|q| q.number == number) else {
        return Err(format!("Frage Q{number} gibt es nicht."));
    };
    if !question.open {
        return Err(format!("Q{number} ist schon beantwortet."));
    }

    // Einfügepunkt: Ende der Questions-Sektion (vor dem nächsten `## `-
    // Heading danach, sonst Body-Ende).
    let section_start = body
        .lines()
        .scan(0usize, |offset, line| {
            let here = *offset;
            *offset += line.len() + 1;
            Some((here, line))
        })
        .find(|(_, line)| line.trim().eq_ignore_ascii_case("## questions"))
        .map(|(offset, line)| offset + line.len())
        .ok_or("Keine ## Questions-Sektion.")?;
    let insert_at = body[section_start..]
        .match_indices("\n## ")
        .next()
        .map(|(index, _)| section_start + index)
        .unwrap_or(body.len());

    let block = format!("\n### A{number} · bo · {}\n{answer_text}\n", now_iso());
    let mut new_body = String::with_capacity(body.len() + block.len());
    new_body.push_str(body[..insert_at].trim_end_matches('\n'));
    new_body.push('\n');
    new_body.push_str(&block);
    new_body.push_str(&body[insert_at..]);

    let next_open = oldest_open(&parse_questions(&new_body)).map(|n| format!("Q{n}"));
    let updated = update_ticket_text(&full, &[("open_question", next_open)], Some(&new_body))?;
    write_atomic(&path, &updated)?;

    let ticket_id = full
        .lines()
        .find_map(|line| line.strip_prefix("id:"))
        .map(str::trim)
        .map(str::to_string)
        .unwrap_or_default();
    log_user_event(
        &root,
        &ticket_id,
        "ticket_edited",
        format!("Frage Q{number} beantwortet"),
    );
    Ok(())
}

/// Eine offene Rückfrage fürs Notification-System (W4).
#[derive(Serialize, Clone)]
pub struct OpenQuestion {
    pub ticket_id: String,
    pub title: String,
    /// Dedupe-Schlüssel `<ticket>|Q<n>` — nie zweimal melden.
    pub key: String,
    pub text: String,
}

/// Älteste offene Frage je Ticket (Vertrag: der Agent setzt `open_question`).
pub(crate) fn scan_open_questions(root: &Path) -> Vec<OpenQuestion> {
    let mut open = Vec::new();
    let Ok(entries) = std::fs::read_dir(root.join(".agent/board")) else {
        return open;
    };
    for entry in entries.filter_map(Result::ok) {
        let path = entry.path();
        if path.extension().is_none_or(|ext| ext != "md") {
            continue;
        }
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        let Some((fields, body)) = crate::project_cmd::parse_flat_frontmatter(&text) else {
            continue;
        };
        let Some(marker) = crate::project_cmd::flat_lookup(&fields, "open_question") else {
            continue;
        };
        let Some(number) = marker.trim_start_matches(['Q', 'q']).parse::<u32>().ok() else {
            continue;
        };
        let stem = path
            .file_stem()
            .map(|stem| stem.to_string_lossy().into_owned())
            .unwrap_or_default();
        let ticket_id = crate::project_cmd::flat_lookup(&fields, "id")
            .unwrap_or(&stem)
            .to_string();
        let title = crate::project_cmd::flat_lookup(&fields, "title")
            .unwrap_or(&ticket_id)
            .to_string();
        let question_text = parse_questions(body)
            .into_iter()
            .find(|question| question.number == number && question.open)
            .map(|question| question.text)
            .unwrap_or_default();
        open.push(OpenQuestion {
            key: format!("{ticket_id}|Q{number}"),
            ticket_id,
            title,
            text: question_text,
        });
    }
    open
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(test: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-board-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join(".agent/board")).unwrap();
        dir
    }

    #[test]
    fn questions_parse_tolerantly_and_answer_writes_canonically() {
        // Tolerant: verschiedene Trenner, fehlende Marker, Handschrift.
        let body = "Intro.\n\n## Questions\n\n### Q1 · open · 2026-08-31T10:00:00Z\nErste Frage?\n\n### Q2 - 2026-08-31T11:00:00Z\nZweite Frage,\nzwei Zeilen.\n\n### A1 | bo | 2026-08-31T10:30:00Z\nErste Antwort.\n\n## Notizen\nDanach.\n";
        let questions = parse_questions(body);
        assert_eq!(questions.len(), 2);
        assert!(!questions[0].open);
        assert_eq!(questions[0].answer.as_deref(), Some("Erste Antwort."));
        assert!(questions[1].open);
        assert!(questions[1].text.contains("zwei Zeilen"));
        assert_eq!(oldest_open(&questions), Some(2));

        // Antworten über den Command: kanonischer Block, open_question rückt.
        let dir = fixture("qa");
        let project = dir.to_string_lossy().into_owned();
        let ticket = format!(
            "---\nid: qa-1\ntitle: QA\nstation: Doing\nopen_question: Q1\ncustom: bleibt\n---\n{body}"
        );
        std::fs::write(dir.join(".agent/board/qa-1.md"), &ticket).unwrap();

        // Q1 ist schon beantwortet — der Command verweigert die zweite Antwort.
        let twice = project_ticket_answer(
            project.clone(),
            ".agent/board/qa-1.md".into(),
            1,
            "Nochmal".into(),
        )
        .unwrap_err();
        assert!(twice.contains("schon beantwortet"));

        project_ticket_answer(
            project.clone(),
            ".agent/board/qa-1.md".into(),
            2,
            "Zweite Antwort.".into(),
        )
        .unwrap();
        let saved = std::fs::read_to_string(dir.join(".agent/board/qa-1.md")).unwrap();
        assert!(saved.contains("### A2 · bo · "));
        assert!(saved.contains("custom: bleibt"));
        assert!(!saved.contains("open_question")); // keine offene mehr
        assert!(saved.contains("## Notizen\nDanach.")); // Folgeabschnitt intakt
        let after = project_ticket_questions(project, ".agent/board/qa-1.md".into()).unwrap();
        assert!(after.iter().all(|question| !question.open));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn update_keeps_unknown_fields_in_order() {
        let text = "---\nid: t-1\ntitle: Alt\nstation: Backlog\ncustom: bleibt  so\nmodel: opus\n---\nBody bleibt.\n";
        let updated = update_ticket_text(
            text,
            &[
                ("title", Some("Neu".into())),
                ("ready", Some("true".into())),
                ("station", Some("Doing".into())),
            ],
            None,
        )
        .unwrap();
        assert_eq!(
            updated,
            "---\nid: t-1\ntitle: Neu\nstation: Doing\ncustom: bleibt  so\nmodel: opus\nready: true\n---\nBody bleibt.\n"
        );
        // Entfernen: ready wieder raus, Body ersetzen.
        let cleared = update_ticket_text(&updated, &[("ready", None)], Some("Neuer Body")).unwrap();
        assert_eq!(
            cleared,
            "---\nid: t-1\ntitle: Neu\nstation: Doing\ncustom: bleibt  so\nmodel: opus\n---\nNeuer Body\n"
        );
    }

    #[test]
    fn create_save_history_and_kpis_roundtrip() {
        let dir = fixture("lifecycle");
        let project = dir.to_string_lossy().into_owned();

        let file = project_ticket_create(
            project.clone(),
            "Board-Tab bauen!".into(),
            "Backlog".into(),
            "Erste Fassung.".into(),
            true,
            Some("projektfenster".into()),
            Some(1),
        )
        .unwrap();
        let text = std::fs::read_to_string(dir.join(&file)).unwrap();
        assert!(text.contains("title: Board-Tab bauen!"));
        assert!(text.contains("plan: projektfenster"));
        assert!(text.contains("needs_human: true"));
        let id = text
            .lines()
            .find_map(|l| l.strip_prefix("id: "))
            .unwrap()
            .to_string();
        assert!(id.starts_with("board-tab-bauen-"));

        project_ticket_save(
            project.clone(),
            file.clone(),
            TicketPatch {
                title: "Board-Tab bauen!".into(),
                station: "Doing".into(),
                ready: true,
                needs_human: true,
                order: Some(1),
                body: "Erste Fassung.\n\nMehr.".into(),
            },
        )
        .unwrap();
        let saved = std::fs::read_to_string(dir.join(&file)).unwrap();
        assert!(saved.contains("station: Doing"));
        assert!(saved.contains("ready: true"));
        assert!(saved.ends_with("Mehr.\n"));

        // Agent-Lauf dazu (schreibt der Agent selbst — hier simuliert).
        let run = r#"{"timestamp":"2026-08-31T13:00:00Z","ticket_id":"ID","event_type":"agent_run","actor":"agent:claude","summary":"lief","tokens_in":100,"tokens_out":40,"tokens_cache_read":900,"duration_ms":5000}"#
            .replace("ID", &id);
        use std::io::Write;
        let mut handle = std::fs::OpenOptions::new()
            .append(true)
            .open(
                dir.join(".agent/board/history")
                    .join(&id)
                    .join("index.jsonl"),
            )
            .unwrap();
        writeln!(handle, "{run}").unwrap();
        writeln!(handle, "kaputte zeile die übersprungen wird").unwrap();
        drop(handle);

        let history = project_ticket_history(project.clone(), id.clone()).unwrap();
        assert_eq!(history.len(), 4); // created, station_changed, edited, agent_run
        assert_eq!(history[0].event_type, "agent_run"); // neueste zuerst

        let kpis = project_board_kpis(project.clone()).unwrap();
        assert_eq!(kpis.run_count, 1);
        assert_eq!(kpis.tokens_in, 1000); // 100 + 900 cache_read — effektiv
        assert_eq!(kpis.tokens_out, 40);
        assert_eq!(kpis.recent.len(), 1);

        project_ticket_delete(project.clone(), file.clone()).unwrap();
        assert!(!dir.join(&file).exists());
        let evil = project_ticket_delete(project, ".agent/agent.md".into()).unwrap_err();
        assert!(evil.contains("Kein Board-Ticket"));

        let _ = std::fs::remove_dir_all(&dir);
    }
}
