# speccify-mcp

An MCP server that gives coding agents (Claude Code, Cursor, Aider, Junie) the
playbooks in a project over the
[Model Context Protocol](https://modelcontextprotocol.io) — the knowledge an
agent would otherwise have to research every time.

Every tool is a **thin adapter over `speccify-core`**, the same code the CLI
runs, so an agent and a human never get different answers.

## Install and run

```bash
uv sync --all-packages         # installs `speccify-mcp` too
speccify-mcp --project .       # stdio server against the CWD
# or:
SPECCIFY_PROJECT_ROOT=. speccify-mcp
```

- Transport: `stdio` only.
- Logs go to `stderr`; level via `--log-level` or `SPECCIFY_LOG_LEVEL`
  (default `INFO`).
- `--offline` (the default for `pull` and `verify`) reads only the local
  bare-clone cache. Without a cache hit you get a structured error rather than
  a silent network call.

## Tools

### Reading playbooks

`reference` is a playbook id (`@scope/name`) or a git source
(`git+<url>[#<path>]`). All of these also take `offline` and `library_path`.

| Tool | What it does | Key inputs |
|---|---|---|
| `playbook_list` | everything in the library: id, title, summary, step count | `library_path?` |
| `playbook_get` | one playbook: steps, sources, prerequisites, pitfalls | `reference` |
| `playbook_step` | one step, with its sources resolved and its `verify` line | `reference`, `step_id` |
| `playbook_asset` | a file shipped with the playbook (text as-is, binary base64) | `reference`, `path` |
| `playbook_check` | structure plus source age; `links=true` also checks URLs | `reference`, `links?` |

The order `playbook_list` → `playbook_get` → `playbook_step` → `playbook_asset`
is pinned by a test: an agent that has to guess it is an agent that gets it
wrong halfway through a release.

### Finding and pinning

| Tool | CLI equivalent | Effect |
|---|---|---|
| `search` | `speccify search` | read-only, across discovery indexes |
| `lock` | `speccify lock` | writes `speccify.lock` |
| `pull` | `speccify pull` | fetches bundles into the local library |
| `verify` | `speccify verify` | read-only; re-fetches and compares hashes |

### Working next to the viewer

| Tool | What it does |
|---|---|
| `viewer_selection` | what the user selected in the viewer, already resolved |
| `playbook_propose` | propose a changed playbook; the user sees a diff |

`viewer_selection` returns the step itself — detail, verify line, resolved
sources — so "why is this necessary?" needs no follow-up calls. It talks HTTP
to the backend (`SPECCIFY_API`, default `http://127.0.0.1:8000`); if that is
not running, the answer is `code=backend_unreachable` with the command to start
it, not a crash.

`playbook_propose` takes the **complete** new `playbook.yaml`. It is validated
immediately, so an invalid proposal never becomes a diff the user cannot apply,
and nothing is written until a human clicks Apply. Playbooks from git sources
are refused — changes belong in the source repository, as a commit and a tag.

## Errors are answers

Failures come back as structured results, not MCP errors: `verify` returns
`{ok, problems[]}`, `search` reports `code=no_index_configured`,
`playbook_get` reports `code=not_found`. An agent can react to those.

## Resources

| URI | Content |
|---|---|
| `speccify://manifest` | the project's `speccify.yaml` |
| `speccify://lockfile` | the project's `speccify.lock` |

Both return a hint about what to run when the file does not exist yet.

## Client configuration

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

If `speccify-mcp` is not on `PATH` (a local `uv` venv, for example):

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

## Smoke test (local and CI)

```bash
uv run python scripts/mcp_smoke.py
```

Starts `speccify-mcp` over stdio, runs a real MCP handshake with the official
Python client and checks `tools/list`, a `tools/call` and
`resources/read speccify://manifest`. Exit code `0` means green. The same call
runs as a CI step.
