//! Python-Engine der verteilten App (Plan r5-distribution.md, R5.2/D2).
//!
//! Die App bringt die Spec-Engine als **Payload** mit (`resources/engine`:
//! eigene Wheels + gepinnte `requirements.txt` aus `uv.lock`) und baut daraus
//! beim ersten Start eine venv unter
//! `~/Library/Application Support/io.speccify.desktop/engine/venv`. Damit
//! braucht die verteilte App weder Repo noch `uv sync` — nur einmal Netz
//! (uv lädt CPython und die Third-Party-Wheels).
//!
//! Ein Marker (`installed.json`) hält den Payload-Hash fest: nach einem
//! App-Update mit neuem Payload wird neu installiert.
//!
//! Repo-Modus bleibt Vorrang (D3): wer im Composer ein Repo mit `.venv`
//! angibt, arbeitet weiter gegen den Quellstand.

use std::{
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
    process::{Command, Stdio},
};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager};

use crate::sidecar::{self, BinarySource};

/// Supervisor-/Log-Id der Engine-Installation (die UI hört auf `proc-log`).
pub const LOG_ID: &str = "engine-install";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Payload {
    pub hash: String,
    pub python: String,
    #[serde(default)]
    pub wheels: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct InstalledMarker {
    hash: String,
    python: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct EngineStatus {
    /// venv vorhanden und zum mitgelieferten Payload passend.
    pub ready: bool,
    /// venv vorhanden, aber aus einem älteren Payload (App-Update).
    pub needs_update: bool,
    /// Payload im App-Bundle gefunden?
    pub payload_found: bool,
    pub payload_hash: Option<String>,
    pub installed_hash: Option<String>,
    pub python_version: Option<String>,
    pub venv_dir: String,
    /// Woher `uv` kommt — ohne uv ist keine Installation möglich.
    pub uv_source: BinarySource,
}

// --- Pfade ---------------------------------------------------------------------

/// Resource-Verzeichnis mit dem Payload. Gebündelt liegt es unter
/// `Contents/Resources/…`; im `tauri dev`-Betrieb greifen wir auf das
/// Crate-Verzeichnis zurück, damit der Flow ohne Bundle testbar bleibt.
pub fn resources_dir(app: &AppHandle) -> Option<PathBuf> {
    app.path()
        .resource_dir()
        .ok()
        .and_then(|dir| payload_root(&dir))
        .or_else(|| payload_root(&PathBuf::from(env!("CARGO_MANIFEST_DIR"))))
}

/// Wo unter `dir` liegt der Payload? Tauri legt den Glob `resources/**/*`
/// unter `Contents/Resources/resources/` ab; die Variante ohne
/// Zwischenverzeichnis deckt eine flache Ablage ab, `dir` selbst den
/// `tauri dev`-Fall (Crate-Verzeichnis).
fn payload_root(dir: &Path) -> Option<PathBuf> {
    let marker = Path::new("engine").join("payload.json");
    [dir.join("resources"), dir.to_path_buf()]
        .into_iter()
        .find(|candidate| candidate.join(&marker).is_file())
}

/// `~/Library/Application Support/io.speccify.desktop/engine`
fn engine_dir(app: &AppHandle) -> Result<PathBuf, String> {
    app.path()
        .app_data_dir()
        .map(|dir| dir.join("engine"))
        .map_err(|e| format!("App-Data-Verzeichnis: {e}"))
}

pub fn venv_dir(app: &AppHandle) -> Result<PathBuf, String> {
    engine_dir(app).map(|dir| dir.join("venv"))
}

fn marker_path(app: &AppHandle) -> Result<PathBuf, String> {
    engine_dir(app).map(|dir| dir.join("installed.json"))
}

/// Ausführbares aus der Engine-venv (z. B. `speccify-web-backend`).
pub fn venv_bin(app: &AppHandle, name: &str) -> Result<PathBuf, String> {
    Ok(venv_dir(app)?.join("bin").join(name))
}

fn read_payload(resources: &Path) -> Result<Payload, String> {
    let path = resources.join("engine").join("payload.json");
    let text = std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
    serde_json::from_str(&text).map_err(|e| format!("{}: {e}", path.display()))
}

fn read_marker(app: &AppHandle) -> Option<InstalledMarker> {
    let path = marker_path(app).ok()?;
    let text = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&text).ok()
}

// --- Status --------------------------------------------------------------------

#[tauri::command]
pub fn engine_status(app: AppHandle) -> Result<EngineStatus, String> {
    let venv = venv_dir(&app)?;
    let payload = resources_dir(&app).and_then(|res| read_payload(&res).ok());
    let marker = read_marker(&app);
    let installed = venv.join("bin").join("python3").exists();

    let payload_hash = payload.as_ref().map(|p| p.hash.clone());
    let installed_hash = marker.as_ref().map(|m| m.hash.clone());
    let matches = match (&payload_hash, &installed_hash) {
        (Some(p), Some(i)) => p == i,
        _ => false,
    };

    Ok(EngineStatus {
        ready: installed && matches,
        needs_update: installed && !matches,
        payload_found: payload.is_some(),
        payload_hash,
        installed_hash,
        python_version: payload.map(|p| p.python),
        venv_dir: venv.display().to_string(),
        uv_source: sidecar::resolve("uv").1,
    })
}

// --- Installation --------------------------------------------------------------

fn emit(app: &AppHandle, line: impl Into<String>) {
    let _ = app.emit(
        "proc-log",
        crate::LogEvent {
            id: LOG_ID.to_string(),
            line: line.into(),
        },
    );
}

/// Kommando ausführen und Ausgabe zeilenweise als `proc-log` streamen.
fn run_streamed(app: &AppHandle, program: &Path, args: &[&str]) -> Result<(), String> {
    emit(app, format!("$ {} {}", program.display(), args.join(" ")));
    let mut child = Command::new(program)
        .args(args)
        .env("PATH", crate::augmented_path())
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("{}: {e}", program.display()))?;

    // stderr im Thread (uv schreibt seinen Fortschritt dorthin), stdout hier.
    let stderr_app = app.clone();
    let stderr = child.stderr.take();
    let pump = std::thread::spawn(move || {
        if let Some(stderr) = stderr {
            for line in BufReader::new(stderr).lines().map_while(Result::ok) {
                emit(&stderr_app, line);
            }
        }
    });
    if let Some(stdout) = child.stdout.take() {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            emit(app, line);
        }
    }
    let status = child.wait().map_err(|e| e.to_string())?;
    let _ = pump.join();

    if status.success() {
        Ok(())
    } else {
        Err(format!(
            "{} endete mit {} — Log im Umgebungs-Tab prüfen.",
            program.display(),
            status
                .code()
                .map(|c| c.to_string())
                .unwrap_or_else(|| "Signal".into())
        ))
    }
}

