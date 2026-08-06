# Speccify web backend

The HTTP face of `speccify-core`: the same playbook engine the CLI and the MCP
server use, exposed over FastAPI. The viewer (`apps/composer/`) is its only
frontend.

Everything runs in-process against `speccify-core` — there is no database, no
auth and no persistence beyond the playbook library on disk.

## Quickstart

```bash
uv run speccify-web-backend --host 127.0.0.1 --port 8000
```

Or, together with the viewer and the docs site:

```bash
./scripts/dev-up.sh
```

## Endpoints (v1)

**Playbooks** — read-only over the configured library:

- `GET /api/v1/playbooks` — every playbook in the library, newest version each
- `GET /api/v1/playbook?source=<id>` — one playbook, parsed and resolved
- `GET /api/v1/playbook/asset?source=<id>&path=assets/…` — an asset's bytes
- `GET /api/v1/index?q=…` — discovery search across configured index repos
- `POST /api/v1/validate` — validate a `playbook.yaml` without storing it

**Session** — the bridge between the viewer and the agent beside it. Both
pieces of state live in memory: this is one person, one viewer, one agent, on
one machine, and a selection that outlived the session would be a lie about
what is on screen.

- `PUT /api/v1/selection` — the viewer pushes what the user clicked
- `GET /api/v1/selection` — the same, **resolved** (the step with its detail,
  verify and sources; or the asset's content). This is what the
  `viewer_selection` MCP tool reads, so the agent does not need three more
  calls to learn what "this step" means.
- `POST /api/v1/proposal` — an agent proposes a changed playbook. Validated
  immediately: an invalid proposal never reaches the UI, because otherwise the
  user would be looking at a diff they cannot apply.
- `GET /api/v1/proposal` / `DELETE /api/v1/proposal` — the viewer polls, or discards
- `POST /api/v1/proposal/apply` — writes it to the local library. Only a human
  click gets here, and git-sourced playbooks are refused (`not_local`):
  changes belong in the source repository, or the next `pull` overwrites them.

**Error codes** are shared with the CLI and MCP: `not_found` (404),
`invalid_playbook` / `invalid_yaml` (422), `not_local` (400).

## Tests

```bash
uv run pytest apps/web/backend/tests -v
```
