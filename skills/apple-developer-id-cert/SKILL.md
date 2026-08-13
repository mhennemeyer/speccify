---
name: apple-developer-id-cert
description: Create a Developer ID Application certificate in the Apple Developer portal and
  install it so that `codesign` can find it. Ends with a verified signing identity on the
  machine. Use when targeting macos, or when the user mentions codesign, certificate, keychain,
  developer-id or notarization.
license: MIT
compatibility: Requires Apple Developer Program membership and Keychain Access
metadata:
  speccify.version: 1.0.0
  speccify.scope: speccify
  speccify.platforms: macos
---

## Prerequisites

- Apple Developer Program membership (individual or organisation)
- Account holder or admin role — members cannot create Developer ID certificates

## 1 — Create a certificate signing request

In Keychain Access: *Certificate Assistant → Request a Certificate From a
Certificate Authority*. Enter your Apple ID email, leave the CA field at
its default, and choose **Saved to disk** plus *Let me specify key pair
information* (2048 bit, RSA).

Keep the private key in the login keychain — the certificate you download
later is useless without it.

**Verify:** A `.certSigningRequest` file exists and a new private key appears in the login keychain.

## 2 — Request a Developer ID Application certificate

In the developer portal under *Certificates → +*, pick **Developer ID
Application** (not *Mac App Distribution* — that one only works for the
Mac App Store and cannot notarize direct downloads). Upload the CSR and
download the resulting `.cer`.

**Verify:** The downloaded certificate is of type "Developer ID Application".

*Source: Create Developer ID certificates.*

## 3 — Install the certificate and verify the identity

Double-click the `.cer` to add it to the login keychain, then confirm that
signing will find it:

```bash
security find-identity -v -p codesigning
```

The output must contain a line `"Developer ID Application: <name> (TEAMID)"`.
That exact string is what build scripts pass to `codesign --sign`.

**Verify:** `security find-identity -v -p codesigning` lists a valid "Developer ID Application" identity.

## Pitfalls

- Only the Account Holder can create Developer ID certificates; admins and members cannot.
- A certificate without its private key is worthless — export both together as `.p12` when moving machines.
- Mac App Distribution certificates look similar but cannot notarize software distributed outside the App Store.

## Acceptance

- Given a machine with the certificate installed, when `security find-identity -v -p codesigning` runs, then a "Developer ID Application" identity is listed as valid.

## Sources

- [Create Developer ID certificates](https://developer.apple.com/help/account/create-certificates/create-developer-id-certificates) — retrieved 2026-08-06
  Explains the role requirement and the certificate types.
