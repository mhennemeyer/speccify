//! Discovery-MCP-Skelett (Stufe R0). Tools `actions_list`/`actions_propose`/
//! `mcp_list` kommen in Stufe R2; Actions-Datenmodell:
//! `schema/actions.schema.json`.

fn main() {
    eprintln!(
        "speccify-discovery-mcp {}: noch nicht implementiert (Stufe R2, \
         siehe .agent/plans/rust-neustart-toolkit-mcps.md).",
        env!("CARGO_PKG_VERSION")
    );
    std::process::exit(2);
}

#[cfg(test)]
mod tests {
    /// R0-Platzhalter: hält `cargo test` lauffähig, bis R2 echte Tests bringt.
    #[test]
    fn workspace_builds() {
        assert_eq!(env!("CARGO_PKG_NAME"), "speccify-discovery-mcp");
    }
}
