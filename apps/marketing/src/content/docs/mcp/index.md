---
title: MCP Reference
description: Speccify als MCP-Server — jede CLI-Fähigkeit auch für Coding-Agents.
---

Speccify bringt einen MCP-Server (stdio) mit. Jedes Tool ist ein dünner
Adapter über `speccify-core` und entspricht 1:1 einem CLI-Subcommand; beide
Wege liefern **byte-identische** Dateien.

```bash
uv run speccify-mcp --project /pfad/zum/projekt
```

## Tools

| Tool | CLI-Pendant | Effekt | Wichtige Inputs |
|---|---|---|---|
| `lint` | `speccify lint` | read-only | `spec_path` |
| `resolve` | (Lockfile-Plan) | read-only | `manifest_path?` |
| `render` | (Render in-memory) | read-only | `spec_id`, `target`, `offline?` |
| `lock` | `speccify lock` | schreibt Lockfile | `manifest_path?` |
| `pull` | `speccify pull` | schreibt Outputs | `out_dir`, `offline?`, `cache_dir?` |
| `verify` | `speccify verify` | read-only Drift | `out_dir`, `offline?` |
| `mock` | `speccify mock` | schreibt Mocks | `spec_ref`, `out_dir`, `target?` |
| `build` | `speccify build` | schreibt Projekt | `spec_ref`, `out_dir`, `mocks?` |
| `search` | `speccify search` | read-only | `query`, `index_sources?`, `offline?` |

Fehler sind **strukturierte Antworten**, keine MCP-Errors: `verify` liefert
`{ok, problems[]}`, `build` meldet `code=build_failed`/`cache_miss`,
`search` meldet `code=no_index_configured`. Ein Agent kann darauf reagieren,
statt an einer Exception abzubrechen.

## Resources & Prompt

| URI | Inhalt |
|---|---|
| `speccify://manifest` | `speccify.yaml` des aktiven Projekts |
| `speccify://lockfile` | `speccify.lock` (mit Hinweis, wenn es fehlt) |
| `spec://{scope}/{name}@{version}` | YAML-Bytes einer Spec |

Prompt `add-spec(spec_ref, out_dir)` führt durch resolve → lock → pull → verify.

## Client-Konfiguration

```json
{
  "mcpServers": {
    "speccify": {
      "command": "uv",
      "args": ["run", "speccify-mcp", "--project", "/pfad/zum/projekt"]
    }
  }
}
```

Auch der [Composer](/composer/) ist agent-bedienbar: jede UI-Aktion existiert
als HTTP-Endpoint, der Zustand ist die Spec-Datei auf Disk.
