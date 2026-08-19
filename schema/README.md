# schema/

JSON-Schemas, die **nicht** zum Python-Paket gehören.

- `actions.schema.json` — Aktionsliste des Rust-Workstreams (Exec-/Discovery-MCP);
  wire-kompatibel zu iKanbanAi (`.agent/actions.json` pro Projekt,
  `~/.speccify/actions.json` global).

Die von `speccify-core` geladenen Schemas (Manifest, Lockfile, Index-Eintrag)
liegen als Paket-Daten unter `core/src/speccify_core/schemas/` — sie müssen mit
dem Wheel ausgeliefert werden, sonst funktioniert die installierte CLI nicht.
