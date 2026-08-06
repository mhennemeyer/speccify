# Discovery index

An index says **where** playbooks live — not which versions exist. Versions are
git tags and therefore always current, which means an index cannot go stale.

The model is Homebrew taps and Scoop buckets: a git repository, one file per
playbook repository, extended by pull request. This directory is the Speccify
repository's own index and doubles as the template for your own.

## Format

One file per entry under `entries/*.yaml`. The filename is free; the `source`
is the key. Schema:
[`schema/index-entry.schema.json`](../schema/index-entry.schema.json).

```yaml
schema_version: 1
source: git+https://github.com/acme/notarize-playbook   # or with #path/in/repo
title: Notarize a Tauri app for macOS
summary: Sign, notarize and staple so it opens without a Gatekeeper warning.
keywords: [macos, tauri, notarization, gatekeeper]
homepage: https://github.com/acme/notarize-playbook
license: MIT
```

Required: `schema_version`, `source`, `title`, `summary`. Everything else is
optional, but `keywords` is what makes an entry findable — `speccify search`
matches against title, summary and keywords.

One file per entry is deliberate: a pull request touches exactly one file,
there are no merge conflicts in a growing list, and CI validates each entry on
its own.

## Adding an entry

1. Tag the playbook repository (`v1.2.0`; for a playbook in a subdirectory,
   `<path>/v1.2.0`).
2. Add `entries/<name>.yaml` in the format above.
3. Open a pull request. CI validates the schema and that no two entries claim
   the same `source` (`core/tests/test_spec_index.py::test_repo_index_is_valid`).

## Using it

```bash
speccify search notarization                 # sources: --index, SPECCIFY_INDEX, ./index
speccify search --index git+https://github.com/acme/playbook-index notarization
speccify search --json notarization          # machine-readable, for agents
```

Git indexes live in the same bare-clone cache as playbook sources and are
readable with `--offline` afterwards.

**No entries yet**: the ecosystem gets seeded at launch — placeholder URLs
would be dead links. The format, the validation and `speccify search` all
stand, so entries can be added from now on.
