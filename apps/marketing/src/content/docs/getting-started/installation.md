---
title: Installation
description: Set Speccify up locally — CLI, MCP server and viewer.
---

Speccify is a Python workspace (CLI, MCP server, web backend) plus two Node
apps (viewer, docs site). Everything is MIT licensed; there is no account and
no hosted service.

## Prerequisites

| Tool | What for |
|---|---|
| [uv](https://docs.astral.sh/uv/) | the Python workspace (CLI, MCP, backend) |
| Node ≥ 22 + pnpm | viewer and docs site |
| `git` | consuming playbooks from git repositories |

Only `uv` is required. Without Node you still get the CLI and the MCP server,
which is the whole tool minus the viewer.

## Set up

```bash
git clone https://github.com/mhennemeyer/speccify && cd speccify
uv sync --all-packages
pnpm install --frozen-lockfile
```

Check that it stands:

```bash
uv run speccify --help
uv run speccify lint playbooks/
uv run pytest -q
```

## The three ways in

Every capability exists as a CLI command, an MCP tool and an HTTP endpoint —
all three over the same `speccify-core`, so they cannot drift apart.

```bash
# CLI
uv run speccify check playbooks/ --links

# MCP server (stdio) for coding agents
uv run speccify-mcp --project .

# Backend + viewer + docs site
./scripts/dev-up.sh          # :8000, :5173, :4321
```

As a desktop app: `./scripts/dev.sh --release` builds `Speccify.app`
(see [Download](/download/)).

## Next

- [Your first playbook](/getting-started/first-playbook/)
- [The playbook format](/concepts/playbooks/)
- [The viewer](/viewer/)
