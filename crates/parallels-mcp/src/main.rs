//! CLI des Parallels-MCP: Streamable HTTP (Default, 127.0.0.1:8766) oder
//! stdio (`--stdio`). `--project <root>` (Pflicht: Home-Share-Basis + cwd),
//! optional `--vm <name>` und `--home <pfad>`.

use std::process::{Command, Stdio};
use std::sync::Arc;

use speccify_parallels_mcp::{DEFAULT_PORT, ParallelsMcp, RunError, RunOutput, Runner};
use wait_timeout::ChildExt;

fn main() {
    let mut port = DEFAULT_PORT;
    let mut stdio = false;
    let mut project: Option<String> = None;
    let mut vm: Option<String> = None;
    let mut home: Option<String> = None;

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--port" => {
                port = args
                    .next()
                    .and_then(|raw| raw.parse().ok())
                    .unwrap_or(DEFAULT_PORT)
            }
            "--project" | "-p" => project = args.next(),
            "--vm" => vm = args.next(),
            "--home" => home = args.next(),
            "--stdio" => stdio = true,
            "--help" | "-h" => {
                eprintln!(
                    "speccify-parallels-mcp --project <root> [--vm <name>] [--home <pfad>] [--port {DEFAULT_PORT}] [--stdio]"
                );
                return;
            }
            other => {
                eprintln!("Unbekanntes Argument: {other}");
                std::process::exit(2);
            }
        }
    }

    let Some(project) = project else {
        eprintln!("--project <root> ist erforderlich.");
        std::process::exit(2);
    };
    let project_root = std::path::PathBuf::from(project);
    if !project_root.is_dir() {
        eprintln!("Projekt-Root existiert nicht: {}", project_root.display());
        std::process::exit(1);
    }
    let home = home
        .map(std::path::PathBuf::from)
        .or_else(|| std::env::var("HOME").ok().map(std::path::PathBuf::from))
        .unwrap_or_else(|| project_root.clone());

    let runner: Box<Runner> = Box::new(real_runner);
    let server = Arc::new(ParallelsMcp::new(project_root, vm, home, runner));

    if stdio {
        speccify_mcp_core::serve_stdio(server.as_ref());
        return;
    }
    eprintln!("speccify-parallels-mcp läuft auf http://127.0.0.1:{port}");
    let tool_server: Arc<dyn speccify_mcp_core::ToolServer> = server;
    if let Err(error) =
        speccify_mcp_core::serve_http(tool_server, port, "speccify parallels-mcp", None)
    {
        eprintln!("{error}");
        std::process::exit(1);
    }
}

/// Echter prlctl-Runner: spawnt das Programm, sammelt Output mit Timeout.
fn real_runner(argv: &[String], timeout: f64) -> Result<RunOutput, RunError> {
    let mut child = match Command::new(&argv[0])
        .args(&argv[1..])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
    {
        Ok(child) => child,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Err(RunError::NotFound);
        }
        Err(_) => return Err(RunError::NotFound),
    };

    let mut stdout_pipe = child.stdout.take();
    let mut stderr_pipe = child.stderr.take();
    let out_handle = std::thread::spawn(move || read_all(stdout_pipe.as_mut()));
    let err_handle = std::thread::spawn(move || read_all(stderr_pipe.as_mut()));

    match child.wait_timeout(std::time::Duration::from_secs_f64(timeout)) {
        Ok(Some(status)) => Ok(RunOutput {
            code: status.code(),
            stdout: out_handle.join().unwrap_or_default(),
            stderr: err_handle.join().unwrap_or_default(),
        }),
        _ => {
            let _ = child.kill();
            let _ = child.wait();
            Err(RunError::Timeout {
                stdout: out_handle.join().unwrap_or_default(),
                stderr: err_handle.join().unwrap_or_default(),
            })
        }
    }
}

fn read_all<R: std::io::Read>(reader: Option<&mut R>) -> String {
    let mut buffer = String::new();
    if let Some(reader) = reader {
        let _ = reader.read_to_string(&mut buffer);
    }
    buffer
}
