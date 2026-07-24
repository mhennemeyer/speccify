//! Exec-MCP-Skelett (Stufe R0). Die Implementierung mit Stream-Parität zur
//! Python-Referenz (dotagent `2949d1d`) ist Stufe R1 — Wire-Kontrakt und
//! Portierungs-Checkliste: `docs/exec-mcp-contract.md`.

fn main() {
    eprintln!(
        "speccify-exec-mcp {}: noch nicht implementiert (Stufe R1, \
         siehe .agent/plans/rust-neustart-toolkit-mcps.md).",
        env!("CARGO_PKG_VERSION")
    );
    std::process::exit(2);
}

#[cfg(test)]
mod tests {
    /// R0-Platzhalter: hält `cargo test` lauffähig, bis R1 die
    /// Kontrakt-Tests bringt.
    #[test]
    fn workspace_builds() {
        assert_eq!(env!("CARGO_PKG_NAME"), "speccify-exec-mcp");
    }
}
