fn main() {
    tauri_build::build();

    // Windows: Tauri importiert TaskDialogIndirect, das nur comctl32 **v6**
    // exportiert — v6 lädt der Loader aber nur mit Common-Controls-Manifest.
    // Die App-Exe bekommt ihres von tauri-build (rustc-link-arg-bins); die
    // cargo-test-Exen nicht, und der Loader verweigert ihnen den Start
    // (STATUS_ENTRYPOINT_NOT_FOUND), bevor ein einziger Test läuft. Delay-Load
    // verschiebt die Auflösung auf den ersten Aufruf: Tests zeigen nie Dialoge,
    // die App löst mit ihrem Manifest wie bisher v6 auf.
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows")
        && std::env::var("CARGO_CFG_TARGET_ENV").as_deref() == Ok("msvc")
    {
        println!("cargo:rustc-link-arg=/DELAYLOAD:comctl32.dll");
        println!("cargo:rustc-link-lib=delayimp");
    }
}
