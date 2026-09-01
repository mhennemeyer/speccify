# docs/

Product documentation. The pages listed under "on the site" are the source of
truth for [speccify.io](https://speccify.io) — `scripts/sync_docs_to_site.py`
mirrors them into the Astro site, and CI fails on drift, so edit them here and
never there.

## On the site

| File | Page |
|---|---|
| [`git-sources.md`](./git-sources.md) | git sources, pinning, discovery indexes |

## Repository only

| File | What it covers |
|---|---|
| [`local-dev-e2e.md`](./local-dev-e2e.md) | the whole system on your machine, end to end |
| [`release.md`](./release.md) | tagging a release; signing and notarization |
| [`deploy.md`](./deploy.md) | where the site is hosted |
| [`launch.md`](./launch.md) | what is left before and around going public |
| [`toolkit.md`](./toolkit.md) | the desktop app's MCP servers and terminal |
| [`exec-mcp-contract.md`](./exec-mcp-contract.md) | the exec server wire contract |

The CLI and MCP references on the site are generated from the binary
(`scripts/gen_cli_docs.py`) and are not edited by hand.
