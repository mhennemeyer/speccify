---
title: "The viewer"
description: "The viewer shows a playbook the way you want to read it: steps in order, sources with their age, assets inline, child playbooks one click away."
---

<!-- AUTOGENERIERT aus docs/ via scripts/sync_docs_to_site.py — nicht von Hand editieren. -->

The viewer shows a playbook the way you want to read it: steps in order,
sources with their age, assets inline, child playbooks one click away.

```bash
./scripts/dev-up.sh          # backend :8000 + viewer :5173
```

## No edit mode — on purpose

You do not hand-edit playbooks in a form. Agents write prose and YAML better
than a property grid ever could, so the viewer is **read-only**: you select
something, ask the agent next to it, and accept the change it proposes. The
YAML pane stays as the escape hatch.

## Selection is context

Clicking a step, a source or an asset sets the *selection*. That selection is
what a context-aware agent reads — so "why is this necessary?" resolves against
the step you are looking at, without you restating it.

| Area | What it shows |
|---|---|
| Library (left) | Every playbook in the local library: title, id, version, step count, keywords. One filter box narrows the list *and* doubles as the query for the discovery index — "nothing here, look further" is one click, not a second search UI. |
| Flow (centre-left) | The workflow at a glance: one node per step, delegated ones dashed, markers for assets and verify criteria. Clicking a node selects and scrolls to the step. Long playbooks are hard to hold in your head as a list. |
| View (centre) | Summary and prerequisites, the ordered steps with their `detail` rendered as **markdown** (code blocks, lists, emphasis), verify criteria, source chips, asset chips that expand inline, pitfalls, sources. |

## Ageing is visible

Every source shows how old it is — "retrieved today", "4 months old" — and
anything past the 180-day mark is highlighted in amber, in the chip and in the
source list. The same threshold `speccify check` uses, so the viewer and the
command line never disagree.

## Everything is an endpoint

The viewer has no privileged access — it uses the same HTTP API agents use:

```bash
curl -s localhost:8000/api/v1/playbooks | jq '.playbooks[].id'
curl -s --get localhost:8000/api/v1/playbook \
  --data-urlencode 'source=@speccify/macos-notarize-tauri' | jq '.steps[].id'
curl -s --get localhost:8000/api/v1/playbook/asset \
  --data-urlencode 'source=@speccify/macos-notarize-tauri' \
  --data-urlencode 'path=assets/verify-signatures.sh' | jq -r '.content'
curl -s 'localhost:8000/api/v1/index?q=notarization' | jq '.hits[].source'
```

## What agents use instead

| Tool | Purpose |
|---|---|
| `playbook_list` | what exists in this project's library |
| `playbook_get` | the whole playbook, sources resolved |
| `playbook_step` | one step, with its `verify` criterion |
| `playbook_asset` | a file that ships with the playbook |
| `playbook_check` | is it still current? |
| `search` | find playbooks in discovery indexes |
| `lock` / `pull` / `verify` | pin, materialise, detect drift |

The contract is pinned by a test that walks the whole chain — list, get,
follow a delegated step into its child playbook, read a step, read its asset —
using nothing but the tools.

## Status

The viewer covers reading a playbook end to end. Still to come: the step
diagram, and the chat panel with the selection-aware agent (see the active plan
under `.agent/plans/`).
