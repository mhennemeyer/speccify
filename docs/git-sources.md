# Git repositories as playbook sources

Playbooks are shared like Go modules or SwiftPM packages: **the repository URL
is the identity, tags are the versions**. Nothing central hands out names,
there is no login and no publish upload — releasing is `git tag` + `git push`.

## Referencing a git source

```yaml
# speccify.yaml
schema_version: 1
dependencies:
  "git+https://github.com/acme/notarize-playbook": "^1.2"      # bundle at the repo root
  "git+https://github.com/acme/kit#playbooks/iap": "^0.1"      # bundle in a subdirectory
```

The same form works in a step's `uses:`, which is how one playbook delegates
part of its work to another.

| Form | Expected bundle | Expected tags |
|---|---|---|
| `git+<url>` | `playbook.yaml` at the repo root | `v1.2.0` |
| `git+<url>#<path>` | `<path>/playbook.yaml` | `<path>/v1.2.0` |

A monorepo can therefore version any number of playbooks independently: which
tags belong to which playbook follows mechanically from the id.

A playbook keeps its own name (`id: "@acme/notarize"`) — that is what it is
called once fetched. The id in the manifest says *where it came from*; the
lockfile records that origin, not the directory name.

## A playbook is a bundle

The unit is not a single file but the directory: `playbook.yaml` plus whatever
lives under `assets/`. A playbook whose script arrived but whose steps did not
would be worse than one that failed to arrive at all, so the whole bundle is
hashed together — sorted paths, each path and each content length-prefixed so
`a/b` + `c` cannot hash the same as `a` + `b/c`.

## Reproducibility

`speccify lock` records the bundle hash and, behind a tag, the **commit**:

```yaml
schema_version: 1
playbooks:
  - id: git+https://github.com/acme/notarize-playbook
    version: 1.2.0
    resolved_via: git
    source_commit: 9f1c0b1c1b2a4e7f5d3c8a90b1e2f3a4c5d6e7f8
    bundle_sha256: sha256:…
```

A tag that gets moved therefore shows up as a lockfile diff rather than as a
silent change in what you read. `verify` re-fetches and compares; the commit is
the additional anchor. Signed tags are a later, additive step.

## Cache and offline

Speccify keeps one **bare clone** per repository under `~/.cache/speccify/git/`
(override with `SPECCIFY_GIT_CACHE`). Tags come from `fetch --depth 1`, the
bundle from `git cat-file blob <tag>:<path>` — there is no working tree and no
checkout.

After the first resolve everything is reproducible offline: `pull --offline`
and `verify --offline` read local refs only. If the cache is missing, the run
stops with a hint instead of quietly going to the network. `git` always runs
with `GIT_TERMINAL_PROMPT=0`, so a private repository fails with an error
rather than hanging in a password prompt.

## Alongside the local library

Both sources run side by side: each library declares through `serves` which ids
it answers for (`@scope/name` → local library, `git+…` → git). A project may
mix both forms freely.

A **facade** (`MultiLibrary`) makes that work everywhere: the resolver takes a
list of libraries by nature, but everything else expects exactly one. The
facade routes each request to the first library that serves the id, so git
sources arrive without a special case anywhere downstream. An unreachable git
source is a validation finding in the viewer, not a crash.

## Discovery: finding playbooks

There is no central search service. An **index** is a git repository (or a
local directory) with one file per playbook repository — the model is Homebrew
taps and Scoop buckets:

```
<index-repo>/entries/<name>.yaml
```

```yaml
schema_version: 1
source: git+https://github.com/acme/notarize-playbook
title: Notarize a Tauri app for macOS
summary: Sign, notarize and staple so it opens without a Gatekeeper warning.
keywords: [macos, tauri, notarization]
license: MIT
```

One file per entry is deliberate: a pull request touches exactly one file,
there are no merge conflicts in a growing list, and CI validates each entry on
its own (schema: [`schema/index-entry.schema.json`](../schema/index-entry.schema.json)).

The index says **only where a playbook lives** — never which versions exist.
Versions are tags and therefore always current, which means an index cannot go
stale.

```bash
speccify search notarization
speccify search --index git+https://github.com/acme/playbook-index notarization
speccify search --json notarization      # for agents and scripts
speccify search --offline notarization   # local cache only
```

Source order: `--index` (repeatable) > `SPECCIFY_INDEX` (comma-separated —
**not** colon-separated, that character lives in every git URL) > `./index`.
Multiple indexes are merged; for the same source the first mention wins. Git
indexes live in the same bare-clone cache as playbook sources.

Template and contribution flow: [`index/README.md`](../index/README.md).

## Every way in, not just the CLI

| Path | Git sources | Discovery |
|---|---|---|
| CLI | `lock`/`pull`/`verify` against `git+…`, `--offline` uses only the cache | `speccify search` |
| MCP | the same tools, library facade included | tool `search` |
| Web/viewer | playbooks and their delegated children resolve across sources | `GET /api/v1/index?q=` |

Playbooks fetched from a git source are **read-only** in the viewer. A change
belongs in the source repository — as a commit and a new tag — because a local
edit would be overwritten by the next `pull`. `playbook_propose` refuses those
with `not_local` and says so.

## Limits

- The index in this repository is still empty: placeholder URLs would be dead
  links, so it gets seeded at launch.
- Only `https://` and `file://` remotes; SSH refs are deliberately not enabled
  yet (credential handling).
- Tags must carry exact semver (`v1.2.0`), no pre-releases.

## Cross-references

- Playbook format: [`playbooks.md`](./playbooks.md)
- Lockfile format: [`schema/lockfile.schema.json`](../schema/lockfile.schema.json)
- Local walkthrough: [`local-dev-e2e.md`](./local-dev-e2e.md)
