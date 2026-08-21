---
name: macos-notarize-tauri
description: Take a working Tauri 2 build to a `.dmg` that opens on a stranger's Mac without
  a Gatekeeper warning — hardened runtime, sidecar signing, notarization and stapling included.
  Use when working with tauri on macos, or when the user mentions codesign, notarization,
  gatekeeper, dmg or sidecar.
license: MIT
compatibility: Requires Tauri 2, Xcode command line tools and Apple Developer Program
---

## Prerequisites

- `pnpm tauri build` already produces a working unsigned .app
- An app-specific password for notarytool exists (appleid.apple.com -> Sign-In and Security)

## 1 — Have a Developer ID signing identity available

Covered by the skill `@speccify/apple-developer-id-cert@^1.0` — follow that one, then continue.

## 2 — Turn on the hardened runtime in tauri.conf.json

Notarization rejects anything without the hardened runtime. In
`src-tauri/tauri.conf.json`:

```json
"bundle": {
  "macOS": {
    "hardenedRuntime": true,
    "minimumSystemVersion": "10.15"
  }
}
```

Leave the signing identity **out** of the config and pass it through the
environment instead — otherwise every contributor needs your certificate
to build at all.

**Verify:** `codesign -d --entitlements - <app>` later shows the runtime flag.

*Source: Tauri — macOS bundle configuration.*

## 3 — Build with signing enabled

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: <name> (TEAMID)"
pnpm tauri build
```

Tauri signs the main binary, but **every sidecar and embedded binary must
carry a valid signature too** — check them explicitly rather than trusting
the build:

```bash
codesign --verify --deep --strict --verbose=2 "target/release/bundle/macos/<App>.app"
```

**Verify:** `codesign --verify --deep --strict` exits 0 for the .app and each sidecar.

*Source: Tauri — code signing for macOS.*

## 4 — Submit to notarytool and wait for the verdict

```bash
xcrun notarytool submit "<App>.dmg" \
  --apple-id "<apple-id>" --team-id "<TEAMID>" \
  --password "<app-specific-password>" --wait
```

On rejection, fetch the log — the summary alone rarely says enough:

```bash
xcrun notarytool log <submission-id> --apple-id … --team-id … --password …
```

**Verify:** notarytool reports status "Accepted".

*Source: Notarizing macOS software before distribution.*

## 5 — Staple the ticket and verify like a stranger's Mac would

Stapling puts the notarization ticket inside the artifact so first launch
works offline:

```bash
xcrun stapler staple "<App>.dmg"
spctl --assess --type open --context context:primary-signature -v "<App>.dmg"
```

`spctl` must answer `accepted` with `source=Notarized Developer ID`.

**Verify:** `spctl --assess` prints "accepted" and "source=Notarized Developer ID".

*Source: Customizing the notarization workflow.*

## Pitfalls

- Notarization silently fails for unsigned sidecars — verify each embedded binary, not just the .app.
- `spctl --assess` on the .app can pass while the .dmg fails; assess the artifact you actually ship.
- An expired app-specific password produces an authentication error that reads like a network problem.
- Keeping the signing identity in tauri.conf.json breaks builds for everyone without your certificate.

## Acceptance

- Given a freshly built and notarized .dmg, when it is opened on a Mac that has never seen the developer certificate, then it launches without a Gatekeeper warning.

## Sources

- [Tauri — macOS bundle configuration](https://tauri.app/reference/config/#macconfig) — retrieved 2026-08-06
  hardenedRuntime, minimumSystemVersion, signingIdentity.
- [Tauri — code signing for macOS](https://tauri.app/distribute/sign/macos/) — retrieved 2026-08-06
  Environment variables the build reads.
- [Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) — retrieved 2026-08-06
- [Customizing the notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow) — retrieved 2026-08-06
  Stapling and the spctl assessment.

## Tools

- [verify-signatures](../../tools/verify-signatures/TOOL.md) — the contract; `reference.sh` beside it is one
  implementation for macOS. Write your own where that one does not run.

## In this project

<!-- Everything above is upstream and is replaced on re-expand; this
     section is yours and is kept. Fill in what is specific here. -->

- Builds on [apple-developer-id-cert](../apple-developer-id-cert/SKILL.md).
- Tool [verify-signatures](../../tools/verify-signatures/TOOL.md) — implemented for this platform in `.agent/tools/verify-signatures/`; see the examples there for the contract.
