---
title: Exporting your own skill
description: A workflow you learned becomes a skill in your own Speccify work repo.
sidebar:
  order: 7
---

Importing is half the cycle. The other half: what building 4Notice
*taught* you goes back into a repo you own — your **Speccify work
repo** — available to every following project. This chapter sets
that repo up.

## 1. Create your work repo

One private GitHub repo, one directory per skill bundle:

```text
your-skills-repo/
└── skills/
    ├── macos-notarize-tauri/
    │   ├── SKILL.md
    │   └── tools/
    │       └── verify-signatures/
    │           ├── TOOL.md
    │           └── fixtures/…
    └── release-checks/
        ├── SKILL.md
        └── tools/…
```

```sh
gh repo create your-skills-repo --private
```

Bundles carry **tool specs, not implementations** — contracts travel,
scripts don't ([why](/speccify/overview/)). A `reference.py` per tool
is fine as a worked example for one platform; the spec stays the
truth.

## 2. Tag discipline

Versions are git tags, one per bundle: `skills/<name>/v1.0.0`. Two
rules from practice:

- **Tags are final.** Version resolution picks the *lowest* tag that
  satisfies a range — so a broken `v1.0.0` left in place would be
  chosen forever. A mistake means a new tag *and* deleting the broken
  one (as long as nobody has locked it), never re-tagging in place.
- **Reference sibling skills within the same source** (a `uses` link
  to `git+…#skills/<other>@^1.0`), so a bundle resolves no matter
  where it's consumed from.

Before pushing, validate:

```sh
speccify check    # every bundle: frontmatter, specs, examples
```

## 3. Prove the loop

The acceptance test for your repo is the import you already know: in
an empty scratch folder, `add` one of your bundles by its
`git+…#skills/<name>` id, expand it, and watch normal skills and tool
contracts appear under `.agent/` — exactly the
[import experience](/tutorial/importing-skills/) 4Notice had, now
served from *your* repo.

## 4. Export a workflow you actually learned

:::note[Stub — this step is next on the real project]
4Notice's candidate is written down: *"SwiftUI app from zero to the
first runnable build with the Speccify app"* — the setup workflow from the
[project-setup chapter](/tutorial/project-setup/), generalized into a
`SKILL.md` with its lessons (argv-without-shell, DerivedData vs.
iCloud) as pitfalls, plus tool specs where a check can be mechanical.
When that export has run, this section becomes the worked example:
what generalized, what stayed project-specific, and how the skill
looked arriving in the next project.
:::

The shape of the move is already clear from the import chapter run
backwards: strip the project-specific parts into an `## In this
project`-style tail (they stay behind), turn hard-won findings into
`Pitfalls`, give every step a `Verify:` line, and give tools a
contract with examples — because your next project will trust the
[check](/speccify/evaluate/), not your memory.
