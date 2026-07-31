//! Auflösung der mitgelieferten MCP-Binaries (Plan r5-distribution.md, R5.1/D1).
//!
//! Die verteilte App bringt `speccify-exec-mcp`, `speccify-discovery-mcp` und
//! `speccify-parallels-mcp` als Tauri-Sidecars mit; macOS legt sie neben das
//! App-Binary (`Speccify.app/Contents/MacOS/`). Reihenfolge beim Auflösen:
//!
//!   1. gebündelt (neben `current_exe`)  → verteilte App, kein Rust nötig
//!   2. PATH (angereichert, s. `crate::augmented_path`) → Entwickler-Betrieb
//!      mit `cargo install --path crates/…` und `tauri dev` (dort liegen keine
//!      Sidecars neben dem Debug-Binary)
//!
//! Absolute bzw. pfadhaltige Kommandos aus eigenen Toolbox-Manifesten bleiben
//! unverändert — wer einen Pfad hinschreibt, meint ihn auch.

use std::path::{Path, PathBuf};

/// Woher ein Kommando aufgelöst wurde — die UI zeigt das im Server-Tab an.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum BinarySource {
    /// Aus dem App-Bundle (Sidecar).
    Bundled,
    /// Aus der installierten Python-Engine (`<venv>/bin`, R5.2).
    Engine,
    /// Über den angereicherten PATH gefunden.
    Path,
    /// Im Manifest stand ein Pfad, der existiert.
    Explicit,
    /// Nirgends gefunden.
    Missing,
}

/// Reine Auflösungsfunktion (testbar): sucht `command` erst in `bundle_dir`,
/// dann in `path_dirs`.
pub fn resolve_in(
    command: &str,
    bundle_dir: Option<&Path>,
    path_dirs: &[PathBuf],
) -> (Option<PathBuf>, BinarySource) {
    if command.contains('/') {
        let explicit = PathBuf::from(command);
        return if explicit.is_file() {
            (Some(explicit), BinarySource::Explicit)
        } else {
            (None, BinarySource::Missing)
        };
    }
    if let Some(dir) = bundle_dir {
        let candidate = dir.join(command);
        if candidate.is_file() {
            return (Some(candidate), BinarySource::Bundled);
        }
    }
    for dir in path_dirs {
        let candidate = dir.join(command);
        if candidate.is_file() {
            return (Some(candidate), BinarySource::Path);
        }
    }
    (None, BinarySource::Missing)
}

/// Verzeichnis neben dem laufenden App-Binary (dort landen die Sidecars).
pub fn bundle_dir() -> Option<PathBuf> {
    std::env::current_exe()
        .ok()
        .and_then(|exe| exe.parent().map(Path::to_path_buf))
}

/// Auflösung gegen die echte Umgebung.
pub fn resolve(command: &str) -> (Option<PathBuf>, BinarySource) {
    let dirs: Vec<PathBuf> = std::env::split_paths(&crate::augmented_path()).collect();
    resolve_in(command, bundle_dir().as_deref(), &dirs)
}

/// Für den Prozess-Start: aufgelöster Pfad, sonst das Kommando unverändert
/// (dann meldet der Spawn selbst einen aussagekräftigen Fehler).
pub fn command_for_spawn(command: &str) -> PathBuf {
    resolve(command).0.unwrap_or_else(|| PathBuf::from(command))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn touch_exec(dir: &Path, name: &str) {
        let path = dir.join(name);
        std::fs::write(&path, b"#!/bin/sh\n").unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).unwrap();
        }
    }

    fn tempdir(tag: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-sidecar-{tag}-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn bundled_wins_over_path() {
        let bundle = tempdir("bundle");
        let path_dir = tempdir("path");
        touch_exec(&bundle, "speccify-exec-mcp");
        touch_exec(&path_dir, "speccify-exec-mcp");

        let (resolved, source) = resolve_in(
            "speccify-exec-mcp",
            Some(&bundle),
            std::slice::from_ref(&path_dir),
        );
        assert_eq!(source, BinarySource::Bundled);
        assert_eq!(resolved.unwrap(), bundle.join("speccify-exec-mcp"));

        std::fs::remove_dir_all(&bundle).ok();
        std::fs::remove_dir_all(&path_dir).ok();
    }

    #[test]
    fn falls_back_to_path_without_bundle() {
        let path_dir = tempdir("path-only");
        touch_exec(&path_dir, "speccify-discovery-mcp");

        let (resolved, source) = resolve_in(
            "speccify-discovery-mcp",
            None,
            std::slice::from_ref(&path_dir),
        );
        assert_eq!(source, BinarySource::Path);
        assert_eq!(resolved.unwrap(), path_dir.join("speccify-discovery-mcp"));

        std::fs::remove_dir_all(&path_dir).ok();
    }

    #[test]
    fn missing_binary_reports_missing() {
        let (resolved, source) = resolve_in("speccify-nicht-da", None, &[]);
        assert_eq!(source, BinarySource::Missing);
        assert!(resolved.is_none());
    }

    #[test]
    fn explicit_path_is_kept() {
        let dir = tempdir("explicit");
        touch_exec(&dir, "eigenes-binary");
        let literal = dir.join("eigenes-binary").display().to_string();

        let (resolved, source) = resolve_in(&literal, None, &[]);
        assert_eq!(source, BinarySource::Explicit);
        assert_eq!(resolved.unwrap(), dir.join("eigenes-binary"));

        // Pfadhaltig, aber nicht vorhanden ⇒ kein PATH-Fallback.
        let (missing, source) =
            resolve_in("./gibts-nicht/binary", None, std::slice::from_ref(&dir));
        assert_eq!(source, BinarySource::Missing);
        assert!(missing.is_none());

        std::fs::remove_dir_all(&dir).ok();
    }
}
