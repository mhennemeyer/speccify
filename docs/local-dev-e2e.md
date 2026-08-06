# Local walkthrough: from a playbook to an agent using it

This runs the whole system on your machine and walks the path a playbook takes:
write it, check it, look at it, hand it to an agent. Nothing here needs the
network except the optional link check.

## 1. Bring it up

```bash
uv sync --all-packages
./scripts/dev-up.sh
```

| Service | URL | What it is |
|---|---|---|
| Backend (FastAPI) | <http://127.0.0.1:8000> | `speccify-core` over HTTP |
| Viewer (Vite) | <http://localhost:5173> | the playbook viewer |
| Docs site (Astro) | <http://localhost:4321> | landing page + docs |

`Ctrl-C` stops all of them. Without Node installed:

```bash
./scripts/dev-up.sh --no-frontends   # backend only
```

## 2. Look at the reference playbooks

Four playbooks live in `playbooks/speccify/`. Open the viewer and pick
**Ship a trial-then-unlock in-app purchase** — it is the one with everything in
it: nine steps, three assets, a delegated step that pulls in a second playbook.

What is worth noticing:

- The **workflow diagram** at the top is the step order. A step drawn with a
  double border delegates to another playbook via `uses`.
- Every **source** shows how long ago it was retrieved. Past 180 days it turns
  into a warning — the same threshold `speccify check` uses, deliberately, so
  the screen and the CLI never disagree.
- There is **no edit button**. That is the design, not a gap; see step 5.

## 3. Check them

```bash
uv run speccify lint playbooks/            # structure only
uv run speccify check playbooks/           # + how old every source is
uv run speccify check playbooks/ --links   # + does every URL still resolve
```

The first two are offline and belong in a normal test run. `--links` needs the
network and is slow, which is why it sits behind the `links` pytest marker and
is deselected by default:

```bash
uv run pytest -m links      # the network checks, explicitly
```

Try breaking one on purpose — change a `retrieved:` date to two years ago, or
point a source at a URL that 404s. Both should be reported, and the structural
errors should shadow the age warnings rather than pile up next to them.

## 4. Use one from an agent

The MCP server speaks the same core over stdio:

```bash
uv run python scripts/mcp_smoke.py     # lists the tools and exercises them
```

In an agent, the sequence that matters is: `playbook_list` → `playbook_get` →
`playbook_step` → `playbook_asset`. That path is pinned by a test
(`mcp/tests/`), because an agent that has to guess the order is an agent that
gets it wrong halfway through a release.

## 5. The agent beside the viewer

Select a step in the viewer. The viewer pushes that selection to the backend,
and `viewer_selection` hands it to the agent **resolved** — the step with its
detail, its verify line and its sources, not just an id. Ask "why is this
necessary?" and it answers about the step on your screen.

When the answer belongs in the playbook, the agent calls `playbook_propose`
with the full new YAML. The backend validates it immediately, so an invalid
proposal never becomes a diff you cannot apply. The viewer shows the diff with
**Apply** and **Discard**. Nothing touches disk until you click.

Two things it will refuse:

- **Playbooks from git sources.** Changes belong in the source repository — as
  a commit and a new tag. A local edit would be overwritten by the next `pull`.
- **Anything that does not validate.** The proposal is rejected at the door
  with the reason.

## 6. Consume a playbook from a git repository

In a scratch directory:

```bash
uv run speccify init
uv run speccify add git+file:///path/to/a/playbook/repo
uv run speccify lock
uv run speccify verify
```

`speccify.lock` now pins the bundle hash *and* the commit behind the tag.
`verify` re-fetches and compares — if the tag was moved, this is where you find
out. Details in [`git-sources.md`](./git-sources.md).

## Troubleshooting

- **Vite only listens on `::1` here.** Playwright waits on `127.0.0.1`, so the
  composer's `playwright.config.ts` starts the dev server with
  `--host 127.0.0.1`. If you start it by hand, do the same.
- **`uv run` re-syncs and re-hides editable `.pth` files** under macOS
  quarantine. `dev-up.sh` runs the hygiene script once and then sets
  `UV_NO_SYNC=1`; when running commands by hand, export
  `PYTHONPATH="$PWD/core/src:$PWD/cli/src:$PWD/mcp/src:$PWD/apps/web/backend/src"`.
- **Git-source tests skip cleanly** when `git` is not on `PATH`.
