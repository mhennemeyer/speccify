//! A single Markdown task definition for board counts, inspector and writes.
use pulldown_cmark::{Event, Options, Parser};
use serde::Serialize;

#[derive(Debug, Serialize)]
pub(crate) struct SpecTask {
    pub index: usize,
    pub done: bool,
    pub text: String,
    #[serde(skip)]
    pub marker_offset: usize,
}

pub(crate) fn parse_tasks(body: &str) -> Vec<SpecTask> {
    let mut tasks = Vec::new();
    for (event, range) in Parser::new_ext(body, Options::ENABLE_TASKLISTS).into_offset_iter() {
        if let Event::TaskListMarker(done) = event {
            // The parser range points at the source checkbox, not rendered text.
            let marker = &body[range.clone()];
            if !matches!(marker, "[ ]" | "[x]" | "[X]") {
                continue;
            }
            let text = body[range.end..]
                .lines()
                .next()
                .unwrap_or("")
                .trim()
                .to_string();
            tasks.push(SpecTask {
                index: tasks.len(),
                done,
                text,
                marker_offset: range.start + 1,
            });
        }
    }
    tasks
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn markdown_examples_are_not_tasks() {
        let body = "# Übung\r\n- [ ] offen\r\n```md\r\n- [x] Beispiel\r\n```\r\n~~~\r\n* [ ] Beispiel\r\n~~~\r\n\n    - [ ] eingerückter Code\n\n## Acceptance\n* [X] fertig\n+ [ ] plus\n1. [x] nummeriert\n   - [ ] verschachtelt\n";
        let tasks = parse_tasks(body);
        assert_eq!(tasks.len(), 5, "{tasks:?}");
        assert_eq!(tasks.iter().filter(|t| t.done).count(), 2);
        assert_eq!(tasks[0].text, "offen");
        assert_eq!(tasks[4].text, "verschachtelt");
        for task in tasks {
            let marker = body.as_bytes()[task.marker_offset];
            assert!(if task.done {
                matches!(marker, b'x' | b'X')
            } else {
                marker == b' '
            });
        }
    }

    #[test]
    fn long_unclosed_and_nested_fences_are_ignored() {
        for body in [
            "````md\n```\n- [ ] example\n````\n- [ ] real",
            "~~~\n- [ ] example",
            "- item\n  ```\n  - [ ] example\n  ```\n- [ ] real",
        ] {
            assert!(parse_tasks(body).iter().all(|t| t.text == "real"));
        }
    }
}
