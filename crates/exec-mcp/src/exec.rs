//! Reine Befehlsausführung (Vertrag: `docs/exec-mcp-contract.md`):
//! shlex/argv ohne Shell, cwd = Projekt-Root, Timeout. `run_command_result`
//! kappt stdout/stderr (20 000 Zeichen, Agent-Kontext-Schutz); `stream_command`
//! merged stderr in stdout (fd-Level, Konsolen-Reihenfolge) und ist
//! **ungekappt** — plus Timeout-Kill und Disconnect-Kill (Stop-Semantik).

use std::io::{BufRead, BufReader, Read};
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::time::{Duration, Instant};

use serde_json::{Value, json};
use wait_timeout::ChildExt;

pub const MAX_OUTPUT_CHARS: usize = 20_000;

/// Zeichen-basierte Kappung (wie Python `_cap_flag`).
fn cap(text: String, max: usize) -> (String, bool) {
    if text.chars().count() <= max {
        return (text, false);
    }
    let truncated: String = text.chars().take(max).collect();
    (format!("{truncated}\n… [gekappt nach {max} Zeichen]"), true)
}

/// Führt `command` aus und liefert das agentenlesbare Ergebnis-Objekt
/// (`exit_code/stdout/stderr/truncated/duration_ms` bzw. `error/exit_code`).
pub fn run_command_result(command: &str, cwd: &Path, timeout: f64, max_output: usize) -> Value {
    let argv = match shlex::split(command) {
        Some(argv) if !argv.is_empty() => argv,
        Some(_) => return json!({"error": "Leerer Befehl.", "exit_code": Value::Null}),
        None => {
            return json!({
                "error": format!("Befehl nicht parsebar: {command}"),
                "exit_code": Value::Null,
            });
        }
    };

    let started = Instant::now();
    let mut child = match Command::new(&argv[0])
        .args(&argv[1..])
        .current_dir(cwd)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
    {
        Ok(child) => child,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return json!({
                "error": format!("Programm nicht gefunden: {}", argv[0]),
                "exit_code": Value::Null,
            });
        }
        Err(error) => {
            return json!({
                "error": format!("{}: {error}", argv[0]),
                "exit_code": Value::Null,
            });
        }
    };

    let mut stdout_pipe = child.stdout.take();
    let mut stderr_pipe = child.stderr.take();
    let out_handle = std::thread::spawn(move || read_to_string(stdout_pipe.as_mut()));
    let err_handle = std::thread::spawn(move || read_to_string(stderr_pipe.as_mut()));

    let status = child.wait_timeout(Duration::from_secs_f64(timeout));
    let duration_ms = started.elapsed().as_millis() as u64;

    match status {
        Ok(Some(status)) => {
            let (stdout, stdout_truncated) = cap(out_handle.join().unwrap_or_default(), max_output);
            let (stderr, stderr_truncated) = cap(err_handle.join().unwrap_or_default(), max_output);
            json!({
                "exit_code": status.code().unwrap_or(-1),
                "stdout": stdout,
                "stderr": stderr,
                "truncated": stdout_truncated || stderr_truncated,
                "duration_ms": duration_ms,
            })
        }
        _ => {
            let _ = child.kill();
            let _ = child.wait();
            let (stdout, _) = cap(out_handle.join().unwrap_or_default(), max_output);
            let (stderr, _) = cap(err_handle.join().unwrap_or_default(), max_output);
            json!({
                "error": format!("Timeout nach {timeout:.0}s."),
                "exit_code": Value::Null,
                "stdout": stdout,
                "stderr": stderr,
            })
        }
    }
}

fn read_to_string<R: Read>(reader: Option<&mut R>) -> String {
    let mut buffer = String::new();
    if let Some(reader) = reader {
        let _ = reader.read_to_string(&mut buffer);
    }
    buffer
}

