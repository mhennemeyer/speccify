//! CLI des Exec-MCP: Streamable HTTP (Default, 127.0.0.1:8765, inkl.
//! `/stream`-SSE) oder stdio (`--stdio`, JSON-RPC ohne /stream).
//! `--project <root>` = bound-Modus, sonst multi.

use std::io::Write;
use std::sync::Arc;

use serde_json::Value;
use speccify_exec_mcp::{DEFAULT_PORT, DEFAULT_TIMEOUT_SECONDS, ExecMcp};

fn main() {
    let mut port = DEFAULT_PORT;
    let mut stdio = false;
    let mut timeout = DEFAULT_TIMEOUT_SECONDS;
    let mut project: Option<String> = None;

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--port" => port = parse_next(&mut args, "--port"),
            "--timeout" => timeout = parse_next(&mut args, "--timeout"),
            "--project" | "-p" => project = args.next(),
            "--stdio" => stdio = true,
            "--help" | "-h" => {
                eprintln!(
                    "speccify-exec-mcp [--port {DEFAULT_PORT}] [--timeout {DEFAULT_TIMEOUT_SECONDS}] [--project <root>] [--stdio]"
                );
                return;
            }
            other => {
                eprintln!("Unbekanntes Argument: {other}");
                std::process::exit(2);
            }
        }
    }

    let root = project.map(std::path::PathBuf::from);
    if let Some(root) = &root
        && !root.is_dir()
    {
        eprintln!("Projekt-Root existiert nicht: {}", root.display());
        std::process::exit(1);
    }

    let exec = Arc::new(ExecMcp::new(root, timeout));

    if stdio {
        speccify_mcp_core::serve_stdio(exec.as_ref());
        return;
    }

    // /stream-Handler: SSE-Events aus ExecMcp::stream_run auf den Socket.
    let exec_for_stream = Arc::clone(&exec);
    let stream: Arc<speccify_mcp_core::StreamHandler> =
        Arc::new(move |body: &Value, writer: &mut dyn Write| {
            let empty = serde_json::Map::new();
            let arguments = body.as_object().unwrap_or(&empty);
            let mut emit = |event: &Value| -> std::io::Result<()> {
                writer.write_all(format!("data: {event}\n\n").as_bytes())?;
                writer.flush()
            };
            exec_for_stream.stream_run(arguments, &mut emit);
        });

    eprintln!("speccify-exec-mcp läuft auf http://127.0.0.1:{port}");
    let server: Arc<dyn speccify_mcp_core::ToolServer> = exec;
    if let Err(error) =
        speccify_mcp_core::serve_http(server, port, "speccify exec-mcp", Some(stream))
    {
        eprintln!("{error}");
        std::process::exit(1);
    }
}

fn parse_next<T: std::str::FromStr>(args: &mut impl Iterator<Item = String>, flag: &str) -> T {
    args.next()
        .and_then(|raw| raw.parse().ok())
        .unwrap_or_else(|| {
            eprintln!("{flag} braucht einen gültigen Wert.");
            std::process::exit(2);
        })
}
