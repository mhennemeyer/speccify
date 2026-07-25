//! CLI des Discovery-MCP: Streamable HTTP (Default, 127.0.0.1:8767)
//! oder stdio (`--stdio`, für `claude mcp add` ohne laufende App).

use std::sync::Arc;

use speccify_discovery_mcp::{DEFAULT_PORT, DiscoveryMcp};

fn main() {
    let mut port = DEFAULT_PORT;
    let mut stdio = false;
    let mut working_dir: Option<String> = None;

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--port" => {
                port = args
                    .next()
                    .and_then(|raw| raw.parse().ok())
                    .unwrap_or_else(|| {
                        eprintln!("--port braucht eine Zahl.");
                        std::process::exit(2);
                    });
            }
            "--stdio" => stdio = true,
            "--working-dir" => working_dir = args.next(),
            "--help" | "-h" => {
                eprintln!(
                    "speccify-discovery-mcp [--port {DEFAULT_PORT}] [--stdio] [--working-dir <pfad>]"
                );
                return;
            }
            other => {
                eprintln!("Unbekanntes Argument: {other}");
                std::process::exit(2);
            }
        }
    }

    let mut server = DiscoveryMcp::from_env();
    if let Some(dir) = working_dir {
        let path = std::path::PathBuf::from(dir);
        if !path.is_dir() {
            eprintln!("--working-dir existiert nicht: {}", path.display());
            std::process::exit(2);
        }
        server.working_dir = Some(path);
    }

    if stdio {
        speccify_mcp_core::serve_stdio(&server);
        return;
    }
    eprintln!("speccify-discovery-mcp läuft auf http://127.0.0.1:{port}");
    if let Err(error) =
        speccify_mcp_core::serve_http(Arc::new(server), port, "speccify discovery-mcp", None)
    {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
