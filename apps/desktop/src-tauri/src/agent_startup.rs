//! Project runtime selection and read-only probes in the terminal's login shell.

use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::Duration;

use serde::Serialize;
use tauri::AppHandle;
use wait_timeout::ChildExt;

const MARKER: &str = "\u{1e}SPECCIFY_START\0";
const REQUIRED_COMMANDS: &[&str] = &["expand", "export", "link", "tool"];

#[derive(Clone, Debug, Serialize)]
pub struct StartupReport {
    pub project: String,
    pub shell: String,
    pub host: String,
    pub host_path: Option<String>,
    pub host_version: Option<String>,
    pub host_ready: bool,
    pub runtime_source: String,
    pub runtime_dir: Option<String>,
    pub shell_cli: Option<String>,
    pub effective_cli: Option<String>,
    pub missing_commands: Vec<String>,
    pub warnings: Vec<String>,
    pub error: Option<String>,
    #[serde(skip)]
    pub launch: String,
}

fn runtime_dir(project: &Path, engine: Option<&Path>) -> (Option<PathBuf>, &'static str) {
    let workspace = crate::engine::bin_dir(&project.join(".venv"));
    if crate::sidecar::find_in_dir(&workspace, "speccify").is_some() {
        return (Some(workspace), "workspace");
    }
    if let Some(dir) = engine.map(crate::engine::bin_dir) {
        if crate::sidecar::find_in_dir(&dir, "speccify").is_some() {
            return (Some(dir), "engine");
        }
    }
    (None, "shell")
}

pub fn login_shell() -> String {
    #[cfg(not(windows))]
    {
        std::env::var("SHELL").unwrap_or_else(|_| "/bin/zsh".into())
    }
    #[cfg(windows)]
    {
        if crate::sidecar::resolve("pwsh.exe").0.is_some() {
            "pwsh.exe".into()
        } else {
            "powershell.exe".into()
        }
    }
}

pub(crate) fn quote(text: &str) -> String {
    if cfg!(windows) {
        format!("'{}'", text.replace('\'', "''"))
    } else {
        shell_words::quote(text).into_owned()
    }
}

pub fn path_setup(dir: Option<&Path>) -> String {
    match dir {
        Some(dir) if cfg!(windows) => format!(
            "$env:PATH = {} + ';' + $env:PATH; ",
            quote(&dir.display().to_string())
        ),
        Some(dir) => format!(
            "export PATH={}:\"$PATH\"; ",
            quote(&dir.display().to_string())
        ),
        None => String::new(),
    }
}

fn known_host(command: &str) -> Option<Vec<String>> {
    if command.contains(['$', '`', ';', '|', '&', '<', '>', '\n', '\r']) {
        return None;
    }
    let argv = shell_words::split(command).ok()?;
    let executable = argv.first()?;
    let name = executable
        .rsplit(['/', '\\'])
        .next()?
        .trim_end_matches(".cmd")
        .trim_end_matches(".exe");
    // Compound shell commands remain free commands: probing must never execute them.
    if !["codex", "claude"].contains(&name)
        || argv
            .iter()
            .any(|arg| [";", "&&", "||", "|", ">", "<", "&"].contains(&arg.as_str()))
    {
        return None;
    }
    Some(argv)
}

