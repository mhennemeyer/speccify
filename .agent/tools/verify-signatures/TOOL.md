---
name: verify-signatures
description: Verifies the code signature of a macOS .app bundle and of every
  executable inside Contents/MacOS — the sidecars that notarization rejects
  without the build ever saying so. Reports the first offender.
inputs:
  type: object
  required: [bundle]
  additionalProperties: false
  properties:
    bundle:
      type: string
      description: Path to the .app bundle.
    identity:
      type: string
      description: Expected signing identity (substring of the certificate
        common name). When set, a valid signature by someone else is an offender.
outputs:
  type: object
  required: [ok, checked, offenders]
  properties:
    ok: {type: boolean}
    checked: {type: array, items: {type: string}, description: Bundle-relative
      paths that were verified.}
    offenders:
      type: array
      items:
        type: object
        required: [path, reason]
        properties:
          path: {type: string}
          reason: {type: string}
effects: reads the bundle; runs `codesign --verify` per binary; writes nothing
requires: codesign
runtime: any
platforms: macos
---

## Behaviour

1. Run `codesign --verify --deep --strict` on the bundle itself. A failure
   here is an offender with path `.`.
2. Walk `Contents/MacOS` and every executable file in it (the Tauri sidecars
   land there); verify each with `codesign --verify --strict`.
3. When `identity` is given, also read the signature's authority
   (`codesign -dvv`) and treat a mismatch as an offender — a bundle signed by
   an ad-hoc or a development identity verifies fine and still fails notarization.
4. `ok` is true only when `offenders` is empty. Never stop at the first
   failure: the point is the complete list, because fixing them one per
   notarization round takes an hour each.

The tool must not modify, re-sign or move anything.

## Examples

### every binary signed by the expected identity
input: {"bundle": "fixtures/Signed.app", "identity": "Developer ID Application"}
output: {"ok": true, "checked": [".", "Contents/MacOS/Signed", "Contents/MacOS/helper"], "offenders": []}

### one unsigned sidecar
input: {"bundle": "fixtures/Broken.app"}
output: {"ok": false, "checked": [".", "Contents/MacOS/Broken", "Contents/MacOS/helper"], "offenders": [{"path": "Contents/MacOS/helper", "reason": "code object is not signed at all"}]}

### signed, but by the wrong identity
input: {"bundle": "fixtures/AdHoc.app", "identity": "Developer ID Application"}
output: {"ok": false, "checked": [".", "Contents/MacOS/AdHoc"], "offenders": [{"path": ".", "reason": "signed by 'adhoc', expected 'Developer ID Application'"}]}
