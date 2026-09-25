//! `speccify-pty-host --state <datei> [--idle <sek>] [--buffer <bytes>]`
//!
//! Bindet 127.0.0.1 an einen freien Port, erzeugt ein Token, schreibt die
//! Zustandsdatei und bedient Clients, bis er `--idle` Sekunden lang weder
//! Client noch lebende Sitzung hat. Die App startet ihn losgelöst (eigene
//! Sitzung/Prozessgruppe), deshalb überlebt er ihr Ende.

use std::net::TcpListener;
use std::path::PathBuf;
use std::time::Duration;

use speccify_pty_host::{
    DEFAULT_BUFFER_BYTES, DEFAULT_IDLE_SECS, Host, HostState, PROTOCOL_VERSION, idle_watch,
    write_state,
};

fn main() {
    let mut state: Option<PathBuf> = None;
    let mut idle = DEFAULT_IDLE_SECS;
    let mut buffer = DEFAULT_BUFFER_BYTES;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--state" => state = args.next().map(PathBuf::from),
            "--idle" => idle = args.next().and_then(|v| v.parse().ok()).unwrap_or(idle),
            "--buffer" => buffer = args.next().and_then(|v| v.parse().ok()).unwrap_or(buffer),
            "--version" => {
                println!(
                    "speccify-pty-host {} (protocol {PROTOCOL_VERSION})",
                    env!("CARGO_PKG_VERSION")
                );
                return;
            }
            other => {
                eprintln!("Unbekanntes Argument: {other}");
                std::process::exit(2);
            }
        }
    }
    let Some(state_path) = state else {
        eprintln!("--state <datei> fehlt");
        std::process::exit(2);
    };
    let listener = match TcpListener::bind(("127.0.0.1", 0)) {
        Ok(listener) => listener,
        Err(error) => {
            eprintln!("Port: {error}");
            std::process::exit(1);
        }
    };
    let port = listener.local_addr().map(|a| a.port()).unwrap_or(0);
    let token = uuid::Uuid::new_v4().simple().to_string();
    let host = Host::new(token.clone(), env!("CARGO_PKG_VERSION").to_owned(), buffer);
    let record = HostState {
        port,
        token,
        pid: std::process::id(),
        protocol: PROTOCOL_VERSION,
        version: env!("CARGO_PKG_VERSION").to_owned(),
    };
    if let Err(error) = write_state(&state_path, &record) {
        eprintln!("Zustandsdatei {}: {error}", state_path.display());
        std::process::exit(1);
    }
    let cleanup_path = state_path.clone();
    idle_watch(host.clone(), Duration::from_secs(idle), move || {
        // Nur die eigene Datei entfernen — ein Nachfolger könnte sie schon
        // überschrieben haben.
        if speccify_pty_host::read_state(&cleanup_path).is_some_and(|s| s.pid == std::process::id())
        {
            let _ = std::fs::remove_file(&cleanup_path);
        }
    });
    println!("speccify-pty-host bereit auf 127.0.0.1:{port}");
    host.serve(listener);
}