fn probe_script(dir: Option<&Path>, host: Option<&str>) -> String {
    let setup = path_setup(dir);
    if cfg!(windows) {
        let host_probe = host.map(|host| format!(
            "$speccifyProbeHost = (Get-Command {} -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source; $speccifyProbeVersion = ''; $speccifyProbeCode = 1; if ($speccifyProbeHost) {{ $speccifyProbeVersion = (& $speccifyProbeHost --version 2>$null | Out-String); $speccifyProbeCode = $LASTEXITCODE }}; ", quote(host)
        )).unwrap_or_else(|| "$speccifyProbeHost = ''; $speccifyProbeVersion = ''; $speccifyProbeCode = 0; ".into());
        return format!(
            "$speccifyProbeOriginal = (Get-Command speccify -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source; {setup}$speccifyProbeCli = (Get-Command speccify -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source; $speccifyProbeHelp = ''; if ($speccifyProbeCli) {{ $speccifyProbeHelp = (& $speccifyProbeCli --help 2>$null | Out-String) }}; {host_probe}[Console]::Write(([char]30 + 'SPECCIFY_START' + [char]0) + (@($speccifyProbeOriginal, $speccifyProbeCli, $speccifyProbeHelp, $speccifyProbeHost, $speccifyProbeVersion, [string]$speccifyProbeCode) -join [char]0) + [char]0)"
        );
    }
    let host_probe = host.map(|host| format!(
        "speccify_probe_host=$(command -v {host} 2>/dev/null); speccify_probe_version=$({host} --version 2>/dev/null); speccify_probe_code=$?; ", host = quote(host)
    )).unwrap_or_else(|| "speccify_probe_host=''; speccify_probe_version=''; speccify_probe_code=0; ".into());
    format!(
        "speccify_probe_original=$(command -v speccify 2>/dev/null); {setup}speccify_probe_cli=$(command -v speccify 2>/dev/null); speccify_probe_help=$(command speccify --help 2>/dev/null); {host_probe}printf '\\036SPECCIFY_START\\000%s\\000%s\\000%s\\000%s\\000%s\\000%s\\000' \"$speccify_probe_original\" \"$speccify_probe_cli\" \"$speccify_probe_help\" \"$speccify_probe_host\" \"$speccify_probe_version\" \"$speccify_probe_code\""
    )
}

fn capture(mut command: Command) -> Result<String, String> {
    let mut child = command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("Login-Shell konnte nicht gestartet werden: {e}"))?;
    let stdout = child.stdout.take().ok_or("Shell-Ausgabe fehlt")?;
    let (send, receive) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let mut bytes = Vec::new();
        let _ = stdout.take(512 * 1024).read_to_end(&mut bytes);
        let _ = send.send(bytes);
    });
    match child.wait_timeout(Duration::from_secs(15)) {
        Ok(Some(status)) if status.success() => {}
        result => {
            let _ = child.kill();
            let _ = child.wait();
            return Err(match result {
                Ok(Some(status)) => {
                    format!("Login-Shell-Prüfung fehlgeschlagen ({status}). Shell-Profil prüfen.")
                }
                _ => {
                    "Login-Shell-Prüfung nach 15 Sekunden abgebrochen. Shell-Profil und CLI prüfen."
                        .into()
                }
            });
        }
    }
    let bytes = receive
        .recv_timeout(Duration::from_secs(1))
        .map_err(|_| "Shell-Ausgabe nicht abgeschlossen")?;
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

fn optional(text: &str) -> Option<String> {
    (!text.trim().is_empty()).then(|| text.trim().to_string())
}

fn parse_report(
    output: &str,
    project: &Path,
    shell: &str,
    command: &str,
    dir: Option<&Path>,
    source: &str,
) -> Result<StartupReport, String> {
    let fields: Vec<_> = output.rsplit_once(MARKER).ok_or("Die Shell hat keine Startdiagnose geliefert. Unterstützt: zsh, bash, sh und PowerShell.")?.1.split('\0').collect();
    if fields.len() < 7 {
        return Err("Unvollständige Startdiagnose der Shell".into());
    }
    let argv = known_host(command);
    let mut report = StartupReport {
        project: project.display().to_string(),
        shell: shell.into(),
        host: if command.trim().is_empty() {
            "shell"
        } else if argv.is_some() {
            "agent"
        } else {
            "custom"
        }
        .into(),
        host_path: optional(fields[3]),
        host_version: fields[4].lines().find_map(optional),
        host_ready: argv.is_none() || (!fields[3].is_empty() && fields[5] == "0"),
        runtime_source: source.into(),
        runtime_dir: dir.map(|d| d.display().to_string()),
        shell_cli: optional(fields[0]),
        effective_cli: optional(fields[1]),
        missing_commands: REQUIRED_COMMANDS
            .iter()
            .filter(|name| !fields[2].split_whitespace().any(|word| word == **name))
            .map(|s| s.to_string())
            .collect(),
        warnings: Vec::new(),
        error: None,
        launch: command.into(),
    };
    if let Some(mut argv) = argv {
        if !report.host_ready {
            report.error = Some(format!("{} ist in der Login-Shell nicht startbar. Installation und `{} --version` im Terminal prüfen.", argv[0], argv[0]));
        } else if Path::new(fields[3]).is_absolute() {
            argv[0] = fields[3].into();
            report.launch = format!(
                "{}{}",
                if cfg!(windows) { "& " } else { "" },
                argv.iter().map(|a| quote(a)).collect::<Vec<_>>().join(" ")
            );
        } else {
            report.host_ready = false;
            report.error = Some("Das Agent-Kommando ist ein Alias oder eine Shell-Funktion. Bitte den ausführbaren Pfad als Kommando eintragen.".into());
        }
    } else if !command.trim().is_empty() {
        report.warnings.push("Freies Shell-Kommando: wird unverändert gestartet; keine automatische Funktionsprüfung.".into());
    }
    if report.effective_cli.is_none() {
        report.warnings.push("Speccify-CLI fehlt. Im Speccify-Checkout `uv sync --all-packages` ausführen oder im Umgebungs-Tab die App-Engine installieren. Bereits eingerichtete MCPs können separat genutzt werden.".into());
    } else if !report.missing_commands.is_empty() {
        report.warnings.push(format!("Speccify-CLI unvollständig: {} fehlen oder die Hilfe konnte nicht gelesen werden. Workspace synchronisieren bzw. App-Engine aktualisieren.", report.missing_commands.join(", ")));
    }
    if report.shell_cli.is_some() && report.shell_cli != report.effective_cli {
        report.warnings.push(
            "Die Projekt-/App-Runtime hat Vorrang vor der Speccify-Installation der Shell.".into(),
        );
    }
    Ok(report)
}

