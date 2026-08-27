//! Terminal-Seitenleiste (Plan toolkit-discovery-terminal.md, T6/D5):
//! echtes PTY (portable-pty) mit der Login-Shell des Users, cwd = Working
//! Dir aus den Settings. Output geht als `term-out`-Events ans Frontend
//! (xterm.js), Input über `terminal_write`. Beim Öffnen wird der
//! Autostart-Command aus den Settings in die Shell getippt (T0.5).
//! macOS/Linux: Login-Shell aus `$SHELL`; Windows (D16, Plan
//! projektfenster.md): ConPTY via portable-pty, `pwsh` wenn auf dem PATH,
//! sonst `powershell.exe` — und kein `-l` (das ist ein Unix-Login-Flag).

use std::collections::HashMap;
use std::io::{Read, Write};
use std::sync::Mutex;

use portable_pty::{native_pty_system, ChildKiller, CommandBuilder, MasterPty, PtySize};
use serde::Serialize;
use tauri::{AppHandle, Emitter, State};

use crate::settings;

struct TerminalSession {
    writer: Box<dyn Write + Send>,
    master: Box<dyn MasterPty + Send>,
    killer: Box<dyn ChildKiller + Send + Sync>,
}

/// Laufende Terminals; Drop killt die Shells beim App-Quit.
pub struct Terminals(Mutex<HashMap<String, TerminalSession>>);

impl Default for Terminals {
    fn default() -> Self {
        Self(Mutex::new(HashMap::new()))
    }
}

impl Drop for Terminals {
    fn drop(&mut self) {
        if let Ok(mut sessions) = self.0.lock() {
            for session in sessions.values_mut() {
                let _ = session.killer.kill();
            }
        }
    }
}

#[derive(Clone, Serialize)]
struct TermOut {
    id: String,
    data: String,
}

#[derive(Clone, Serialize)]
struct TermExit {
    id: String,
}

#[cfg(not(windows))]
fn login_shell() -> String {
    std::env::var("SHELL").unwrap_or_else(|_| "/bin/zsh".into())
}

#[cfg(windows)]
fn login_shell() -> String {
    let on_path = |name: &str| {
        std::env::var_os("PATH")
            .map(|path| std::env::split_paths(&path).any(|dir| dir.join(name).is_file()))
            .unwrap_or(false)
    };
    if on_path("pwsh.exe") {
        "pwsh.exe".into()
    } else {
        "powershell.exe".into()
    }
}

/// Öffnet ein Terminal und tippt den Autostart-Command vor. Ohne `cwd`/
/// `autostart` gelten die App-Settings (Dashboard); das Projektfenster
/// übergibt beides selbst (Plan projektfenster.md, P1: cwd = Projektwurzel,
/// Agent-Kommando pro Projekt). → Startverzeichnis (für die UI-Anzeige).
#[tauri::command]
pub fn terminal_open(
    app: AppHandle,
    state: State<Terminals>,
    id: String,
    cols: u16,
    rows: u16,
    cwd: Option<String>,
    autostart: Option<String>,
) -> Result<String, String> {
    let app_settings = settings::get_settings()?;
    let cwd = match cwd {
        Some(dir) => settings::resolve_working_dir(&dir)?,
        None => {
            let raw_dir = app_settings
                .working_dir
                .ok_or("Kein Working Dir gesetzt — zuerst im Settings-Tab wählen.")?;
            settings::resolve_working_dir(&raw_dir)?
        }
    };
    // None = Settings-Default; Some("") = bewusst reine Shell.
    let autostart = autostart
        .unwrap_or(app_settings.terminal_autostart_command)
        .trim()
        .to_string();

    let pty = native_pty_system()
        .openpty(PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|e| format!("PTY: {e}"))?;

    let shell = login_shell();
    let mut command = CommandBuilder::new(&shell);
    #[cfg(not(windows))]
    command.arg("-l"); // Login-Shell: PATH/Profile des Users
    command.cwd(&cwd);
    command.env("TERM", "xterm-256color");

    let child = pty
        .slave
        .spawn_command(command)
        .map_err(|e| format!("{shell}: {e}"))?;
    let killer = child.clone_killer();

    let mut reader = pty
        .master
        .try_clone_reader()
        .map_err(|e| format!("PTY-Reader: {e}"))?;
    let mut writer = pty
        .master
        .take_writer()
        .map_err(|e| format!("PTY-Writer: {e}"))?;

    // Autostart-Command vortippen (die tty-Eingabe puffert, bis die Shell
    // liest). Leer = reines Terminal.
    if !autostart.is_empty() {
        let _ = writer.write_all(format!("{autostart}\r").as_bytes());
    }

    // Reader-Thread: PTY-Output als Events (lossy — Escape-Sequenzen sind
    // Bytes, xterm.js verdaut UTF-8-Strings).
    let app_for_reader = app.clone();
    let id_for_reader = id.clone();
    std::thread::spawn(move || {
        let mut buffer = [0u8; 8192];
        loop {
            match reader.read(&mut buffer) {
                Ok(0) | Err(_) => break,
                Ok(count) => {
                    let data = String::from_utf8_lossy(&buffer[..count]).into_owned();
                    let _ = app_for_reader.emit(
                        "term-out",
                        TermOut {
                            id: id_for_reader.clone(),
                            data,
                        },
                    );
                }
            }
        }
        let _ = app_for_reader.emit("term-exit", TermExit { id: id_for_reader });
    });

    state.0.lock().unwrap().insert(
        id,
        TerminalSession {
            writer,
            master: pty.master,
            killer,
        },
    );
    Ok(cwd.display().to_string())
}

