---
title: Expand
description: From a source skill to normal project files — and a provenance record that remembers where everything came from.
sidebar:
  order: 2
---

**Expand** turns a skill from a source repo into one or more normal
skills under `.agent/skills/`, plus tool contracts under
`.agent/tools/`. `speccify expand <skill>` computes the dependency
tree, creates the directories and `TOOL.md` copies, strips the
Speccify metadata, writes the provenance record — and hands the agent
a task list: *"2 skills normalized, 3 tools to implement for macos,
2 placeholders to fill."*

What happens to the content:

- **References are resolved.** A skill the source referenced via
  `uses` becomes its own normal skill next door; the reference in the
  body becomes an ordinary relative link.
- **Metadata is stripped.** No `speccify.*` frontmatter survives in
  the project — a project skill looks exactly like a hand-written one.
- **Placeholders become concrete** (bundle id, paths, identities,
  ports), and project specifics are *added* as an `## In this
  project` section — the upstream body stays untouched, so a later
  re-expand is a merge, not a rewrite.
- **Tool contracts are copied** to `.agent/tools/<name>/TOOL.md`, so
  the contract lives where the implementation will. Tools are
  project-wide: two skills that need the same tool share one
  implementation.

## The provenance record

Origin does not live in the skill — it lives in
`.agent/speccify/expansions.yaml`, written by `speccify expand`. From
the Speccify app project, verbatim:

```yaml
schema_version: 1
skills:
  release-checks:
    source: git+https://github.com/mhennemeyer/speccify-first-test#skills/release-checks
    version: 1.0.0
    bundle_sha256: sha256:9692ba527af7c8a12ec94a56cd925a1609f97965bba1959da2408307791fe425
    expanded: '2026-08-23'
    requested: true
    tools:
    - check-entitlements
    - check-plist-keys
    - orphan-strings
tools:
  check-plist-keys:
    from:
    - release-checks
    spec_sha256: 8dc9cae189f6ced17c7c238de90ca3ac26eca36ec49f16d1211ea641d4f159dd
    platforms:
      macos:
        file: macos.py
        status: verified
        checked: '2026-08-23'
```

The record answers three questions the files alone can't: *where did
this come from* (source, version, content hash), *which tools does it
bring and in what state* (`implemented` vs. `verified`, per
platform), and *has upstream moved on* since the expansion. The file
carries a warning in its header for a reason: **edit the skills, not
this file** — it is bookkeeping, and Speccify maintains it.

With the files in place and the task list in hand, the agent moves on
to [Execute](/speccify/execute/).