fn diagnose(
    project: &Path,
    command: &str,
    shell: &str,
    engine: Option<&Path>,
) -> Result<StartupReport, String> {
    let (dir, source) = runtime_dir(project, engine);
    let argv = known_host(command);
    let script = probe_script(
        dir.as_deref(),
        argv.as_ref().and_then(|a| a.first()).map(String::as_str),
    );
    let mut probe = Command::new(shell);
    if cfg!(windows) {
        probe.args(["-NoLogo", "-NonInteractive", "-Command", &script]);
    } else {
        let name = Path::new(shell)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("");
        if !["zsh", "bash", "sh", "dash"].contains(&name) {
            return Err("Startdiagnose unterstützt zsh, bash, sh und PowerShell. Für eine andere Shell ein leeres Autostart-Kommando verwenden.".into());
        }
        probe.args(["-lic", &script]);
    }
    probe
        .current_dir(project)
        .env("PATH", crate::augmented_path())
        .env("TERM", "xterm-256color")
        .env("NO_COLOR", "1")
        .env("COLUMNS", "160");
    let output = capture(probe)?;
    parse_report(&output, project, shell, command, dir.as_deref(), source)
}

pub fn prepare(app: &AppHandle, project: &Path, command: &str) -> Result<StartupReport, String> {
    let engine = crate::engine::engine_status(app.clone())
        .ok()
        .filter(|s| s.ready)
        .map(|s| PathBuf::from(s.venv_dir));
    diagnose(project, command, &login_shell(), engine.as_deref())
}

