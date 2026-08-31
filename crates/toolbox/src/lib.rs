//! Toolbox-Manifeste (Plan toolkit-discovery-terminal.md, T2/D1).
//!
//! Format 1:1 aus dotagent (`src/dotagent/registry/{model,store}.py`):
//! TOML mit `kind = "tool" | "mcp" | "kb"`, `name`, `slug`, optional
//! `description/tags/category`, `[run] command/args/transport/autostart`,
//! `[requires] binaries`. Drei Quellen mit Vorrang bei Slug-Kollision:
//! `workingdir` > `global` (`~/.speccify/toolbox/`) > `builtin`
//! (im Binary eingebettet, `builtin/*.toml`).

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

pub const KINDS: &[&str] = &["tool", "mcp", "kb"];
pub const TRANSPORTS: &[&str] = &["stdio", "sse", "http"];

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RunSpec {
    pub command: String,
    #[serde(default)]
    pub args: Vec<String>,
    #[serde(default = "default_transport")]
    pub transport: String,
    #[serde(default)]
    pub autostart: bool,
}

fn default_transport() -> String {
    "stdio".into()
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Manifest {
    pub kind: String,
    pub name: String,
    pub slug: String,
    pub description: String,
    pub tags: Vec<String>,
    pub category: String,
    pub run: Option<RunSpec>,
    pub requires_binaries: Vec<String>,
    pub source: String,
    pub path: Option<String>,
}

// --- Parsing -------------------------------------------------------------------

#[derive(Deserialize)]
struct RawManifest {
    kind: Option<String>,
    name: Option<String>,
    slug: Option<String>,
    #[serde(default)]
    description: String,
    #[serde(default)]
    tags: Vec<String>,
    #[serde(default)]
    category: String,
    run: Option<RawRun>,
    requires: Option<RawRequires>,
}

#[derive(Deserialize)]
struct RawRun {
    command: Option<String>,
    #[serde(default)]
    args: Vec<String>,
    transport: Option<String>,
    #[serde(default)]
    autostart: bool,
}

#[derive(Deserialize)]
struct RawRequires {
    #[serde(default)]
    binaries: Vec<String>,
}

pub fn parse_manifest(text: &str, source: &str, path: Option<&Path>) -> Result<Manifest, String> {
    let raw: RawManifest =
        toml::from_str(text).map_err(|e| format!("Ungültiges TOML: {}", e.message()))?;

    let mut missing = Vec::new();
    for (key, value) in [
        ("kind", &raw.kind),
        ("name", &raw.name),
        ("slug", &raw.slug),
    ] {
        if value.as_deref().unwrap_or("").is_empty() {
            missing.push(key);
        }
    }
    if !missing.is_empty() {
        return Err(format!("Pflichtfelder fehlen: {}", missing.join(", ")));
    }
    let kind = raw.kind.unwrap();
    if !KINDS.contains(&kind.as_str()) {
        return Err(format!(
            "Unbekanntes kind: '{kind}' (erlaubt: {})",
            KINDS.join(", ")
        ));
    }

    let run = match raw.run {
        None => None,
        Some(run) => {
            let command = run
                .command
                .filter(|command| !command.is_empty())
                .ok_or("[run] braucht ein command-Feld")?;
            let transport = run.transport.unwrap_or_else(default_transport);
            if !TRANSPORTS.contains(&transport.as_str()) {
                return Err(format!(
                    "Unbekannter transport: '{transport}' (erlaubt: {})",
                    TRANSPORTS.join(", ")
                ));
            }
            Some(RunSpec {
                command,
                args: run.args,
                transport,
                autostart: run.autostart,
            })
        }
    };

    Ok(Manifest {
        kind,
        name: raw.name.unwrap(),
        slug: raw.slug.unwrap(),
        description: raw.description,
        tags: raw.tags,
        category: raw.category,
        run,
        requires_binaries: raw.requires.map(|r| r.binaries).unwrap_or_default(),
        source: source.to_string(),
        path: path.map(|p| p.display().to_string()),
    })
}

// --- Builtin-Manifeste -----------------------------------------------------------

const BUILTINS: &[(&str, &str)] = &[
    (
        "speccify-exec.toml",
        include_str!("../builtin/speccify-exec.toml"),
    ),
    (
        "speccify-discovery.toml",
        include_str!("../builtin/speccify-discovery.toml"),
    ),
    (
        "parallels-dotnet.toml",
        include_str!("../builtin/parallels-dotnet.toml"),
    ),
    (
        "playwright.toml",
        include_str!("../builtin/playwright.toml"),
    ),
    (
        "speccify-mcp.toml",
        include_str!("../builtin/speccify-mcp.toml"),
    ),
];

pub fn builtin_manifests() -> Vec<Manifest> {
    BUILTINS
        .iter()
        .map(|(file, text)| {
            parse_manifest(text, "builtin", None)
                .unwrap_or_else(|e| panic!("builtin/{file} invalide: {e}"))
        })
        .collect()
}

// --- Store -------------------------------------------------------------------

pub fn load_dir(directory: &Path, source: &str) -> (Vec<Manifest>, Vec<String>) {
    let mut manifests = Vec::new();
    let mut warnings = Vec::new();
    let Ok(entries) = std::fs::read_dir(directory) else {
        return (manifests, warnings);
    };
    let mut files: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "toml"))
        .collect();
    files.sort();
    for file in files {
        match std::fs::read_to_string(&file) {
            Ok(text) => match parse_manifest(&text, source, Some(&file)) {
                Ok(manifest) => manifests.push(manifest),
                Err(error) => warnings.push(format!("{}: {error}", file.display())),
            },
            Err(error) => warnings.push(format!("{}: {error}", file.display())),
        }
    }
    (manifests, warnings)
}

