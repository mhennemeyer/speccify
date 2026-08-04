# schema/

JSON-Schema-Definitionen für `speccify.yaml`-Specs. Sprach-unabhängig (kein Python-Paket).

**Aktive Phase**: Phase 3 — Multi-Target-Schema-Vorgriff. Siehe [Master-Plan, Zeilen 123–174 + 276–281](../.agent/plans/archive/speccify-plan.md) und den [Phase-0-Spike-Plan](../.agent/plans/archive/phase-0-spec-schema-spike.md).

**Schema-Inventur**:
- `spec.schema.json` — aktive Spec-Definition (Phase 0).
- `manifest.schema.json` — aktiv geladene Manifest-Definition (derzeit v1).
- `manifest.v1.schema.json` — Snapshot v1 (= aktuell aktiv).
- `manifest.v2.schema.json` — Phase-3-Stage-1b-Vorgriff (Multi-Target, `targets: list[str]`); noch nicht aktiv.
- `lockfile.schema.json` — aktiv geladene Lockfile-Definition (derzeit v2).
- `lockfile.v1.schema.json` — Phase-1a-Snapshot.
- `lockfile.v2.schema.json` — Snapshot v2 (= aktuell aktiv, Phase-2-Bump mit `signature` + `yank_status`).
- `lockfile.v3.schema.json` — Phase-3-Stage-1b-Vorgriff (Multi-Target, Top-Level `targets: list[str]`); noch nicht aktiv.
- `actions.schema.json` — Aktionsliste des Rust-Neustart-Workstreams (R0): benannte CLI-Befehle für Exec-/Discovery-MCP; wire-kompatibel zu iKanbanAi (`.agent/actions.json` pro Projekt, `~/.speccify/actions.json` global).
