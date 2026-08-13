---
name: storekit-sandbox-testing
description: Get from "purchases work in Xcode" to "purchases work on a device with a real
  Apple ID" — the two testing worlds StoreKit has, and how to avoid mistaking one for the
  other. Use when working with storekit or xcode on macos or ios, or when the user mentions
  sandbox, testing, iap or purchases.
license: MIT
compatibility: Requires Xcode and App Store Connect access
metadata:
  speccify.version: 1.0.0
  speccify.scope: speccify
  speccify.stack: storekit, xcode
  speccify.platforms: macos, ios
---

## Prerequisites

- An app with at least one in-app purchase product in the code
- App Store Connect access with the Admin or App Manager role

## 1 — Test locally with a StoreKit configuration file

A `.storekit` file lets you buy, refund and fail transactions **without
App Store Connect and without a network** — the fastest loop by far.

Add it to the scheme: *Edit Scheme → Run → Options → StoreKit
Configuration*. Without that selection the file is inert and your app
silently talks to the real store instead.

In the editor (or the JSON) you can force failures and ask for
"Ask to Buy" — both are worth exercising before shipping.

**Verify:** The paywall shows the product's localized price while offline.

*Source: Setting up StoreKit testing in Xcode.*

## 2 — Create a sandbox tester in App Store Connect

*Users and Access → Sandbox → Test Accounts*. Use an email address you
control but have **never** used as a real Apple ID — an address that is
already an Apple ID cannot become a sandbox tester.

Do **not** sign into iCloud with a sandbox account. It belongs in the
store sign-in only, and signing into iCloud with it can wedge the device.

**Verify:** The tester appears in the list with the intended storefront country.

*Source: Testing at all stages of development with Xcode and the sandbox.*

## 3 — Sign the device into the sandbox account

- **iOS:** Settings → App Store → *Sandbox Account* (bottom of the page).
  This is separate from the account used for real purchases.
- **macOS:** there is no sandbox slot. The first sandbox purchase prompts
  for credentials — enter the tester there.

A build installed from Xcode or TestFlight uses the sandbox; a build from
the App Store does not.

**Verify:** A purchase in the app shows the "[Environment: Sandbox]" hint in the dialog.

*Source: Testing at all stages of development with Xcode and the sandbox.*

## 4 — Know that sandbox time is compressed

For **subscriptions**, sandbox renewals run on a compressed clock: a
monthly subscription renews in minutes, a yearly one in about an hour,
and a free trial shrinks accordingly. Plan tests around that instead of
waiting.

For **non-consumables** this does not apply — but if you built your own
trial period, the sandbox will *not* compress it. Your own clock is your
own problem; test it by injecting dates, not by waiting seven days.

**Verify:** A subscription renewal (or your own trial expiry) can be observed within one test session.

*Source: Testing at all stages of development with Xcode and the sandbox.*

## Pitfalls

- A StoreKit configuration file that is not selected in the scheme does nothing — and the failure looks like "products not found".
- An email address that is already an Apple ID cannot become a sandbox tester.
- Never sign into iCloud with a sandbox tester; it belongs in the store sign-in only.
- Products only load once they exist *and* the paid-applications agreement is active — an unsigned agreement produces an empty product list with no error.

## Acceptance

- Given a sandbox tester signed in on a device, when the app offers the product and the tester buys it, then the purchase completes and the entitlement is visible after a relaunch.

## Sources

- [Setting up StoreKit testing in Xcode](https://developer.apple.com/documentation/xcode/setting-up-storekit-testing-in-xcode) — retrieved 2026-08-06
  StoreKit configuration files and the scheme option that activates them.
- [Testing at all stages of development with Xcode and the sandbox](https://developer.apple.com/documentation/storekit/testing-at-all-stages-of-development-with-xcode-and-the-sandbox) — retrieved 2026-08-06
  Sandbox testers, device setup and the compressed renewal clock.
