//! Spec-Lifecycle + History + KPIs (Plan spec-workflow.md, S2; davor
//! projektfenster.md P5/W3 für Tickets — dieselbe Mechanik, jetzt auf
//! `.agent/specs/<slug>/SPEC.md`).
//!
//! Die App schreibt Specs **byte-stabil**: bekannte Frontmatter-Zeilen
//! werden ersetzt oder ergänzt, unbekannte bleiben in Reihenfolge erhalten
//! (agentgeschriebene Felder überleben jede UI-Aktion). Jede App-Änderung
//! loggt eine Zeile in `.agent/specs/<slug>/history.jsonl` mit
//! `actor: "user"` — `agent_run`-Zeilen schreibt der Agent selbst (D26);
//! die KPI-Kopfzeile rechnet daraus. Effektiver Input = tokens_in +
//! cache_read + cache_write (sonst „mehr out als in", iKanban-Befund).
//! Die Tauri-Kommandos heißen aus Kompatibilität weiter `project_ticket_*`
//! / `project_board*`; die Begriffe im UI sind „Spec" und „Specs".

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::project_cmd::writable_spec_path;
use crate::project_cmd::{
    heading_title, resolve_project_root, safe_project_path, spec_dir_of, spec_file_path,
    BOARD_STATIONS, SPECS_DIR,
};

const SPEC_TEMPLATE: &str = include_str!("../templates/spec.md");

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
    /// Slug der Spec; alte Zeilen (`ticket_id`) werden weiter gelesen.
    #[serde(alias = "ticket_id")]
    pub spec_id: String,
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

/// `history.jsonl` liegt neben der SPEC.md — auch im Archiv.
fn history_file(root: &Path, spec_id: &str) -> PathBuf {
    let dir = spec_dir_of(root, spec_id).unwrap_or_else(|| root.join(SPECS_DIR).join(spec_id));
    dir.join("history.jsonl")
}

/// Hängt ein User-Event an — Fehler beim Loggen brechen die eigentliche
/// Aktion nicht ab (History ist Protokoll, nicht Transaktion).
pub(crate) fn log_user_event(root: &Path, spec_id: &str, event_type: &str, summary: String) {
    let event = HistoryEvent {
        timestamp: now_iso(),
        spec_id: spec_id.into(),
        event_type: event_type.into(),
        actor: "user".into(),
        summary,
        tokens_in: None,
        tokens_out: None,
        tokens_cache_read: None,
        tokens_cache_write: None,
        duration_ms: None,
    };
    let file = history_file(root, spec_id);
    if let Some(parent) = file.parent() {
        if std::fs::create_dir_all(parent).is_err() {
            return;
        }
    }
    if let Ok(line) = serde_json::to_string(&event) {
        use std::io::Write;
        if let Ok(mut handle) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(file)
        {
            let _ = writeln!(handle, "{line}");
        }
    }
}

fn read_history(root: &Path, spec_id: &str) -> Vec<HistoryEvent> {
    read_history_path(&history_file(root, spec_id))
}

fn read_history_path(path: &Path) -> Vec<HistoryEvent> {
    let Ok(text) = std::fs::read_to_string(path) else {
        return Vec::new();
    };
    // Tolerant: korrupte Zeilen überspringen (der Agent tippt das von Hand).
    text.lines()
        .filter_map(|line| serde_json::from_str(line).ok())
        .collect()
}

/// History einer Spec, neueste zuerst (die UI deckelt die Anzeige).
#[tauri::command]
pub fn project_ticket_history(
    project: String,
    ticket_id: String,
    file: Option<String>,
) -> Result<Vec<HistoryEvent>, String> {
    if ticket_id.contains('/') || ticket_id.contains('\\') || ticket_id.contains("..") {
        return Err(format!("Keine Spec-Id: {ticket_id}"));
    }
    let root = resolve_project_root(&project)?;
    let mut events = if let Some(file) = file {
        let path = spec_file_path(&root, &file)?;
        if crate::project_cmd::spec_id_of(&root, &path) != ticket_id {
            return Err("Spec-Pfad und Id passen nicht zusammen.".into());
        }
        read_history_path(&path.with_file_name("history.jsonl"))
    } else {
        read_history(&root, &ticket_id)
    };
    events.reverse();
    Ok(events)
}

// --- KPIs aus agent_run-Events ------------------------------------------------

