# Playbooks

A playbook captures a **complex, recurring workflow**: the ordered steps, the
sources they were researched from, the assets they need, and the pitfalls you
would otherwise hit twice. It is written for coding agents — the knowledge an
agent would have to re-derive on every run.

The test for whether something deserves a playbook is not its size:

> **Would I have had to look this up again the second time?**

If yes, write it down. If a good agent gets it right from a one-line
instruction, it is a step inside a playbook, not a playbook.

## Shape

A playbook is a **bundle**: a directory with `playbook.yaml` and an optional
`assets/` tree.

```text
playbooks/speccify/macos-notarize-tauri/1.0.0/
  playbook.yaml
  assets/verify-signatures.sh
```

```yaml
schema_version: 1
id: "@speccify/macos-notarize-tauri"
version: 1.0.0
title: Sign and notarize a Tauri 2 app for distribution outside the App Store
summary: >
  Take a working Tauri 2 build to a .dmg that opens on a stranger's Mac without
  a Gatekeeper warning.

applies_to:                     # how an agent decides this is the right one
  platforms: [macos]            # where it runs
  stack: [tauri]                # what you must be building with
  requires: ["Tauri 2", "Apple Developer Program"]
  keywords: [codesign, notarization]

prerequisites:
  - "`pnpm tauri build` already produces a working unsigned .app"

steps:
  - id: signing_identity
    title: Have a Developer ID signing identity available
    uses: "@speccify/apple-developer-id-cert@^1.0"   # reuse another playbook

  - id: notarize
    title: Submit to notarytool and wait for the verdict
    detail: |
      Markdown — what to do, in which order, what to watch out for.
    sources: [notarytool_docs]
    assets: [assets/verify-signatures.sh]
    verify: notarytool reports status "Accepted".

sources:                        # the expensive part: where this came from
  - id: notarytool_docs
    title: Notarizing macOS software before distribution
    url: https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
    retrieved: 2026-08-06

pitfalls:
  - Notarization silently fails for unsigned sidecars — verify each embedded binary.

acceptance:
  - given: a freshly built and notarized .dmg
    when: it is opened on a Mac that has never seen the developer certificate
    then: it launches without a Gatekeeper warning
```

Schema: [`schema/playbook.schema.json`](../schema/playbook.schema.json).
Validate with `speccify lint playbooks/`.

## The parts, and why they exist

| Field | Why |
|---|---|
| `steps` | Order is the part that is expensive to rediscover. Each step is either self-contained (`detail`) or delegated (`uses`) — never both. |
| `verify` | Tells an agent how to confirm a step worked *before* moving on. Without it, failures surface three steps later. |
| `sources` | Every link carries `retrieved`, so ageing is measurable rather than a guess. Sources must be referenced by a step — an unused source is dead weight. |
| `assets` | Files that travel with the playbook: scripts, configs, screenshots. They are part of the bundle hash. |
| `pitfalls` | The things you get wrong once. Often the most valuable field in the file. |
| `applies_to` | Selection criteria for agents and for `speccify search`. |

Deliberately absent: an execution engine. The agent is the executor; the
playbook is context, not a scripting language.

## Finding the right playbook

`applies_to` has three axes, and keeping them apart is what makes "what do I
have for Tauri?" a lookup instead of a substring hunt through a list that also
contains `dmg` and `gatekeeper`:

| Axis | Question it answers | Examples |
|---|---|---|
| `platforms` | Where does this run? | `macos`, `ios`, `linux`, `windows`, `web` |
| `stack` | What must I be building with? | `tauri`, `swiftui`, `react`, `storekit`, `fastlane`, `swiftpm` |
| `keywords` | Everything else worth finding it by | `notarization`, `paywall`, `sse` |

Leave an axis empty when the playbook holds regardless — the Streamable-HTTP
client playbook names no platform and no stack, because it is true in any
language. An empty axis is a statement, not an omission.

`speccify search` matches the axes **exactly** and keywords by substring, so
`ios` does not match `macos`, and a stack hit outranks a keyword hit.

