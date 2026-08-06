# Speccify

> Playbooks for complex, recurring workflows — written for coding agents,
> shared over Git.

A **playbook** captures a piece of work you have done before and would have to
research again: the ordered steps, the sources they came from, the assets they
need, and the pitfalls you only find out about once.

```yaml
steps:
  - id: trial_storage
    title: Store the start date where deleting the app cannot reach
    detail: |
      UserDefaults survives a backup but not a delete; the Keychain survives a
      delete but not a new device; iCloud spans devices but needs an account.
      Write to two, read the union, earliest start wins.
    sources: [review_guidelines]
    verify: Deleting and reinstalling does not reset the remaining days.
```

The test for whether something deserves a playbook is not its size:

> **Would I have had to look this up again the second time?**

If yes, write it down once. If a good agent gets it right from a one-line
instruction, it belongs *inside* a playbook as a step — not as one.

## Why this and not a folder of notes

Notes rot silently. Playbooks are versioned, pinned and checkable:

- **`speccify check`** reports how old every source is and whether its URL
  still resolves. Stale instructions are worse than none, so ageing is a fact
  in the tool, not a feeling.
- **`speccify.lock`** pins each playbook by a hash over its whole bundle and,
  for git sources, by commit. A playbook you used three months ago still says
  the same thing today — or `verify` tells you it does not.
- **Agents read them directly** over MCP: find, read a step, fetch an asset,
  check freshness. No copy-paste from a wiki.

## Quickstart

```bash
uv sync --all-packages
pnpm install --frozen-lockfile

uv run speccify lint playbooks/          # the reference playbooks in this repo
uv run speccify check playbooks/ --links # are their sources still alive?
./scripts/dev-up.sh                      # viewer on :5173, backend on :8000
```

In a project that consumes playbooks:

```bash
uv run speccify init
uv run speccify search notarization
uv run speccify add git+https://github.com/acme/notarize-playbook
uv run speccify show @acme/notarize --step staple
```

## The three ways in

Everything exists as CLI, as MCP tool and over HTTP — the same core, so the
answers cannot drift.

| | |
|---|---|
| **CLI** | `init`, `search`, `add`, `lock`, `pull`, `verify`, `show`, `lint`, `check` |
| **MCP** | `playbook_list/_get/_step/_asset/_check`, `search`, `lock`, `pull`, `verify`, plus `viewer_selection` and `playbook_propose` |
| **HTTP** | `/playbooks`, `/playbook`, `/playbook/asset`, `/index`, `/validate`, `/selection`, `/proposal` |

## The viewer

`./scripts/dev-up.sh` opens a read-only viewer: the workflow as a diagram, the
steps with rendered markdown, sources with their age, assets inline.

There is no edit mode. You select a step and ask the agent beside you — it
reads that selection through `viewer_selection`, so "why is this necessary?"
resolves against what is on screen. When the answer belongs in the playbook,
the agent proposes the change and you see a diff with an Apply button. Nothing
is written until you click it.

## Sharing

Like Go modules: the repository URL is the identity, tags are the versions,
publishing is `git tag` + `git push`. No account, no central registry.

```yaml
dependencies:
  "git+https://github.com/acme/notarize-playbook": "^1.0"
```

Discovery works through **index repositories** — one file per playbook repo,
extendable by pull request ([`index/README.md`](./index/README.md)).

## Documentation

- [`docs/playbooks.md`](./docs/playbooks.md) — the format, the fields and why each exists
- [`docs/viewer.md`](./docs/viewer.md) — the viewer and the agent beside it
- [`docs/git-sources.md`](./docs/git-sources.md) — git sources, pinning, discovery
- [`docs/launch.md`](./docs/launch.md) — what is left before this goes public

Reference playbooks live in [`playbooks/`](./playbooks/): notarizing a Tauri
app, getting a Developer ID certificate, shipping a trial-then-unlock in-app
purchase, and testing StoreKit.

## Status

The project pivoted on 2026-08-06 from component specs to workflow playbooks:
coding agents got good enough that describing a button is no longer worth
doing, while the knowledge around a *task* — the order, the fine print, the
dead ends — is exactly what they still lack. What carried over is the part
that was always the point: version pinning, hashes and checkable sources.

MIT licensed. No hosted service, no account, no telemetry.