/// Baut die Engine-venv aus dem mitgelieferten Payload. Blockiert bis fertig
/// (die UI zeigt derweil den Live-Log) und ist idempotent — ein erneuter Lauf
/// installiert einfach neu.
#[tauri::command]
pub fn engine_install(app: AppHandle) -> Result<EngineStatus, String> {
    let resources = resources_dir(&app)
        .ok_or("Kein Engine-Payload im App-Bundle — `./scripts/build_engine_payload.sh` vor dem Build ausführen.")?;
    let payload = read_payload(&resources)?;
    let uv = sidecar::resolve("uv")
        .0
        .ok_or("`uv` nicht gefunden — im Umgebungs-Tab installieren (brew install uv).")?;

    let venv = venv_dir(&app)?;
    if let Some(parent) = venv.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    // Marker zuerst weg: bricht die Installation ab, gilt die venv als unfertig.
    let _ = std::fs::remove_file(marker_path(&app)?);

    emit(&app, format!("Engine-Payload {}…", &payload.hash[..12]));
    let venv_str = venv.display().to_string();
    run_streamed(&app, &uv, &["venv", "--python", &payload.python, &venv_str])?;

    let python = venv.join("bin").join("python3").display().to_string();
    let requirements = resources
        .join("engine")
        .join("requirements.txt")
        .display()
        .to_string();
    run_streamed(
        &app,
        &uv,
        &["pip", "install", "--python", &python, "-r", &requirements],
    )?;

    // Eigene Wheels ohne Deps — die stecken schon in requirements.txt.
    let wheels_dir = resources.join("engine").join("wheels");
    let wheels: Vec<String> = payload
        .wheels
        .iter()
        .map(|name| wheels_dir.join(name).display().to_string())
        .collect();
    if wheels.is_empty() {
        return Err("Payload enthält keine Wheels.".into());
    }
    let mut args: Vec<&str> = vec!["pip", "install", "--python", &python, "--no-deps"];
    args.extend(wheels.iter().map(String::as_str));
    run_streamed(&app, &uv, &args)?;

    let marker = InstalledMarker {
        hash: payload.hash.clone(),
        python: payload.python.clone(),
    };
    std::fs::write(
        marker_path(&app)?,
        serde_json::to_string_pretty(&marker).map_err(|e| e.to_string())? + "\n",
    )
    .map_err(|e| e.to_string())?;

    emit(&app, "Engine installiert.");
    engine_status(app)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Bundle-Layout: `Contents/Resources/resources/engine/payload.json`
    /// (Tauri-Glob) muss gefunden werden, eine leere Resource-Ablage nicht.
    #[test]
    fn payload_root_finds_the_bundle_layout() {
        let root = std::env::temp_dir().join(format!("speccify-res-{}", std::process::id()));
        let nested = root.join("resources").join("engine");
        std::fs::create_dir_all(&nested).unwrap();
        assert_eq!(payload_root(&root), None, "ohne payload.json kein Treffer");

        std::fs::write(nested.join("payload.json"), b"{}").unwrap();
        assert_eq!(payload_root(&root), Some(root.join("resources")));

        // Flache Ablage direkt im Resource-Verzeichnis.
        let flat = root.join("flat");
        std::fs::create_dir_all(flat.join("engine")).unwrap();
        std::fs::write(flat.join("engine").join("payload.json"), b"{}").unwrap();
        assert_eq!(payload_root(&flat), Some(flat.clone()));

        std::fs::remove_dir_all(&root).ok();
    }

    /// Der ausgelieferte Payload muss im Repo liegen und zu den Wheels passen —
    /// sonst baut `tauri build` eine App ohne funktionierende Engine.
    #[test]
    fn repo_payload_is_consistent() {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("resources");
        if !dir.join("engine").join("payload.json").is_file() {
            // Payload wird von scripts/build_engine_payload.sh erzeugt und ist
            // gitignored — im frischen Checkout ist der Test gegenstandslos.
            return;
        }
        let payload = read_payload(&dir).expect("payload.json lesbar");
        assert_eq!(payload.hash.len(), 64, "sha256-Hex erwartet");
        assert!(
            payload.python.starts_with("3."),
            "Python-Version im Payload"
        );
        assert!(
            payload
                .wheels
                .iter()
                .any(|w| w.starts_with("speccify_web_backend")),
            "web-backend-Wheel fehlt: {:?}",
            payload.wheels
        );
        for wheel in &payload.wheels {
            assert!(
                dir.join("engine").join("wheels").join(wheel).is_file(),
                "Wheel aus payload.json fehlt: {wheel}"
            );
        }
        assert!(dir.join("composer").join("index.html").is_file());
        assert!(dir.join("skills").is_dir());
    }
}
