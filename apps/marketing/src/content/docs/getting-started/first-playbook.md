---
title: Your first playbook
description: Turn something you have done twice into a playbook an agent can follow.
---

Write a playbook the **second** time you do something. The first time you do
not yet know which parts were hard; the second time you do, and you still
remember.

## 1. The shape

A playbook is a directory: a `playbook.yaml` plus an optional `assets/` folder.
That directory is the unit Speccify hashes, pins and distributes.

```
macos-notarize-tauri/
├── playbook.yaml
└── assets/
    └── entitlements.plist
```

## 2. Write the steps

```yaml
# playbook.yaml
schema_version: 1
id: "@org/macos-notarize-tauri"
version: 1.0.0
title: Notarize a Tauri app for macOS
summary: |
  Sign, notarize and staple a Tauri app so it opens without a Gatekeeper
  warning on a machine that has never seen it.

applies_to:
  platforms: [macos]
  keywords: [tauri, notarization, gatekeeper]

prerequisites:
  - An Apple Developer ID Application certificate in the login keychain.

steps:
  - id: entitlements
    title: Declare the entitlements the hardened runtime needs
    detail: |
      Notarization requires the hardened runtime, which blocks the JIT and
      unsigned memory Tauri's webview needs. Without these two keys the app
      notarizes and then crashes on launch — which is worse than failing.
    assets: [assets/entitlements.plist]
    sources: [hardened_runtime]
    verify: codesign -d --entitlements - Speccify.app lists both keys.

sources:
  - id: hardened_runtime
    title: Hardened Runtime entitlements
    url: https://developer.apple.com/documentation/security/hardened-runtime
    retrieved: 2026-08-06
```

Three things carry the weight:

- **`detail` says why, not just what.** "Add these entitlements" is something
  an agent can already guess. "Without them it notarizes and then crashes" is
  the thing you paid for the first time.
- **`sources` carry a `retrieved` date.** That is what makes rot detectable
  later.
- **`verify` is how you know it worked** — a command or an observation, not a
  feeling.

A step either describes itself with `detail` or delegates to another playbook
with `uses` — never both, because then it is unclear which one to follow:

```yaml
  - id: certificate
    title: Get a Developer ID certificate
    uses: "@org/apple-developer-id-cert@^1.0"
```

## 3. Check it

```bash
uv run speccify lint playbooks/org/macos-notarize-tauri
uv run speccify check playbooks/org/macos-notarize-tauri --links
```

`lint` is structure. `check` adds source age, and `--links` asks whether every
URL still resolves. Run it again in six months — that is the point.

## 4. Look at it

```bash
./scripts/dev-up.sh     # → http://localhost:5173
```

The [viewer](/viewer/) shows the workflow as a diagram and every source with
its age. There is no edit mode: select a step, ask the agent beside it, and
apply what it proposes as a diff.

## 5. Share it

Publishing is `git tag` + `git push` — no registry account:

```yaml
dependencies:
  "git+https://github.com/acme/notarize-playbook": "^1.0"
```

More: [Git sources & discovery](/git-sources/).