/// Live-Streaming: ruft `emit` je Ausgabezeile (`{"type":"line",…}`) und
/// zum Abschluss (`{"type":"exit",…}`). stderr ist in stdout gemergt
/// (fd-Level). `emit` gibt `Err` zurück, wenn der Client die Verbindung
/// abbricht — dann wird der Kindprozess sofort gekillt (Stop-Semantik).
pub fn stream_command(
    command: &str,
    cwd: &Path,
    timeout: f64,
    emit: &mut dyn FnMut(&Value) -> std::io::Result<()>,
) {
    let argv = match shlex::split(command) {
        Some(argv) if !argv.is_empty() => argv,
        Some(_) => {
            let _ =
                emit(&json!({"type": "exit", "error": "Leerer Befehl.", "exit_code": Value::Null}));
            return;
        }
        None => {
            let _ = emit(&json!({
                "type": "exit",
                "error": format!("Befehl nicht parsebar: {command}"),
                "exit_code": Value::Null,
            }));
            return;
        }
    };

    // fd-Level-Merge: ein Pipe-Writer für stdout UND stderr → echte
    // Konsolen-Reihenfolge (wie Popen(stderr=STDOUT)).
    let (reader, writer) = match os_pipe::pipe() {
        Ok(pair) => pair,
        Err(error) => {
            let _ = emit(
                &json!({"type": "exit", "error": format!("Pipe: {error}"), "exit_code": Value::Null}),
            );
            return;
        }
    };
    let writer_clone = match writer.try_clone() {
        Ok(clone) => clone,
        Err(error) => {
            let _ = emit(
                &json!({"type": "exit", "error": format!("Pipe: {error}"), "exit_code": Value::Null}),
            );
            return;
        }
    };

    let started = Instant::now();
    let mut child = match Command::new(&argv[0])
        .args(&argv[1..])
        .current_dir(cwd)
        .stdin(Stdio::null())
        .stdout(Stdio::from(writer))
        .stderr(Stdio::from(writer_clone))
        .spawn()
    {
        Ok(child) => child,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            let _ = emit(&json!({
                "type": "exit",
                "error": format!("Programm nicht gefunden: {}", argv[0]),
                "exit_code": Value::Null,
            }));
            return;
        }
        Err(error) => {
            let _ = emit(
                &json!({"type": "exit", "error": format!("{}: {error}", argv[0]), "exit_code": Value::Null}),
            );
            return;
        }
    };

    // Reader-Thread → Queue: blockierendes readline mit dem Timeout
    // kombinierbar machen.
    let (tx, rx) = mpsc::channel::<Option<String>>();
    std::thread::spawn(move || {
        let buffered = BufReader::new(reader);
        for line in buffered.lines() {
            match line {
                Ok(line) => {
                    if tx.send(Some(line)).is_err() {
                        return;
                    }
                }
                Err(_) => break,
            }
        }
        let _ = tx.send(None);
    });

    let deadline = started + Duration::from_secs_f64(timeout);
    loop {
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            let _ = child.kill();
            let _ = child.wait();
            let _ = emit(&json!({
                "type": "exit",
                "error": format!("Timeout nach {timeout:.0}s."),
                "exit_code": Value::Null,
                "duration_ms": started.elapsed().as_millis() as u64,
                "truncated": false,
            }));
            return;
        }
        match rx.recv_timeout(remaining.min(Duration::from_millis(500))) {
            Ok(Some(line)) => {
                if emit(&json!({"type": "line", "text": line.trim_end_matches('\n')})).is_err() {
                    // Client weg → Kindprozess sofort killen und reapen.
                    let _ = child.kill();
                    let _ = child.wait();
                    return;
                }
            }
            Ok(None) => break,
            Err(mpsc::RecvTimeoutError::Timeout) => continue,
            Err(mpsc::RecvTimeoutError::Disconnected) => break,
        }
    }

    let exit_code = child
        .wait()
        .ok()
        .and_then(|status| status.code())
        .unwrap_or(-1);
    let _ = emit(&json!({
        "type": "exit",
        "exit_code": exit_code,
        "duration_ms": started.elapsed().as_millis() as u64,
        "truncated": false,
    }));
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cwd() -> std::path::PathBuf {
        std::env::temp_dir()
    }

    #[test]
    fn run_command_caps_at_limit() {
        let result = run_command_result(
            "python3 -c \"print('x' * 25000)\"",
            &cwd(),
            30.0,
            MAX_OUTPUT_CHARS,
        );
        let stdout = result["stdout"].as_str().unwrap();
        assert!(result["truncated"].as_bool().unwrap());
        assert!(stdout.contains("[gekappt nach 20000 Zeichen]"));
        assert!(stdout.chars().count() < 21_000);
    }

    #[test]
    fn stream_is_not_capped_and_merges_stderr() {
        let mut events = Vec::new();
        stream_command(
            "python3 -c \"import sys; print('x'*25000); sys.stdout.flush(); print('e', file=sys.stderr)\"",
            &cwd(),
            30.0,
            &mut |event| {
                events.push(event.clone());
                Ok(())
            },
        );
        let lines: Vec<&str> = events
            .iter()
            .filter(|event| event["type"] == "line")
            .map(|event| event["text"].as_str().unwrap())
            .collect();
        // Ungekappt: die 25000-Zeichen-Zeile kommt vollständig.
        assert!(lines.iter().any(|line| line.chars().count() == 25_000));
        assert!(lines.contains(&"e")); // stderr gemergt
        assert_eq!(events.last().unwrap()["type"], "exit");
    }

    #[test]
    fn stream_timeout_kills_and_reports() {
        let started = Instant::now();
        let mut exit = None;
        stream_command("sleep 30", &cwd(), 1.0, &mut |event| {
            if event["type"] == "exit" {
                exit = Some(event.clone());
            }
            Ok(())
        });
        assert!(started.elapsed() < Duration::from_secs(5));
        let exit = exit.unwrap();
        assert!(exit["error"].as_str().unwrap().contains("Timeout"));
    }

    #[test]
    fn stream_disconnect_kills_promptly() {
        let started = Instant::now();
        let mut first = true;
        // Endloser Output; emit bricht nach der ersten Zeile ab (Client weg).
        stream_command(
            "python3 -c \"import time\\nwhile True: print('tick'); time.sleep(0.05)\"",
            &cwd(),
            30.0,
            &mut |event| {
                if event["type"] == "line" && first {
                    first = false;
                    return Err(std::io::Error::new(std::io::ErrorKind::BrokenPipe, "gone"));
                }
                Ok(())
            },
        );
        assert!(started.elapsed() < Duration::from_secs(5));
    }
}