### Recommended spellings

Neither axis is a fixed list in the schema, on purpose. Speccify has no central
authority handing out names — that is the whole point of using git repositories
as identity — and an enum would reintroduce one: every new framework would need
a schema release, and older Speccify versions would reject playbooks written
for it.

The cost of that freedom is drift (`app-store` and `appstore`, `iap` and
`in-app-purchase`). So converge by convention, the way npm keywords do:

- **lowercase, hyphenated**, no spaces — `mac-app-store`, not `Mac App Store`
- **singular**, unless the thing is plural by nature — `subscription`, `docs`
- the **name the ecosystem uses for itself** — `swiftpm`, not `swift-package-manager`
- platforms: `macos`, `ios`, `ipados`, `tvos`, `visionos`, `linux`, `windows`,
  `android`, `web`
- stacks in use here today: `tauri`, `swift`, `swiftui`, `swiftpm`, `xcode`,
  `storekit`, `fastlane`

Before inventing a term, check what the existing playbooks use:
`speccify search --json ""` lists everything with its axes.

## Reuse

A step can delegate to another playbook:

```yaml
steps:
  - id: signing_identity
    title: Have a Developer ID signing identity available
    uses: "@speccify/apple-developer-id-cert@^1.0"
```

The resolver follows those references transitively and pins every bundle in
`speccify.lock`. Child playbooks are not born from splitting a big playbook
top-down — they appear when the same block shows up in a *second* playbook and
stands on its own.

## Using them

```bash
speccify search notarization          # find one (discovery indexes)
speccify add @speccify/macos-notarize-tauri
speccify show @speccify/macos-notarize-tauri
speccify show @speccify/macos-notarize-tauri --step notarize --json
speccify pull                          # materialise bundles, assets included
speccify verify                        # bundles still match the lockfile?
```

Agents use the MCP server instead: `playbook_list`, `playbook_get`,
`playbook_step`, `playbook_asset`, `playbook_check`, `search`, `lock`, `pull`,
`verify` — the same core, so the answers cannot drift. Two more connect an
agent to the viewer a person is looking at: `viewer_selection` and
`playbook_propose` (see [the viewer](./viewer.md)).

## Staying true

Code has compilers; playbooks have decay. `speccify check` asks whether a
playbook is still *true* rather than merely well-formed:

```bash
speccify check playbooks/                 # structure + source age (offline)
speccify check playbooks/ --links         # also: do the URLs still resolve?
speccify check playbooks/ --stale-days 90 # tighter freshness bar
```

- **Structure** — the same rules `lint` applies.
- **Age** — every source carries `retrieved`, so "last read 582 days ago"
  is a fact rather than a feeling. Warnings do not fail the run; errors do.
- **Reachability** — opt-in, because it needs the network. A 404 is an error,
  a 500 a warning, a redirect is fine.
- **Soft 404s** — some hosts answer `200` for pages that do not exist and put
  "Page Not Found" in the body, which status-code checking cannot see. Before
  checking a host, `check` requests a URL it invented; if that renders a page
  announcing itself as missing, every source on that host whose page is *that
  page* is reported as gone.

  The canary's own status code is ignored on purpose — `developer.apple.com`
  answers an honest 404 at the site root while returning `200` for missing
  pages inside its help section, serving the identical body for both. What
  calibration needs is what a missing page *looks like* on that host.

  A host whose canary shows no such marker is never compared: a site that
  serves one shell for every path cannot be told apart, and guessing there
  would reject all of its sources.

Agents get the same thing through the `playbook_check` MCP tool — worth calling
before following a playbook you have not used in a while.

## Reproducibility

`speccify lock` pins each bundle by a **hash over all its files** (sorted paths
plus contents, so a changed asset changes the hash) and, for git sources, by
the commit behind the tag. `speccify verify` reports version drift, bundle
drift and moved tags. A playbook you used three months ago still says the same
thing today — or `verify` tells you it does not.

## Cross-references

- [Git sources and discovery](./git-sources.md)
- [The viewer](./viewer.md)