/// Merged builtin + global + working dir; bei Slug-Kollision gewinnt die
/// spezifischste Quelle. Sortiert nach (kind, slug) wie dotagent.
pub fn load_all(
    global_dir: Option<&Path>,
    working_dir: Option<&Path>,
) -> (Vec<Manifest>, Vec<String>) {
    let mut warnings = Vec::new();
    let mut merged: Vec<Manifest> = Vec::new();

    let mut layers: Vec<Vec<Manifest>> = vec![builtin_manifests()];
    if let Some(dir) = global_dir {
        let (manifests, layer_warnings) = load_dir(dir, "global");
        warnings.extend(layer_warnings);
        layers.push(manifests);
    }
    if let Some(root) = working_dir {
        let (manifests, layer_warnings) =
            load_dir(&root.join(".speccify").join("toolbox"), "workingdir");
        warnings.extend(layer_warnings);
        layers.push(manifests);
    }

    // Spätere Layer (spezifischer) überschreiben frühere per Slug.
    for layer in layers {
        for manifest in layer {
            merged.retain(|existing| existing.slug != manifest.slug);
            merged.push(manifest);
        }
    }
    merged.sort_by_key(|manifest| (manifest.kind.clone(), manifest.slug.clone()));
    (merged, warnings)
}

// --- MCP-Utilities (geteilt von Discovery-MCP und Desktop-Server-Tab) ---------

/// Bekannte HTTP-Ports der builtin-Server (Fallback, wenn im Manifest kein
/// `--port`-Argument steht).
pub const KNOWN_HTTP_PORTS: &[(&str, u16)] = &[
    ("speccify-exec", 8765),
    ("parallels-dotnet", 8766),
    ("speccify-discovery", 8767),
];

/// HTTP-Port eines MCP-Manifests: `--port <n>` aus den run-Args, sonst
/// bekannter Default je Slug.
pub fn http_port(manifest: &Manifest) -> Option<u16> {
    let run = manifest.run.as_ref()?;
    if run.transport != "http" {
        return None;
    }
    if let Some(index) = run.args.iter().position(|arg| arg == "--port")
        && let Some(port) = run.args.get(index + 1).and_then(|raw| raw.parse().ok())
    {
        return Some(port);
    }
    KNOWN_HTTP_PORTS
        .iter()
        .find(|(slug, _)| *slug == manifest.slug)
        .map(|(_, port)| *port)
}

/// Nimmt der Port gerade Verbindungen an? (Laufzeitstatus für http-Server.)
pub fn probe_port(port: u16) -> bool {
    std::net::TcpStream::connect_timeout(
        &std::net::SocketAddr::from(([127, 0, 0, 1], port)),
        std::time::Duration::from_millis(150),
    )
    .is_ok()
}

/// Hostneutrale Client-Konfiguration für einen Manifest-Eintrag (http → URL,
/// sonst command/args für stdio), die Clients in ihr natives Format übertragen.
pub fn client_config(manifest: &Manifest) -> Option<serde_json::Value> {
    let run = manifest.run.as_ref()?;
    if run.transport == "http" {
        let port = http_port(manifest)?;
        return Some(serde_json::json!({
            "type": "http",
            "url": format!("http://127.0.0.1:{port}"),
        }));
    }
    Some(serde_json::json!({"command": run.command, "args": run.args}))
}

// --- Scaffold ------------------------------------------------------------------

const MANIFEST_TEMPLATE: &str = r#"kind        = "{kind}"
name        = "{name}"
slug        = "{slug}"
description = ""
tags        = []

# Optional: startbarer Prozess (typisch für kind = "mcp"):
# [run]
# command   = "npx"
# args      = ["mein-mcp"]
# transport = "stdio"   # stdio | sse | http
# autostart = false

# Optional: Binaries, deren Vorhandensein vor dem Start geprüft wird:
# [requires]
# binaries = []
"#;