#[tauri::command]
pub async fn project_agent_startup(
    app: AppHandle,
    project: String,
    command: String,
) -> Result<StartupReport, String> {
    let project = crate::project_cmd::resolve_project_root(&project)?;
    tauri::async_runtime::spawn_blocking(move || prepare(&app, &project, &command))
        .await
        .map_err(|e| e.to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_host_and_incomplete_cli_are_not_ready() {
        let output =
            format!("profile output{MARKER}/old/speccify\0/old/speccify\0init search\0\0\0127\0");
        let report = parse_report(
            &output,
            Path::new("/project"),
            "/bin/zsh",
            "codex",
            None,
            "shell",
        )
        .unwrap();
        assert!(!report.host_ready);
        assert!(report.error.is_some());
        assert_eq!(report.missing_commands.len(), 4);
        assert_eq!(report.effective_cli.as_deref(), Some("/old/speccify"));
    }

    #[test]
    fn custom_commands_are_never_executed_by_the_probe() {
        assert!(known_host("printf side-effect > file").is_none());
        assert!(known_host("codex && touch file").is_none());
        let script = probe_script(None, None);
        assert!(!script.contains("side-effect"));
        let output = format!("{MARKER}\0\0\0\0\00\0");
        let report =
            parse_report(&output, Path::new("/project"), "shell", "", None, "shell").unwrap();
        assert!(report.host_ready);
        assert_eq!(report.host, "shell");
    }

    #[cfg(unix)]
    #[test]
    fn login_shell_uses_workspace_over_old_path_and_quotes_paths() {
        use std::os::unix::fs::PermissionsExt;
        let dir =
            std::env::temp_dir().join(format!("speccify-startup-{}-space ' $", std::process::id()));
        let bin = crate::engine::bin_dir(&dir.join(".venv"));
        std::fs::create_dir_all(&bin).unwrap();
        let old = dir.join("old-bin");
        std::fs::create_dir_all(&old).unwrap();
        let old_cli = old.join("speccify");
        std::fs::write(&old_cli, "#!/bin/sh\nprintf 'init search\\n'\n").unwrap();
        std::fs::set_permissions(&old_cli, std::fs::Permissions::from_mode(0o755)).unwrap();
        std::fs::write(
            dir.join(".zshrc"),
            format!(
                "export PATH={}:\"$PATH\"\n",
                quote(&old.display().to_string())
            ),
        )
        .unwrap();
        for (name, body) in [
            (
                "speccify",
                "#!/bin/sh\nprintf 'expand export link tool\\n'\n",
            ),
            ("codex", "#!/bin/sh\nprintf 'codex-cli test-version\\n'\n"),
        ] {
            let file = bin.join(name);
            std::fs::write(&file, body).unwrap();
            std::fs::set_permissions(file, std::fs::Permissions::from_mode(0o755)).unwrap();
        }
        let (selected, source) = runtime_dir(&dir, None);
        assert_eq!(source, "workspace");
        for initial_path in [
            "/usr/bin:/bin".to_string(),
            format!("{}:/usr/bin:/bin", old.display()),
        ] {
            let mut probe = Command::new("/bin/zsh");
            probe
                .args(["-lic", &probe_script(selected.as_deref(), Some("codex"))])
                .current_dir(&dir)
                .env("ZDOTDIR", &dir)
                .env("PATH", &initial_path);
            let output = capture(probe).unwrap();
            let report = parse_report(
                &output,
                &dir,
                "/bin/zsh",
                "codex --model 'a b'",
                selected.as_deref(),
                source,
            )
            .unwrap();
            assert!(report.host_ready, "{report:?}");
            assert!(report.missing_commands.is_empty());
            assert_eq!(report.shell_cli, Some(old_cli.display().to_string()));
            assert_eq!(
                report.host_path,
                Some(bin.join("codex").display().to_string())
            );
            assert_eq!(shell_words::split(&report.launch).unwrap()[2], "a b");
            let mut start = Command::new("/bin/zsh");
            start
                .args([
                    "-lic",
                    &format!("{}command -v speccify", path_setup(selected.as_deref())),
                ])
                .current_dir(&dir)
                .env("ZDOTDIR", &dir)
                .env("PATH", &initial_path);
            assert!(capture(start)
                .unwrap()
                .contains(&bin.join("speccify").display().to_string()));
        }
        // Without a workspace CLI the same probe exposes the old installation.
        let mut old_probe = Command::new("/bin/zsh");
        old_probe
            .args([
                "-lic",
                &probe_script(None, Some("speccify-test-missing-host")),
            ])
            .current_dir(&dir)
            .env("ZDOTDIR", &dir)
            .env("PATH", "/usr/bin:/bin");
        let report = parse_report(
            &capture(old_probe).unwrap(),
            &dir,
            "/bin/zsh",
            "codex",
            None,
            "shell",
        )
        .unwrap();
        assert!(!report.host_ready);
        assert_eq!(report.missing_commands.len(), 4);
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn engine_is_selected_only_when_no_workspace_cli_exists() {
        let dir =
            std::env::temp_dir().join(format!("speccify-startup-selection-{}", std::process::id()));
        let project = dir.join("project");
        let engine = dir.join("engine");
        let bin = crate::engine::bin_dir(&engine);
        std::fs::create_dir_all(&bin).unwrap();
        std::fs::write(bin.join("speccify"), "fixture").unwrap();
        assert_eq!(runtime_dir(&project, Some(&engine)), (Some(bin), "engine"));
        let workspace_bin = crate::engine::bin_dir(&project.join(".venv"));
        std::fs::create_dir_all(&workspace_bin).unwrap();
        std::fs::write(workspace_bin.join("speccify"), "fixture").unwrap();
        assert_eq!(
            runtime_dir(&project, Some(&engine)),
            (Some(workspace_bin), "workspace")
        );
        assert_eq!(runtime_dir(&dir.join("other"), None), (None, "shell"));
        std::fs::remove_dir_all(dir).unwrap();
    }
}