#[derive(Serialize)]
pub struct RunEntry {
    spec_id: String,
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
pub async fn project_board_kpis(project: String) -> Result<KpiSummary, String> {
    tauri::async_runtime::spawn_blocking(move || read_board_kpis(project))
        .await
        .map_err(|error| error.to_string())?
}

fn read_board_kpis(project: String) -> Result<KpiSummary, String> {
    let root = resolve_project_root(&project)?;
    let mut runs: Vec<RunEntry> = Vec::new();
    for dir in crate::project_cmd::spec_dirs(&root, true) {
        let Ok(text) = std::fs::read_to_string(dir.join("history.jsonl")) else {
            continue;
        };
        for event in text
            .lines()
            .filter_map(|line| serde_json::from_str::<HistoryEvent>(line).ok())
        {
            {
                if event.event_type != "agent_run" {
                    continue;
                }
                runs.push(RunEntry {
                    spec_id: event.spec_id,
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

// --- Spec-Mutationen -----------------------------------------------------------

fn slugify(title: &str) -> String {
    let mut slug = String::new();
    for ch in title.to_lowercase().chars() {
        if ch.is_ascii_alphanumeric() {
            slug.push(ch);
        } else if ch == 'ä' || ch == 'ö' || ch == 'ü' || ch == 'ß' {
            slug.push_str(match ch {
                'ä' => "ae",
                'ö' => "oe",
                'ü' => "ue",
                _ => "ss",
            });
        } else if !slug.ends_with('-') && !slug.is_empty() {
            slug.push('-');
        }
    }
    let slug = slug.trim_matches('-').to_string();
    if slug.is_empty() {
        "spec".into()
    } else {
        slug.chars().take(48).collect()
    }
}

/// Body der Vorlage (`templates/spec.md`) ohne deren Frontmatter, Titel
/// eingesetzt — die Abschnitte, die die Policy vom Agenten erwartet.
fn template_body(title: &str) -> String {
    template_body_from(SPEC_TEMPLATE, title)
}

fn template_body_from(template: &str, title: &str) -> String {
    // Git checkouts may materialize bundled templates with CRLF on Windows.
    // Normalize only new template output, never an existing project document.
    let normalized = template.replace("\r\n", "\n");
    let body = normalized
        .splitn(3, "---\n")
        .nth(2)
        .unwrap_or(&normalized)
        .trim_start_matches('\n');
    body.replace("<title>", title)
        .replace("<date>", &now_iso()[..10])
}

/// Legt `.agent/specs/<slug>/SPEC.md` an; leerer Body = Vorlage.
#[tauri::command]
pub fn project_ticket_create(
    project: String,
    title: String,
    station: String,
    body: String,
    needs_human: bool,
    parent: Option<String>,
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
    let specs = root.join(SPECS_DIR);
    // Laufende Nummer als Präfix (BO 2026-09-10, „in anderen Projekten gut
    // aufgenommen"): `012-slug` — eindeutig, sortierbar, zitierbar.
    let base = format!(
        "{:03}-{}",
        crate::project_cmd::next_spec_number(&root),
        slugify(title)
    );
    let mut id = base.clone();
    let mut counter = 2;
    while specs.join(&id).exists() {
        id = format!("{base}-{counter}");
        counter += 1;
    }

    let mut frontmatter = vec![format!("station: {station}")];
    if let Some(order) = order {
        frontmatter.push(format!("order: {order}"));
    }
    frontmatter.push(format!("created: {}", &now_iso()[..10]));
    if needs_human {
        frontmatter.push("needs_human: true".into());
    }
    if let Some(parent) = parent.as_deref().map(str::trim).filter(|p| !p.is_empty()) {
        frontmatter.push(format!("parent: {parent}"));
    }

    let mut body = if body.trim().is_empty() {
        template_body(title)
    } else if body.trim_start().starts_with("# ") {
        body
    } else {
        format!("# {title}\n\n{body}")
    };
    if !body.ends_with('\n') {
        body.push('\n');
    }
    let text = format!("---\n{}\n---\n{}", frontmatter.join("\n"), body);
    let file = specs.join(&id).join("SPEC.md");
    write_atomic(&file, &text)?;
    log_user_event(
        &root,
        &id,
        "spec_created",
        format!("Spec angelegt: {title}"),
    );

    Ok(file
        .strip_prefix(&root)
        .unwrap_or(&file)
        .to_string_lossy()
        .replace('\\', "/"))
}

/// Toggle a task from the same Markdown snapshot the inspector displayed.
#[tauri::command]
pub fn project_spec_toggle_task(
    project: String,
    file: String,
    index: usize,
    done: bool,
    expected_body: String,
) -> Result<(), String> {
    static TASK_WRITES: std::sync::Mutex<()> = std::sync::Mutex::new(());
    let _guard = TASK_WRITES.lock().map_err(|e| e.to_string())?;
    let root = resolve_project_root(&project)?;
    let path = writable_spec_path(&root, &file)?;
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    let body = crate::project_cmd::parse_flat_frontmatter(&text)
        .map(|(_, body)| body)
        .unwrap_or(&text);
    const CONFLICT: &str =
        "SPEC_CHANGED: Spec wurde zwischenzeitlich geändert. Bitte neu laden und erneut wählen.";
    if body != expected_body {
        return Err(CONFLICT.into());
    }
    let tasks = crate::spec_tasks::parse_tasks(body);
    let task = tasks
        .get(index)
        .ok_or_else(|| format!("Task {} gibt es nicht.", index + 1))?;
    if task.done == done {
        return Ok(());
    }
    let offset = text.len() - body.len() + task.marker_offset;
    let mut out = text.clone();
    out.replace_range(offset..offset + 1, if done { "x" } else { " " });
    if std::fs::read_to_string(&path).map_err(|e| e.to_string())? != text {
        return Err(CONFLICT.into());
    }
    write_atomic(&path, &out)?;
    let id = crate::project_cmd::spec_id_of(&root, &path);
    log_user_event(
        &root,
        &id,
        "spec_edited",
        format!(
            "Task {} {}",
            index + 1,
            if done { "erledigt" } else { "wieder offen" }
        ),
    );
    Ok(())
}

/// Specs ohne Nummer nachnummerieren — in Reihenfolge `created`, dann Name.
/// Benennt den Ordner um (`slug` → `NNN-slug`) und zieht `parent:`-Verweise
/// in allen Specs nach. Archivierte bleiben, wie sie sind. Rückgabe: die
/// neuen Ids.
#[tauri::command]
pub fn project_specs_number(project: String) -> Result<Vec<String>, String> {
    let root = resolve_project_root(&project)?;
    let mut candidates: Vec<(String, String, PathBuf)> = Vec::new(); // (created, id, dir)
    for dir in crate::project_cmd::spec_dirs(&root, false) {
        let path = dir.join("SPEC.md");
        let id = crate::project_cmd::spec_id_of(&root, &path);
        if crate::project_cmd::spec_number_of(&id).is_some() {
            continue;
        }
        let created = std::fs::read_to_string(&path)
            .ok()
            .and_then(|text| {
                crate::project_cmd::parse_flat_frontmatter(&text).and_then(|(fields, _)| {
                    crate::project_cmd::flat_lookup(&fields, "created").map(str::to_string)
                })
            })
            .unwrap_or_default();
        candidates.push((created, id, dir));
    }
    candidates.sort();
    let mut number = crate::project_cmd::next_spec_number(&root);
    let mut renamed: Vec<(String, String)> = Vec::new();
    for (_, id, dir) in candidates {
        let new_id = format!("{number:03}-{id}");
        let target = root.join(SPECS_DIR).join(&new_id);
        std::fs::rename(&dir, &target).map_err(|e| format!("{}: {e}", dir.display()))?;
        log_user_event(
            &root,
            &new_id,
            "spec_edited",
            format!("Nummeriert: {id} → {new_id}"),
        );
        renamed.push((id, new_id));
        number += 1;
    }
    if renamed.is_empty() {
        return Ok(Vec::new());
    }
    // Historical snapshots remain unchanged, including their parent references.
    for dir in crate::project_cmd::spec_dirs(&root, false) {
        let path = dir.join("SPEC.md");
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        let Some((fields, _)) = crate::project_cmd::parse_flat_frontmatter(&text) else {
            continue;
        };
        let Some(parent) = crate::project_cmd::flat_lookup(&fields, "parent") else {
            continue;
        };
        if let Some((_, new_id)) = renamed.iter().find(|(old, _)| old == parent) {
            let updated = update_ticket_text(&text, &[("parent", Some(new_id.clone()))], None)?;
            write_atomic(&path, &updated)?;
        }
    }
    Ok(renamed.into_iter().map(|(_, new_id)| new_id).collect())
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

/// Titel = erste `# `-Überschrift im Body: ersetzen oder voranstellen.
fn body_with_title(body: &str, title: &str) -> String {
    let mut lines: Vec<&str> = body.lines().collect();
    if let Some(position) = lines.iter().position(|line| line.starts_with("# ")) {
        let heading = format!("# {title}");
        let mut out: Vec<String> = lines.iter().map(|line| line.to_string()).collect();
        out[position] = heading;
        return out.join("\n");
    }
    lines.insert(0, "");
    format!("# {title}\n{}", lines.join("\n"))
}

/// Speichert das Editor-Sheet in einem Rutsch; loggt `station_changed`
/// und/oder `spec_edited`, je nachdem, was sich wirklich geändert hat.
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
    let path = writable_spec_path(&root, &file)?;
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;

    let old_station = text
        .lines()
        .find_map(|line| line.strip_prefix("station:"))
        .map(str::trim)
        .unwrap_or("")
        .to_string();
    let spec_id = crate::project_cmd::spec_id_of(&root, &path);

    let updates: Vec<(&str, Option<String>)> = vec![
        ("title", None), // v1-Feld: der Titel steht in der Überschrift
        ("station", Some(patch.station.clone())),
        ("ready", patch.ready.then(|| "true".into())),
        ("needs_human", patch.needs_human.then(|| "true".into())),
        ("order", patch.order.map(|order| order.to_string())),
    ];
    let body = body_with_title(&patch.body, patch.title.trim());
    let updated = update_ticket_text(&text, &updates, Some(&body))?;
    if updated == text {
        return Ok(());
    }
    write_atomic(&path, &updated)?;

    if old_station != patch.station {
        log_user_event(
            &root,
            &spec_id,
            "station_changed",
            format!("{old_station} -> {}", patch.station),
        );
    }
    log_user_event(
        &root,
        &spec_id,
        "spec_edited",
        "Im Editor gespeichert".into(),
    );
    Ok(())
}

/// Löscht den ganzen Spec-Ordner (SPEC.md, History, Beilagen).
#[tauri::command]
pub fn project_ticket_delete(project: String, file: String) -> Result<(), String> {
    let root = resolve_project_root(&project)?;
    let path = writable_spec_path(&root, &file)?;
    let dir = path.parent().ok_or_else(|| format!("Keine Spec: {file}"))?;
    std::fs::remove_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))
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
    /// Spec 030: Adressat (`· an: <email>` in der Kopfzeile).
    pub to: Option<String>,
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

/// Spec 030: `· an: <email>` in der Kopfzeile adressiert eine Person.
pub(crate) fn parse_addressee(head: &str) -> Option<String> {
    let lower = head.to_ascii_lowercase();
    let start = lower.find("an:")?;
    let rest = &head[start + 3..];
    let value = rest.split(['·', '|']).next()?.trim();
    (!value.is_empty()).then(|| value.trim_matches(['<', '>']).to_ascii_lowercase())
}

/// Fragen samt Antworten aus einem Ticket-Body, älteste zuerst.
pub(crate) fn parse_questions(body: &str) -> Vec<TicketQuestion> {
    let mut questions: Vec<TicketQuestion> = Vec::new();
    let mut answers: Vec<(u32, String, Option<String>)> = Vec::new();
    let mut in_section = false;
    let mut current: Option<(bool, u32, Option<String>, Option<String>, Vec<String>)> = None;

    let mut finish = |entry: Option<(bool, u32, Option<String>, Option<String>, Vec<String>)>| {
        if let Some((is_question, number, timestamp, to, lines)) = entry {
            let text = lines.join("\n").trim().to_string();
            if is_question {
                questions.push(TicketQuestion {
                    number,
                    open: true,
                    asked_at: timestamp,
                    to,
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
                current = Some((
                    is_question,
                    number,
                    timestamp,
                    parse_addressee(head),
                    Vec::new(),
                ));
            }
            continue;
        }
        if let Some(entry) = current.as_mut() {
            entry.4.push(line.to_string());
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
    let path = writable_spec_path(&root, &file)?;
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

    let spec_id = crate::project_cmd::spec_id_of(&root, &path);
    log_user_event(
        &root,
        &spec_id,
        "spec_edited",
        format!("Frage Q{number} beantwortet"),
    );
    Ok(())
}

/// Eine offene Rückfrage fürs Notification-System (W4).
#[derive(Serialize, Clone)]
pub struct OpenQuestion {
    pub spec_id: String,
    pub title: String,
    /// Spec 030: adressierte Person (E-Mail), falls angegeben.
    pub to: Option<String>,
    /// Dedupe-Schlüssel `<spec>|Q<n>` — nie zweimal melden.
    pub key: String,
    pub text: String,
}

/// Älteste offene Frage je Spec (Vertrag: der Agent setzt `open_question`).
pub(crate) fn scan_open_questions(root: &Path) -> Vec<OpenQuestion> {
    let mut open = Vec::new();
    for dir in crate::project_cmd::spec_dirs(root, false) {
        let path = dir.join("SPEC.md");
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
        let spec_id = crate::project_cmd::spec_id_of(root, &path);
        let title = heading_title(body).unwrap_or_else(|| spec_id.clone());
        let question = parse_questions(body)
            .into_iter()
            .find(|question| question.number == number && question.open);
        open.push(OpenQuestion {
            key: format!("{spec_id}|Q{number}"),
            spec_id,
            title,
            to: question.as_ref().and_then(|q| q.to.clone()),
            text: question.map(|question| question.text).unwrap_or_default(),
        });
    }
    open
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bundled_template_accepts_lf_and_crlf_checkouts() {
        let lf = SPEC_TEMPLATE.replace("\r\n", "\n");
        let crlf = lf.replace('\n', "\r\n");
        let expected = template_body_from(&lf, "Windows title");
        assert!(expected.starts_with("# Windows title\n"));
        assert!(!expected.contains("station:"));
        assert_eq!(template_body_from(&crlf, "Windows title"), expected);
    }

    #[test]
    fn historical_specs_are_read_only_and_history_is_path_addressed() {
        let dir = fixture("historical-identity");
        let project = dir.display().to_string();
        let id = "001-same";
        let active = format!(".agent/specs/{id}/SPEC.md");
        let old = format!(".agent/specs/archive/2026-09-01-{id}/SPEC.md");
        let body = "# Same\n\n- [ ] task\n\n## Questions\n\n### Q1 · open · 2026-09-01T10:00:00Z\nQuestion?\n";
        let source = format!(
            "---\nstation: Done\nparent: topic\nopen_question: Q1\ncustom: keep\n---\n{body}"
        );
        for (file, summary) in [(&active, "active history"), (&old, "old history")] {
            let path = dir.join(file);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(&path, &source).unwrap();
            let event = serde_json::json!({"timestamp":"2026-09-01T10:00:00Z", "spec_id":id, "event_type":"spec_created", "actor":"project", "summary":summary});
            std::fs::write(path.with_file_name("history.jsonl"), format!("{event}\n")).unwrap();
        }
        let old_history = std::fs::read(dir.join(&old).with_file_name("history.jsonl")).unwrap();
        let board =
            serde_json::to_value(crate::project_cmd::read_project_board(project.clone()).unwrap())
                .unwrap();
        assert_eq!(board.as_array().unwrap().len(), 2);
        for (file, summary) in [(&active, "active history"), (&old, "old history")] {
            let events =
                project_ticket_history(project.clone(), id.into(), Some(file.clone())).unwrap();
            assert_eq!(events[0].summary, summary);
        }
        assert!(
            project_ticket_history(project.clone(), "002-wrong".into(), Some(old.clone())).is_err()
        );
        assert!(
            project_ticket_history(project.clone(), id.into(), Some("../SPEC.md".into())).is_err()
        );
        assert_eq!(
            project_ticket_questions(project.clone(), old.clone())
                .unwrap()
                .len(),
            1
        );
        assert!(
            project_spec_toggle_task(project.clone(), old.clone(), 0, true, body.into()).is_err()
        );
        assert!(project_ticket_answer(project.clone(), old.clone(), 1, "Answer".into()).is_err());
        assert!(crate::project_cmd::project_board_move(
            project.clone(),
            old.clone(),
            "Doing".into()
        )
        .is_err());
        assert!(project_ticket_save(
            project.clone(),
            old.clone(),
            TicketPatch {
                title: "Changed".into(),
                station: "Doing".into(),
                ready: false,
                needs_human: false,
                order: None,
                body: "Changed".into(),
            }
        )
        .is_err());
        assert!(project_ticket_delete(project.clone(), old.clone()).is_err());
        let topic = dir.join(".agent/specs/topic");
        std::fs::create_dir_all(&topic).unwrap();
        std::fs::write(
            topic.join("SPEC.md"),
            "---\nstation: Backlog\n---\n# Topic\n",
        )
        .unwrap();
        project_specs_number(project.clone()).unwrap();
        assert_eq!(std::fs::read_to_string(dir.join(&old)).unwrap(), source);
        assert_eq!(
            std::fs::read(dir.join(&old).with_file_name("history.jsonl")).unwrap(),
            old_history
        );
        // Done is a state change, never a move to an archive directory.
        crate::project_cmd::project_board_move(project.clone(), active.clone(), "Doing".into())
            .unwrap();
        crate::project_cmd::project_board_move(project, active.clone(), "Done".into()).unwrap();
        assert!(dir.join(active).is_file());
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn task_list_count_and_toggle_share_markdown_offsets() {
        let dir = fixture("markdown-tasks");
        let folder = dir.join(".agent/specs/001-tasks");
        std::fs::create_dir_all(&folder).unwrap();
        let file = ".agent/specs/001-tasks/SPEC.md".to_string();
        let body = "# Übung\r\n\r\n```markdown\r\n- [ ] kein Task\r\n```\r\n\r\n    - [ ] Code\r\n\r\n## Acceptance\r\n- [ ] öffnen\r\n* [X] erledigt\r\n";
        let text = format!("---\r\nstation: Doing\r\ncustom: keep\r\n---\r\n{body}");
        std::fs::write(folder.join("SPEC.md"), &text).unwrap();
        let project = dir.display().to_string();
        let entries =
            serde_json::to_value(crate::project_cmd::read_project_board(project.clone()).unwrap())
                .unwrap();
        assert_eq!(entries[0]["tasks_total"], 2);
        assert_eq!(entries[0]["tasks_done"], 1);
        assert_eq!(entries[0]["tasks"][0]["text"], "öffnen");
        project_spec_toggle_task(project, file, 1, false, body.into()).unwrap();
        assert_eq!(
            std::fs::read_to_string(folder.join("SPEC.md")).unwrap(),
            text.replace("* [X] erledigt", "* [ ] erledigt")
        );
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn stale_task_click_preserves_external_changes_and_current_frontmatter() {
        let dir = fixture("stale-tasks");
        let folder = dir.join(".agent/specs/001-tasks");
        std::fs::create_dir_all(&folder).unwrap();
        let file = ".agent/specs/001-tasks/SPEC.md".to_string();
        let project = dir.display().to_string();
        let body = "# Tasks\n- [ ] original\n";
        let changed =
            "---\nstation: Doing\nforeign: keep\n---\n# Tasks\n- [ ] inserted\n- [ ] original\n";
        std::fs::write(folder.join("SPEC.md"), changed).unwrap();
        let error = project_spec_toggle_task(project.clone(), file.clone(), 0, true, body.into())
            .unwrap_err();
        assert!(error.starts_with("SPEC_CHANGED:"));
        assert_eq!(
            std::fs::read_to_string(folder.join("SPEC.md")).unwrap(),
            changed
        );
        assert!(!folder.join("history.jsonl").exists());
        let current = format!("---\nstation: Doing\nforeign: new-value\n---\n{body}");
        std::fs::write(folder.join("SPEC.md"), &current).unwrap();
        project_spec_toggle_task(project.clone(), file.clone(), 0, true, body.into()).unwrap();
        let updated = std::fs::read_to_string(folder.join("SPEC.md")).unwrap();
        assert_eq!(updated, current.replace("- [ ] original", "- [x] original"));
        assert!(project_spec_toggle_task(project, file, 0, true, body.into()).is_err());
        assert_eq!(
            std::fs::read_to_string(folder.join("SPEC.md")).unwrap(),
            updated
        );
        std::fs::remove_dir_all(dir).unwrap();
    }

    fn fixture(test: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-board-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join(".agent/specs")).unwrap();
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
        let spec =
            format!("---\nstation: Doing\nopen_question: Q1\ncustom: bleibt\n---\n# QA\n\n{body}");
        std::fs::create_dir_all(dir.join(".agent/specs/qa-1")).unwrap();
        std::fs::write(dir.join(".agent/specs/qa-1/SPEC.md"), &spec).unwrap();
        let file = ".agent/specs/qa-1/SPEC.md".to_string();
        let open = scan_open_questions(&dir);
        assert_eq!(open.len(), 1);
        assert_eq!(open[0].key, "qa-1|Q1");
        assert_eq!(open[0].title, "QA");

        // Q1 ist schon beantwortet — der Command verweigert die zweite Antwort.
        let twice =
            project_ticket_answer(project.clone(), file.clone(), 1, "Nochmal".into()).unwrap_err();
        assert!(twice.contains("schon beantwortet"));

        project_ticket_answer(project.clone(), file.clone(), 2, "Zweite Antwort.".into()).unwrap();
        let saved = std::fs::read_to_string(dir.join(".agent/specs/qa-1/SPEC.md")).unwrap();
        assert!(saved.contains("### A2 · bo · "));
        assert!(saved.contains("custom: bleibt"));
        assert!(!saved.contains("open_question")); // keine offene mehr
        assert!(saved.contains("## Notizen\nDanach.")); // Folgeabschnitt intakt
        let after = project_ticket_questions(project, file).unwrap();
        assert!(after.iter().all(|question| !question.open));
        assert!(dir.join(".agent/specs/qa-1/history.jsonl").is_file());

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
            String::new(),
            true,
            Some("projektfenster".into()),
            Some(1),
        )
        .unwrap();
        assert_eq!(file, ".agent/specs/001-board-tab-bauen/SPEC.md");
        let text = std::fs::read_to_string(dir.join(&file)).unwrap();
        assert!(text.starts_with("---\nstation: Backlog\norder: 1\ncreated: "));
        assert!(text.contains("needs_human: true"));
        assert!(text.contains("parent: projektfenster"));
        assert!(text.contains("# Board-Tab bauen!\n"));
        assert!(text.contains("## Tasks\n\n- [ ] …"));
        let id = "001-board-tab-bauen".to_string();
        // Gleicher Titel noch einmal → nächste Nummer, nie Überschreiben.
        let second = project_ticket_create(
            project.clone(),
            "Board-Tab bauen!".into(),
            "Backlog".into(),
            String::new(),
            false,
            None,
            None,
        )
        .unwrap();
        assert_eq!(second, ".agent/specs/002-board-tab-bauen/SPEC.md");
        project_ticket_delete(project.clone(), second).unwrap();
        // Nachnummerieren: unnummerierte Specs bekommen die nächste Nummer,
        // parent-Verweise ziehen mit.
        std::fs::create_dir_all(dir.join(".agent/specs/thema")).unwrap();
        std::fs::write(
            dir.join(".agent/specs/thema/SPEC.md"),
            "---\nstation: Backlog\ncreated: 2026-09-01\n---\n# Thema\n",
        )
        .unwrap();
        std::fs::create_dir_all(dir.join(".agent/specs/kind")).unwrap();
        std::fs::write(
            dir.join(".agent/specs/kind/SPEC.md"),
            "---\nstation: Backlog\ncreated: 2026-09-02\nparent: thema\n---\n# Kind\n",
        )
        .unwrap();
        let numbered = project_specs_number(project.clone()).unwrap();
        // 002 wurde gelöscht → die Nummer ist wieder frei (Archiv zählt mit).
        assert_eq!(
            numbered,
            vec!["002-thema".to_string(), "003-kind".to_string()]
        );
        let kind = std::fs::read_to_string(dir.join(".agent/specs/003-kind/SPEC.md")).unwrap();
        assert!(kind.contains("parent: 002-thema"));
        assert!(project_specs_number(project.clone()).unwrap().is_empty());
        assert_eq!(crate::project_cmd::spec_number_of("002-thema"), Some(2));
        assert_eq!(crate::project_cmd::spec_number_of("thema"), None);
        assert_eq!(crate::project_cmd::next_spec_number(&dir), 4);
        for extra in ["002-thema", "003-kind"] {
            project_ticket_delete(project.clone(), format!(".agent/specs/{extra}/SPEC.md"))
                .unwrap();
        }

        project_ticket_save(
            project.clone(),
            file.clone(),
            TicketPatch {
                title: "Board-Tab bauen".into(),
                station: "Doing".into(),
                ready: true,
                needs_human: true,
                order: Some(1),
                body: "# Alt\n\nErste Fassung.\n\n## Tasks\n\n- [ ] eins\n- [x] zwei\n- [ ] drei\n\nMehr.".into(),
            },
        )
        .unwrap();
        let saved = std::fs::read_to_string(dir.join(&file)).unwrap();
        assert!(saved.contains("station: Doing"));
        assert!(saved.contains("ready: true"));
        assert!(saved.contains("# Board-Tab bauen\n")); // Titel in der Überschrift
        assert!(!saved.contains("title:"));
        assert!(saved.ends_with("Mehr.\n"));

        // Tasks umschalten: nur die getroffene Zeile ändert sich.
        let body = crate::project_cmd::parse_flat_frontmatter(&saved)
            .unwrap()
            .1
            .to_string();
        project_spec_toggle_task(project.clone(), file.clone(), 2, true, body).unwrap();
        let toggled = std::fs::read_to_string(dir.join(&file)).unwrap();
        assert!(toggled.contains("- [ ] eins\n- [x] zwei\n- [x] drei\n"));
        let body = crate::project_cmd::parse_flat_frontmatter(&toggled)
            .unwrap()
            .1
            .to_string();
        project_spec_toggle_task(project.clone(), file.clone(), 1, false, body).unwrap();
        let toggled = std::fs::read_to_string(dir.join(&file)).unwrap();
        assert!(toggled.contains("- [ ] eins\n- [ ] zwei\n- [x] drei\n"));
        let body = crate::project_cmd::parse_flat_frontmatter(&toggled)
            .unwrap()
            .1
            .to_string();
        assert!(project_spec_toggle_task(project.clone(), file.clone(), 7, true, body).is_err());

        // Agent-Lauf dazu (schreibt der Agent selbst — hier simuliert); eine
        // Zeile im alten ticket_id-Format wird weiter gelesen.
        let run = r#"{"timestamp":"2026-08-31T13:00:00Z","spec_id":"ID","event_type":"agent_run","actor":"agent:claude","summary":"lief","tokens_in":100,"tokens_out":40,"tokens_cache_read":900,"duration_ms":5000}"#
            .replace("ID", &id);
        let legacy = r#"{"timestamp":"2026-08-30T13:00:00Z","ticket_id":"ID","event_type":"agent_run","actor":"agent:claude","summary":"alt","tokens_in":10,"tokens_out":4,"duration_ms":500}"#
            .replace("ID", &id);
        use std::io::Write;
        let mut handle = std::fs::OpenOptions::new()
            .append(true)
            .open(dir.join(".agent/specs").join(&id).join("history.jsonl"))
            .unwrap();
        writeln!(handle, "{run}").unwrap();
        writeln!(handle, "{legacy}").unwrap();
        writeln!(handle, "kaputte zeile die übersprungen wird").unwrap();
        drop(handle);

        let history = project_ticket_history(project.clone(), id.clone(), None).unwrap();
        // created, station_changed, edited, 2× task, agent_run, legacy agent_run
        assert_eq!(history.len(), 7);
        assert_eq!(history[0].event_type, "agent_run"); // neueste zuerst
        assert!(history.iter().all(|event| event.spec_id == id));

        let kpis = tauri::async_runtime::block_on(project_board_kpis(project.clone())).unwrap();
        assert_eq!(kpis.run_count, 2);
        assert_eq!(kpis.tokens_in, 1010); // 100 + 900 cache_read + 10 — effektiv
        assert_eq!(kpis.tokens_out, 44);
        assert_eq!(kpis.recent.len(), 2);

        // Fixture from the retired workflow: reads/KPIs still include old data.
        let legacy_dir = dir
            .join(".agent/specs/archive")
            .join(format!("2026-09-01-{id}"));
        std::fs::create_dir_all(legacy_dir.parent().unwrap()).unwrap();
        std::fs::rename(dir.join(&file).parent().unwrap(), &legacy_dir).unwrap();
        let archived = format!(".agent/specs/archive/2026-09-01-{id}/SPEC.md");
        assert!(archived.starts_with(".agent/specs/archive/"));
        assert!(archived.ends_with(&format!("-{id}/SPEC.md")));
        assert!(!dir.join(".agent/specs").join(&id).exists());
        assert!(dir.join(&archived).is_file());
        assert!(dir
            .join(&archived)
            .with_file_name("history.jsonl")
            .is_file());
        assert_eq!(
            tauri::async_runtime::block_on(project_board_kpis(project.clone()))
                .unwrap()
                .run_count,
            2
        );
        assert!(project_ticket_delete(project.clone(), archived.clone()).is_err());
        assert!(dir.join(&archived).exists());
        let evil = project_ticket_delete(project, ".agent/agent.md".into()).unwrap_err();
        assert!(evil.contains("Keine Spec"));

        let _ = std::fs::remove_dir_all(&dir);
    }
}