/// Legt ein neues Manifest an (niemals überschreiben). → Pfad der Datei.
pub fn scaffold(directory: &Path, slug: &str, kind: &str, name: &str) -> Result<PathBuf, String> {
    if slug.is_empty() || !slug.chars().all(|c| c.is_ascii_alphanumeric() || c == '-') {
        return Err(format!("Ungültiger Slug: '{slug}' (a-z, 0-9, '-')."));
    }
    if !KINDS.contains(&kind) {
        return Err(format!(
            "Unbekanntes kind: '{kind}' (erlaubt: {})",
            KINDS.join(", ")
        ));
    }
    let target = directory.join(format!("{slug}.toml"));
    if target.exists() {
        return Err(format!(
            "{} existiert bereits — wird nicht überschrieben.",
            target.display()
        ));
    }
    std::fs::create_dir_all(directory).map_err(|e| format!("{}: {e}", directory.display()))?;
    let content = MANIFEST_TEMPLATE
        .replace("{kind}", kind)
        .replace("{name}", if name.is_empty() { slug } else { name })
        .replace("{slug}", slug);
    std::fs::write(&target, content).map_err(|e| format!("{}: {e}", target.display()))?;
    Ok(target)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(label: &str) -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("speccify-toolbox-{label}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn parses_full_manifest() {
        let manifest = parse_manifest(
            r#"
kind = "mcp"
name = "Test"
slug = "test"
description = "d"
tags = ["a", "b"]
category = "c"

[run]
command = "npx"
args = ["x"]
transport = "http"
autostart = true

[requires]
binaries = ["npx"]
"#,
            "global",
            None,
        )
        .unwrap();
        assert_eq!(manifest.kind, "mcp");
        let run = manifest.run.unwrap();
        assert_eq!(run.transport, "http");
        assert!(run.autostart);
        assert_eq!(manifest.requires_binaries, vec!["npx"]);
    }

    #[test]
    fn rejects_missing_fields_unknown_kind_and_transport() {
        assert!(
            parse_manifest("kind = \"tool\"", "global", None)
                .unwrap_err()
                .contains("Pflichtfelder fehlen")
        );
        assert!(
            parse_manifest(
                "kind = \"nope\"\nname = \"x\"\nslug = \"x\"",
                "global",
                None
            )
            .unwrap_err()
            .contains("Unbekanntes kind")
        );
        assert!(parse_manifest(
            "kind = \"mcp\"\nname = \"x\"\nslug = \"x\"\n[run]\ncommand = \"c\"\ntransport = \"tcp\"",
            "global",
            None
        )
        .unwrap_err()
        .contains("Unbekannter transport"));
    }

    #[test]
    fn builtin_manifests_are_valid_and_present() {
        let builtins = builtin_manifests();
        let slugs: Vec<&str> = builtins.iter().map(|m| m.slug.as_str()).collect();
        for expected in [
            "speccify-exec",
            "speccify-discovery",
            "parallels-dotnet",
            "playwright",
            "speccify-mcp",
        ] {
            assert!(slugs.contains(&expected), "fehlt: {expected}");
        }
    }

    #[test]
    fn working_dir_overrides_global_overrides_builtin() {
        let global = temp_dir("global");
        let working = temp_dir("working");
        std::fs::write(
            global.join("playwright.toml"),
            "kind = \"mcp\"\nname = \"Global-Playwright\"\nslug = \"playwright\"",
        )
        .unwrap();
        let toolbox = working.join(".speccify/toolbox");
        std::fs::create_dir_all(&toolbox).unwrap();
        std::fs::write(
            toolbox.join("playwright.toml"),
            "kind = \"mcp\"\nname = \"WD-Playwright\"\nslug = \"playwright\"",
        )
        .unwrap();

        let (manifests, warnings) = load_all(Some(&global), Some(&working));
        assert!(warnings.is_empty());
        let playwright = manifests.iter().find(|m| m.slug == "playwright").unwrap();
        assert_eq!(playwright.name, "WD-Playwright");
        assert_eq!(playwright.source, "workingdir");
        let _ = std::fs::remove_dir_all(&global);
        let _ = std::fs::remove_dir_all(&working);
    }

    #[test]
    fn scaffold_creates_once_and_result_parses() {
        let dir = temp_dir("scaffold");
        let path = scaffold(&dir, "mein-tool", "tool", "Mein Tool").unwrap();
        let text = std::fs::read_to_string(&path).unwrap();
        let manifest = parse_manifest(&text, "workingdir", Some(&path)).unwrap();
        assert_eq!(manifest.slug, "mein-tool");
        assert!(
            scaffold(&dir, "mein-tool", "tool", "X")
                .unwrap_err()
                .contains("existiert bereits")
        );
        assert!(scaffold(&dir, "Bad Slug", "tool", "X").is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }
}
