//! One signed update transaction per app, shared by every window.
use serde::{Deserialize, Serialize};
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
    time::{Duration, SystemTime, UNIX_EPOCH},
};
use tauri::{AppHandle, Emitter, Manager, State, WebviewWindow};
use tauri_plugin_updater::{Update, UpdaterExt};
use tokio::sync::Notify;

#[derive(Clone, Serialize, Deserialize)]
pub struct Preferences {
    pub automatic: bool,
    pub interval_hours: u64,
}
impl Default for Preferences {
    fn default() -> Self {
        Self {
            automatic: true,
            interval_hours: 24,
        }
    }
}
#[derive(Clone, Serialize)]
pub struct Snapshot {
    pub current_version: String,
    pub supported: bool,
    pub reason: Option<String>,
    pub preferences: Preferences,
    pub phase: String,
    pub version: Option<String>,
    pub notes: Option<String>,
    pub downloaded: u64,
    pub total: Option<u64>,
    pub last_checked: Option<u64>,
    pub error: Option<String>,
}
struct Inner {
    preferences: Preferences,
    phase: String,
    update: Option<Update>,
    bytes: Option<Vec<u8>>,
    downloaded: u64,
    total: Option<u64>,
    last_checked: Option<u64>,
    error: Option<String>,
    cancel: Option<Arc<Notify>>,
    guard: Option<String>,
    reports: HashMap<String, Vec<String>>,
    launches: usize,
}
pub struct Updates(Mutex<Inner>);
impl Default for Updates {
    fn default() -> Self {
        let preferences = preferences_path()
            .ok()
            .and_then(|p| std::fs::read(p).ok())
            .and_then(|b| serde_json::from_slice::<Preferences>(&b).ok())
            .filter(|p| valid_interval(p.interval_hours))
            .unwrap_or_default();
        Self(Mutex::new(Inner {
            preferences,
            phase: "idle".into(),
            update: None,
            bytes: None,
            downloaded: 0,
            total: None,
            last_checked: None,
            error: None,
            cancel: None,
            guard: None,
            reports: HashMap::new(),
            launches: 0,
        }))
    }
}
fn preferences_path() -> Result<std::path::PathBuf, String> {
    Ok(crate::settings::home_dir()?.join(".speccify/update-preferences.json"))
}
fn valid_interval(hours: u64) -> bool {
    matches!(hours, 6 | 24 | 168)
}
fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
fn busy(phase: &str) -> bool {
    matches!(
        phase,
        "checking" | "downloading" | "preparing" | "installing"
    )
}
fn unsupported(app: &AppHandle) -> Option<String> {
    if crate::updater_pubkey(app.config()).is_none() {
        return Some("Dieser Build unterstützt noch keine signierten Updates. Einmalig den aktuellen Installer laden.".into());
    }
    if cfg!(target_os = "linux") && std::env::var_os("APPIMAGE").is_none() {
        return Some("Linux-Updates in der App benötigen ein AppImage. deb/rpm bitte über den Paketmanager aktualisieren.".into());
    }
    None
}
#[tauri::command]
pub fn update_snapshot(app: AppHandle, state: State<Updates>) -> Snapshot {
    let s = state.0.lock().unwrap();
    let reason = unsupported(&app);
    Snapshot {
        current_version: app.package_info().version.to_string(),
        supported: reason.is_none(),
        reason,
        preferences: s.preferences.clone(),
        phase: s.phase.clone(),
        version: s.update.as_ref().map(|u| u.version.clone()),
        notes: s.update.as_ref().and_then(|u| u.body.clone()),
        downloaded: s.downloaded,
        total: s.total,
        last_checked: s.last_checked,
        error: s.error.clone(),
    }
}
#[tauri::command]
pub fn update_preferences(state: State<Updates>, preferences: Preferences) -> Result<(), String> {
    if !valid_interval(preferences.interval_hours) {
        return Err("Ungültiges Suchintervall.".into());
    }
    let mut s = state.0.lock().unwrap();
    let path = preferences_path()?;
    std::fs::create_dir_all(path.parent().unwrap()).map_err(|e| e.to_string())?;
    let mut file =
        tempfile::NamedTempFile::new_in(path.parent().unwrap()).map_err(|e| e.to_string())?;
    serde_json::to_writer_pretty(&mut file, &preferences).map_err(|e| e.to_string())?;
    file.persist(path).map_err(|e| e.to_string())?;
    s.preferences = preferences;
    Ok(())
}
#[tauri::command]
pub async fn update_check(app: AppHandle, state: State<'_, Updates>) -> Result<(), String> {
    if let Some(reason) = unsupported(&app) {
        return Err(reason);
    }
    {
        let mut s = state.0.lock().unwrap();
        if busy(&s.phase) || s.bytes.is_some() {
            return Ok(());
        }
        s.phase = "checking".into();
        s.error = None;
        s.last_checked = Some(now());
    }
    let result = match app
        .updater_builder()
        .timeout(Duration::from_secs(20))
        .build()
    {
        Ok(updater) => updater.check().await.map_err(|e| e.to_string()),
        Err(e) => Err(e.to_string()),
    };
    let mut s = state.0.lock().unwrap();
    match result {
        Ok(update) => {
            s.phase = if update.is_some() {
                "available"
            } else {
                "current"
            }
            .into();
            s.update = update;
        }
        Err(error) => {
            s.phase = "error".into();
            s.error = Some(error);
        }
    }
    Ok(())
}
#[tauri::command]
pub async fn update_download(state: State<'_, Updates>) -> Result<(), String> {
    let (mut update, cancel) = {
        let mut s = state.0.lock().unwrap();
        if busy(&s.phase) {
            return Err("Update-Vorgang läuft bereits.".into());
        }
        let update = s.update.clone().ok_or("Zuerst nach Updates suchen.")?;
        if s.bytes.is_some() {
            return Ok(());
        }
        let cancel = Arc::new(Notify::new());
        s.cancel = Some(cancel.clone());
        s.phase = "downloading".into();
        s.error = None;
        s.downloaded = 0;
        s.total = None;
        (update, cancel)
    };
    update.timeout = Some(Duration::from_secs(600));
    let result = tokio::select! {
        result = update.download(|chunk, total| {
            let mut s = state.0.lock().unwrap(); s.downloaded += chunk as u64; s.total = total;
        }, || {}) => Some(result),
        _ = cancel.notified() => None,
    };
    let mut s = state.0.lock().unwrap();
    s.cancel = None;
    match result {
        Some(Ok(bytes)) => {
            s.bytes = Some(bytes);
            s.phase = "ready".into();
        }
        Some(Err(e)) => {
            s.phase = "error".into();
            s.error = Some(e.to_string());
        }
        None => {
            s.phase = "available".into();
            s.downloaded = 0;
            s.total = None;
        }
    }
    Ok(())
}
#[tauri::command]
pub fn update_cancel(state: State<Updates>) {
    if let Some(cancel) = &state.0.lock().unwrap().cancel {
        cancel.notify_one();
    }
}
#[tauri::command]
pub fn update_guard_reply(
    window: WebviewWindow,
    state: State<Updates>,
    token: String,
    blockers: Vec<String>,
) {
    let mut s = state.0.lock().unwrap();
    if s.guard.as_ref() == Some(&token) {
        s.reports.insert(window.label().into(), blockers);
    }
}
pub struct WorkPermit(AppHandle);
impl Drop for WorkPermit {
    fn drop(&mut self) {
        self.0.state::<Updates>().0.lock().unwrap().launches -= 1;
    }
}
pub fn begin_work(app: &AppHandle) -> Result<WorkPermit, String> {
    let state = app.state::<Updates>();
    let mut s = state.0.lock().unwrap();
    if matches!(s.phase.as_str(), "preparing" | "installing") {
        return Err("Update-Installation wird vorbereitet.".into());
    }
    s.launches += 1;
    Ok(WorkPermit(app.clone()))
}
fn guard_result(
    labels: &[String],
    current: &[String],
    reports: &HashMap<String, Vec<String>>,
) -> Result<(), String> {
    if labels != current {
        return Err("Fenster haben sich geändert. Bitte erneut versuchen.".into());
    }
    let blockers: Vec<String> = labels
        .iter()
        .flat_map(|label| match reports.get(label) {
            Some(items) => items
                .iter()
                .map(|item| format!("{label}: {item}"))
                .collect(),
            None => vec![format!("{label}: Fenster antwortet nicht")],
        })
        .collect();
    if blockers.is_empty() {
        Ok(())
    } else {
        Err(blockers.join("\n"))
    }
}
fn labels(app: &AppHandle) -> Vec<String> {
    let mut v: Vec<_> = app.webview_windows().into_keys().collect();
    v.sort();
    v
}
#[tauri::command]
pub async fn update_install(app: AppHandle, state: State<'_, Updates>) -> Result<(), String> {
    let token = uuid::Uuid::new_v4().to_string();
    {
        let mut s = state.0.lock().unwrap();
        if s.phase != "ready" || s.bytes.is_none() {
            return Err("Noch kein geprüftes Update bereit.".into());
        }
        s.phase = "preparing".into();
        s.guard = Some(token.clone());
        s.reports.clear();
        s.error = None;
    }
    let expected = labels(&app);
    let result: Result<(), String> = async {
        app.emit("update-guard", &token)
            .map_err(|e| e.to_string())?;
        for _ in 0..40 {
            if expected
                .iter()
                .all(|label| state.0.lock().unwrap().reports.contains_key(label))
            {
                break;
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
        guard_result(&expected, &labels(&app), &state.0.lock().unwrap().reports)?;
        if state.0.lock().unwrap().launches > 0 {
            return Err("Ein Auftrag wird gerade gestartet. Bitte erneut versuchen.".into());
        }
        if app.state::<crate::terminal::Terminals>().has_active_work()
            || app
                .state::<crate::actions_cmd::ActionRuns>()
                .has_active_work()
            || app
                .state::<crate::Supervisor>()
                .0
                .lock()
                .unwrap()
                .values_mut()
                .any(|child| child.try_wait().ok().flatten().is_none())
        {
            return Err("Terminals oder Aktionen laufen noch. Bitte zuerst beenden.".into());
        }
        let (update, bytes) = {
            let mut s = state.0.lock().unwrap();
            s.phase = "installing".into();
            (s.update.clone().unwrap(), s.bytes.take().unwrap())
        };
        // Installation is blocking and Windows may exit the process here.
        tauri::async_runtime::spawn_blocking(move || update.install(bytes))
            .await
            .map_err(|e| e.to_string())?
            .map_err(|e| e.to_string())?;
        app.restart();
    }
    .await;
    if let Err(error) = &result {
        let mut s = state.0.lock().unwrap();
        s.phase = if s.bytes.is_some() { "ready" } else { "error" }.into();
        s.error = Some(error.clone());
        s.guard = None;
    }
    let _ = app.emit("update-guard-release", &token);
    result
}
pub fn start(app: AppHandle) {
    std::thread::spawn(move || loop {
        std::thread::sleep(Duration::from_secs(10));
        if unsupported(&app).is_some() {
            continue;
        }
        let state = app.state::<Updates>();
        let due = {
            let s = state.0.lock().unwrap();
            s.preferences.automatic
                && !busy(&s.phase)
                && s.bytes.is_none()
                && s.last_checked.is_none_or(|last| {
                    now().saturating_sub(last) >= s.preferences.interval_hours * 3600
                })
        };
        if due {
            let handle = app.clone();
            tauri::async_runtime::spawn(async move {
                let _ = update_check(handle.clone(), handle.state::<Updates>()).await;
            });
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicBool, Ordering};
    use tauri::test::{mock_builder, mock_context, noop_assets};

    #[test]
    fn real_updater_checks_versions_and_rejects_tampered_downloads() {
        let server = Arc::new(tiny_http::Server::http("127.0.0.1:0").unwrap());
        let url = format!("http://{}", server.server_addr());
        let scenario = Arc::new(Mutex::new(("999.0.0".to_string(), false)));
        let stop = Arc::new(AtomicBool::new(false));
        let worker = {
            let (server, scenario, stop, url) =
                (server.clone(), scenario.clone(), stop.clone(), url.clone());
            std::thread::spawn(move || {
                while !stop.load(Ordering::SeqCst) {
                    let Some(request) = server.recv_timeout(Duration::from_millis(100)).unwrap()
                    else {
                        continue;
                    };
                    let (version, tampered) = scenario.lock().unwrap().clone();
                    let body = if request.url() == "/payload" {
                        if tampered {
                            b"tampered".to_vec()
                        } else {
                            include_bytes!("../tests/fixtures/updater/payload.txt").to_vec()
                        }
                    } else {
                        serde_json::to_vec(&serde_json::json!({"version": version, "platforms": {"fixture": {
                        "url": format!("{url}/payload"),
                        "signature": include_str!("../tests/fixtures/updater/payload.txt.sig").trim()
                    }}})).unwrap()
                    };
                    request
                        .respond(tiny_http::Response::from_data(body))
                        .unwrap();
                }
            })
        };
        let mut context = mock_context(noop_assets());
        context.config_mut().plugins.0.insert(
            "updater".into(),
            serde_json::json!({
                "dangerousInsecureTransportProtocol": true,
                "pubkey": include_str!("../tests/fixtures/updater/public.key").trim(),
                "endpoints": [format!("{url}/latest.json")]
            }),
        );
        let app = mock_builder()
            .plugin(tauri_plugin_updater::Builder::new().build())
            .build(context)
            .unwrap();
        let updater = app
            .updater_builder()
            .target("fixture")
            .timeout(Duration::from_secs(2))
            .build()
            .unwrap();
        tauri::async_runtime::block_on(async {
            let update = updater.check().await.unwrap().unwrap();
            let bytes = update.download(|_, _| {}, || {}).await.unwrap();
            assert_eq!(
                bytes,
                include_bytes!("../tests/fixtures/updater/payload.txt")
            );
            scenario.lock().unwrap().1 = true;
            assert!(update.download(|_, _| {}, || {}).await.is_err());
            scenario.lock().unwrap().0 = app.package_info().version.to_string();
            assert!(updater.check().await.unwrap().is_none());
            scenario.lock().unwrap().0 = "0.0.0".into();
            assert!(updater.check().await.unwrap().is_none());
        });
        stop.store(true, Ordering::SeqCst);
        worker.join().unwrap();
        drop(server);
        assert!(tauri::async_runtime::block_on(updater.check()).is_err());
    }
    #[test]
    fn every_window_must_reply_and_new_windows_block_installation() {
        let windows = vec!["main".into(), "project-a".into()];
        let mut reports = HashMap::from([("main".into(), vec![])]);
        assert!(guard_result(&windows, &windows, &reports)
            .unwrap_err()
            .contains("antwortet nicht"));
        reports.insert("project-a".into(), vec!["Editor offen".into()]);
        assert!(guard_result(&windows, &windows, &reports)
            .unwrap_err()
            .contains("Editor offen"));
        reports.insert("project-a".into(), vec![]);
        assert!(guard_result(&windows, &windows, &reports).is_ok());
        assert!(guard_result(&windows, &["main".into()], &reports).is_err());
        assert!(!valid_interval(0));
        assert!(valid_interval(24));
    }
}