#[tauri::command]
pub fn terminal_write(state: State<Terminals>, id: String, data: String) -> Result<(), String> {
    let mut sessions = state.0.lock().unwrap();
    let session = sessions
        .get_mut(&id)
        .ok_or_else(|| format!("Kein Terminal: {id}"))?;
    session
        .writer
        .write_all(data.as_bytes())
        .and_then(|_| session.writer.flush())
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_resize(
    state: State<Terminals>,
    id: String,
    cols: u16,
    rows: u16,
) -> Result<(), String> {
    let sessions = state.0.lock().unwrap();
    let session = sessions
        .get(&id)
        .ok_or_else(|| format!("Kein Terminal: {id}"))?;
    session
        .master
        .resize(PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn terminal_kill(state: State<Terminals>, id: String) -> Result<bool, String> {
    match state.0.lock().unwrap().remove(&id) {
        Some(mut session) => {
            let _ = session.killer.kill();
            Ok(true)
        }
        None => Ok(false),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Validiert das Kern-Muster von terminal_open ohne Tauri: Shell im PTY
    /// spawnen, Kommando VOR dem Shell-Prompt vortippen (tty puffert),
    /// Output lesen. Genau so tippt terminal_open den Autostart-Command.
    #[test]
    fn pty_spawn_pretype_and_read() {
        let pty = native_pty_system()
            .openpty(PtySize {
                rows: 24,
                cols: 80,
                pixel_width: 0,
                pixel_height: 0,
            })
            .unwrap();
        let mut command = CommandBuilder::new(login_shell());
        command.cwd(std::env::temp_dir());
        command.env("TERM", "xterm-256color");
        let mut child = pty.slave.spawn_command(command).unwrap();
        // Slave nach dem Spawn schließen wie in terminal_open (dort fällt er
        // beim Return aus dem Scope) — auf ConPTY kommt sonst kein Output an.
        drop(pty.slave);

        let mut writer = pty.master.take_writer().unwrap();
        writer.write_all(b"echo pty-smoke-ok; exit\r").unwrap();

        // Lesen im eigenen Thread: `read` blockiert, und wenn die Shell im
        // PTY gar nichts liefert (z. B. Session 0 ohne Interaktivität), würde
        // eine Deadline in der Leseschleife nie geprüft — der Test hinge.
        let mut reader = pty.master.try_clone_reader().unwrap();
        let (sender, receiver) = std::sync::mpsc::channel();
        std::thread::spawn(move || {
            let mut collected = String::new();
            let mut buffer = [0u8; 4096];
            loop {
                match reader.read(&mut buffer) {
                    Ok(0) | Err(_) => break,
                    Ok(count) => {
                        collected.push_str(&String::from_utf8_lossy(&buffer[..count]));
                        if collected.contains("pty-smoke-ok") {
                            break;
                        }
                    }
                }
            }
            let _ = sender.send(collected);
        });
        let collected = receiver
            .recv_timeout(std::time::Duration::from_secs(20))
            .unwrap_or_default();
        let _ = child.kill();
        assert!(
            collected.contains("pty-smoke-ok"),
            "PTY-Output: {collected}"
        );
    }
}
