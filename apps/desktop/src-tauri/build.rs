fn main() {
    tauri_build::build();

    // Windows: Test-Binaries brauchen dasselbe Common-Controls-v6-Manifest wie
    // die App (TaskDialogIndirect gibt es nur in comctl32 v6) — sonst startet
    // der Loader sie gar nicht erst (STATUS_ENTRYPOINT_NOT_FOUND). tauri-build
    // versorgt nur die bin-Targets, also hier für die Tests nachlegen.
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows")
        && std::env::var("CARGO_CFG_TARGET_ENV").as_deref() == Ok("msvc")
    {
        let manifest =
            std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("windows-test-manifest.xml");
        println!("cargo:rustc-link-arg-tests=/MANIFEST:EMBED");
        println!(
            "cargo:rustc-link-arg-tests=/MANIFESTINPUT:{}",
            manifest.display()
        );
        println!("cargo:rerun-if-changed=windows-test-manifest.xml");
    }
}
