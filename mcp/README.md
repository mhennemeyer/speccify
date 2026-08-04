# speccify-mcp

MCP-Server, der Coding-Agents (Claude Code, Junie, Cursor, Aider) den
gleichen Workflow wie die `speccify`-CLI über das
[Model Context Protocol](https://modelcontextprotocol.io) gibt —
ohne dass die Agenten Spec- oder Lockfile-Wissen mitbringen müssen.

Der Server ist ein **dünner Adapter über `speccify-core`**: jeder
MCP-Tool-Aufruf entspricht 1:1 einem `speccify <subcommand>` und
liefert dieselben byte-identischen Outputs (vgl. Cross-Consistency-
Test in `mcp/tests/test_tools_write.py`).

**Aktive Phase**: Phase 1c — siehe [Phasen-Plan](../.agent/plans/archive/phase-1c-mcp-server.md).

## Installation & Start

```bash
uv sync --all-packages         # installiert auch `speccify-mcp`
speccify-mcp --project .       # startet stdio-Server gegen CWD
# oder:
SPECCIFY_PROJECT_ROOT=. speccify-mcp
```

- Transport: ausschließlich `stdio` (Phase 1c).
- Logs gehen nach `stderr`. Log-Level via `--log-level` oder
  `SPECCIFY_LOG_LEVEL` (Default `INFO`).
- Offline-Default: solange `--offline` aktiv ist (Default für die
  `pull`/`render`/`verify`-Tools) wird ausschließlich gegen den
  Replay-Cache gelesen; ohne Cache-Hit gibt es einen strukturierten
  Fehler statt eines Netz-Calls.
- Cache-Pfad via `SPECCIFY_CACHE_DIR` (Default: eingecheckter
  Repo-Cache `tests/fixtures/llm-cache/`).

## Tools

Alle Tools sind reine Adapter über `speccify-core`. Inputs werden via
pydantic validiert, Outputs als `structuredContent` zurückgegeben.

| Tool      | CLI-Pendant         | Effekt            | Wichtige Inputs                                                  |
|-----------|---------------------|-------------------|------------------------------------------------------------------|
| `lint`    | `speccify lint`     | read-only         | `spec_path`                                                      |
| `resolve` | (Lockfile-Plan)     | read-only         | `manifest_path?`                                                 |
| `render`  | (Render in-memory)  | read-only         | `spec_id`, `target`, `offline?`, `cache_dir?`                    |
| `lock`    | `speccify lock`     | schreibt Lockfile | `manifest_path?`                                                 |
| `pull`    | `speccify pull`     | schreibt Outputs  | `manifest_path?`, `out_dir`, `offline?`, `cache_dir?`            |
| `verify`  | `speccify verify`   | read-only Drift   | `manifest_path?`, `out_dir`, `offline?`, `cache_dir?`            |

`verify` liefert immer `{"ok": bool, "problems": [...]}` als
strukturiertes Ergebnis — Drift ist **kein** MCP-Error, sondern eine
Antwort, die ein Agent auswerten kann.

## Resources

| URI                                  | Inhalt                                                                |
|--------------------------------------|-----------------------------------------------------------------------|
| `speccify://manifest`                | `speccify.yaml` des aktiven Projekts (YAML, UTF-8).                   |
| `speccify://lockfile`                | `speccify.lock` des aktiven Projekts; Hint-Kommentar, wenn nicht da.  |
| `spec://{scope}/{name}@{version}`    | YAML-Bytes einer Spec aus der Registry des aktiven Manifests.         |

## Prompts

| Name       | Argumente                                                     | Zweck                                                             |
|------------|---------------------------------------------------------------|-------------------------------------------------------------------|
| `add-spec` | `spec_ref` (required), `out_dir` (default `./src/components`) | Anleitung an den Agenten: `resolve` → `lock` → `pull` → `verify`. |

## Client-Konfiguration

### Claude Code / Junie / Cursor

```json
{
  "mcpServers": {
    "speccify": {
      "command": "speccify-mcp",
      "args": ["--project", "."]
    }
  }
}
```

Wenn `speccify-mcp` nicht im `PATH` liegt (z. B. lokales `uv`-Venv),
hilft ein expliziter Aufruf:

```json
{
  "mcpServers": {
    "speccify": {
      "command": "uv",
      "args": ["run", "speccify-mcp", "--project", "."]
    }
  }
}
```

## Smoke-Test (lokal & CI)

```bash
uv run python scripts/mcp_smoke.py
```

Startet `speccify-mcp` per `stdio`, fährt einen MCP-Handshake mit dem
offiziellen Python-Client und prüft `tools/list`, `tools/call render`
(offline) und `resources/read speccify://manifest`. Exit-Code `0` =
grün. Der gleiche Aufruf läuft als CI-Step `speccify-mcp smoke (stdio,
offline)`.
