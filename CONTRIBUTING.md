# Contributing to Speccify

Thanks for your interest in Speccify — a fully open-source, spec-first
platform for language- and framework-independent component specifications.

> Note: Some internal docs and plans are currently written in German while the
> project transitions to a public open-source workflow. English contributions
> and issues are very welcome; docs are being migrated over time.

## Getting started

```bash
# Requirements: uv (https://docs.astral.sh/uv/), Python 3.12+, pnpm (frontends only)
uv sync --all-packages
uv run pytest              # 372 tests, offline, no API keys needed
uv run ruff check .
uv run ruff format --check .
```

The full local system (playground backend/frontend + docs site):

```bash
./scripts/dev-up.sh
```

See [`docs/local-dev-e2e.md`](./docs/local-dev-e2e.md) for the complete
walkthrough.

## Project layout

| Path | Purpose |
|---|---|
| `core/` | `speccify-core` — spec loader, schema validator, MVS resolver, codegen |
| `cli/` | `speccify` CLI — thin adapter over `core/` |
| `mcp/` | MCP server for coding agents — thin adapter over `core/` |
| `schema/` | JSON schemas (playbook, manifest, lockfile, index entry) |
| `playbooks/` | Reference playbooks |
| `apps/web/` | HTTP backend (FastAPI) |
| `apps/composer/` | The playbook viewer (React + Vite) |
| `apps/marketing/` | Landing page + docs site (Astro Starlight) |

Roadmap: [`.agent/plans/`](./.agent/plans/) — exactly one plan is active at a time.

## Ground rules

- **The default suite is offline.** Never add tests that need network access
  or API keys to it. The one exception is the link check, which lives behind
  the `links` pytest marker and is deselected by default (`pytest -m links`).
- **Logic lives in `core/`** — `cli/`, `mcp/` and the web backend are thin
  adapters over it, so the three paths cannot give different answers.
- **A playbook's sources carry a `retrieved` date.** If you touch a playbook,
  re-read what you changed and update that date. Stale instructions are worse
  than none, because an agent will follow them confidently.
- **Tests with assertions for all code.** Run `uv run pytest` and
  `uv run ruff check .` before opening a PR.
- **Conventional Commits**: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`,
  `test:`.
- Branches: `feat/<topic>`, `fix/<topic>`; `main` is the default branch.

## Pull requests

1. Fork and create a feature branch.
2. Keep changes focused; one concern per PR.
3. Include tests and update affected docs (`docs/`, generated CLI reference
   via `uv run python scripts/gen_cli_docs.py`).
4. Make sure the drift checks pass: `scripts/sync_docs_to_site.py --check`
   and `scripts/gen_cli_docs.py --check`.

## License

By contributing you agree that your contributions are licensed under the
[MIT License](./LICENSE).
