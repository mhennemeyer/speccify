---
name: iap-trial-then-unlock
description: Ship an app that is free to try for seven days and then costs one payment — from
  the App Store Connect product to a trial clock that survives reinstalls, new devices and
  a rewound system clock. Use when working with storekit on macos or ios, or when the user
  mentions iap, trial, non-consumable, paywall or universal-purchase.
license: MIT
compatibility: Requires Xcode >= 16, Apple Developer Program and StoreKit 2 (iOS 15 / macOS
  12+)
metadata:
  speccify.version: 1.0.0
  speccify.scope: speccify
  speccify.stack: storekit
  speccify.platforms: macos, ios
  speccify.uses: '@speccify/storekit-sandbox-testing@^1.0'
---

## Prerequisites

- An app record exists in App Store Connect
- The paid applications agreement is active — without it products never load
- You have decided what the app does *after* the trial (see the first step)

## 1 — Decide the trial model — Apple does not give you one

This is the fork that decides everything after it. **StoreKit runs a free
trial for you only through an introductory offer — and those exist only
for subscriptions.** A non-consumable "buy once" product cannot have one,
so nothing in the StoreKit API will count your seven days.

Three routes:

1. **Subscription with an introductory offer.** Apple runs the clock, but
   the user rents rather than owns, and you inherit renewals, grace
   periods and billing retry.
2. **Free app + non-consumable unlock + your own trial clock.**
   You own the clock, the user owns the app. Everything below takes this
   route.
3. **Apple's formal trial for non-subscription apps** (guideline 3.1.1):
   a Non-Consumable at **price tier 0** named `"XX-day Trial"`. This is
   still *your* clock — the tier-0 product exists so the trial is visible
   in the store listing, not because Apple counts the days. Route 2 plus
   this product is the compliant shape when you advertise a trial.

Whatever you pick, guideline 3.1.1 requires that **before** the trial
starts you state its duration, what stops working afterwards, and what
full use costs. And guideline 2.2 keeps demos and trial *versions* off
the store entirely — so the app after day 7 must still be a real app
(see `gate_access`), not a locked shell.

**Verify:** You can say in one sentence what the app does on day 8 without a purchase — and the app says it before day 1.

*Source: App Review Guidelines — In-App Purchase or Introductory offers.*

## 2 — Create the non-consumable product in App Store Connect

*Monetization → In-App Purchases → +* → **Non-Consumable**.

The product ID is permanent — it can never be reused, even after you
delete the product. Two things bite here:

- It may only contain **letters, digits, underscores and dots**. If your
  bundle ID has a hyphen (`com.better-apps.thing`), the product ID cannot
  mirror it — pick something like `com.betterapps.thing.pro` and write
  down why the two differ.
- Enable **Universal Purchase** if Mac and iOS share the bundle ID; one
  purchase then unlocks every platform.

Fill in a localized display name and description for each language you
ship — they appear in the system purchase sheet, not just in the store.

If you advertise the trial in the listing, add the second product
guideline 3.1.1 asks for: another Non-Consumable at **price tier 0**,
named exactly `"7-day Trial"` (`XX-day Trial`). It sells nothing — it
makes the trial visible and keeps review happy.

**Verify:** The product shows up in App Store Connect with status "Ready to Submit".

*Source: In-app purchase types, Create in-app purchases, Add platforms (universal purchase across macOS and iOS) or App Review Guidelines — In-App Purchase.*

## 3 — Add a StoreKit configuration file for local testing

A `.storekit` file mirrors the product locally so the paywall works with
no network and no App Store Connect round trip. Add it to the run scheme
(*Edit Scheme → Run → Options → StoreKit Configuration*) — an
unselected file does nothing, and the symptom looks like "products not
found".

The bundled asset is a minimal starting point: one non-consumable, one
locale. Keep the product ID identical to App Store Connect.

**Verify:** The paywall shows a localized price while the machine is offline.

*Source: Setting up StoreKit testing in Xcode.*

## 4 — Wire up StoreKit 2 — entitlements, purchase, restore

Four things matter, and three of them are ordering problems:

1. **Subscribe to `Transaction.updates` before checking entitlements.**
   A transaction that arrives during startup is otherwise dropped.
2. **Read `Transaction.currentEntitlements` on every launch**, not just
   after a purchase — the purchase may have happened on another device.
3. **Ignore unverified results.** `VerificationResult` is the signature
   check; acting on `.unverified` defeats it.
4. **`.pending` is not a failure.** Under Ask to Buy or Family Sharing
   the purchase completes later through `Transaction.updates`. Telling
   the user "purchase failed" here is simply wrong.

Always `await transaction.finish()` once you have granted the
entitlement, and offer a **Restore Purchases** button that calls
`AppStore.sync()` — App Review requires it for non-consumables.

**Verify:** A fresh install of a purchased account unlocks after launch without any user action.

*Source: StoreKit Transaction, AppStore.sync() or App Review Guidelines — In-App Purchase.*

## 5 — Compute the trial with a high-water mark

The naive version — `start + 7 days < now` — is defeated by setting the
clock back. Keep the **highest time ever observed** alongside the start
date and compute against `max(now, highWaterMark)`:

```swift
func effectiveDate(_ now: Date) -> Date { max(now, highWaterMark) }
func remaining(at now: Date) -> TimeInterval {
    max(0, end.timeIntervalSince(effectiveDate(now)))
}
```

Deliberately *not* punished: a user whose clock is wrong for innocent
reasons loses nothing, they just gain no extra days. Rounding matters
too — round remaining days **up**, so the last day reads "1 day left"
rather than "0 days left".

Keep this logic free of StoreKit so it is testable without a store
environment.

**Verify:** A unit test that moves the clock backwards does not extend the trial.

## 6 — Store the start date where deleting the app cannot reach

This is the actual problem of a self-built trial. No single store has all
the properties you need, so use several and merge them — **the earliest
known start wins**:

| Store | Survives | Fails at |
|---|---|---|
| `UserDefaults` | device backups, migration to a new device | app deletion |
| Keychain | app deletion on the same device | a fresh device |
| `NSUbiquitousKeyValueStore` (iCloud) | every device on one Apple ID | no iCloud account |
| DeviceCheck | even a factory reset (two bits, held by Apple) | needs a server, and it is per device |

Two devices without the iCloud store means seven days *each*; app
deletion without the Keychain means seven days *again*.

**Pick two, deliberately:**

- **Keychain + `UserDefaults`** — the minimum. Survives deletion and
  rides along in a backup. No iCloud dependency.
- **iCloud + `UserDefaults`** — when the app already uses iCloud, and one
  trial across the user's devices matters more than a reinstall on one.
- Add the Keychain *and* iCloud only if both properties actually matter
  to you; three stores is not a badge, it is three things to reconcile.
- **DeviceCheck** is the only store a determined user cannot clear, and
  guideline 3.1.1 points at it — but it needs a server and an Apple key.
  Worth it when the trial guards something expensive; overkill for a
  productivity tool.

Whatever you pick: write to all of them, read the **union**, and
reconcile. If one store knows the start and another does not, backfill
it — otherwise the next device starts fresh.

Put the stores behind a protocol. `NSUbiquitousKeyValueStore` cannot be
faked otherwise, and this is exactly the code that decides between "seven
days total" and "seven days per device".

**Verify:** Deleting and reinstalling the app on the same device does not reset the remaining days.

*Source: DeviceCheck or App Review Guidelines — In-App Purchase.*

## 7 — Derive access, and degrade instead of locking out

Resolve access from two inputs and nothing else:

```swift
static func resolve(isPurchased: Bool, trial: TrialState?, now: Date) -> Access {
    if isPurchased { return .purchased }        // a purchase always wins
    if let trial, trial.isActive(at: now) { return .trial(until: trial.end) }
    return .expired
}
```

A purchase must beat an expired trial, or a paying user lands in the
locked state — an embarrassing bug that only appears after seven days.

After expiry, prefer **read-only over unusable** — for two reasons that
point the same way. The user's data belongs to the user: block creating
new content, keep viewing, renaming, exporting and deleting. And
guideline 2.2 keeps "demos, betas and trial versions" off the store, so
an app that turns into a locked shell after seven days invites exactly
that objection. A capable app with one capability behind a purchase does
not.

**Verify:** With an expired trial the app still opens existing content and only blocks creation.

*Source: App Review Guidelines — In-App Purchase.*

## 8 — If the app used to be paid, keep those buyers unlocked

Switching a paid app to "free plus IAP" must not charge existing buyers
again. `AppTransaction.originalAppVersion` tells you which version a user
originally downloaded — compare it against **the last build you shipped
while the app still cost money**.

That number is not derived, you look it up once: App Store Connect →
your app → the version history shows every released version; take the
build number (`CFBundleVersion`) of the last paid release and freeze it
in the code with a comment saying which marketing version it was.

```swift
/// Last build sold as a paid app (marketing version 1.1.0).
static let lastPaidBuild = 4

static func isGrandfathered(originalAppVersion: String) -> Bool {
    guard let build = Int(originalAppVersion.prefix(while: \.isNumber)) else { return false }
    return build <= lastPaidBuild
}
```

```swift
guard case .verified(let appTransaction)? = try? await AppTransaction.shared,
      isGrandfathered(originalAppVersion: appTransaction.originalAppVersion)
else { return }
```

Two traps: on iOS `originalAppVersion` is the **build number**
(`CFBundleVersion`), not the marketing version — parse it as such. And in
sandbox it reports `"1.0"`, which unlocks everything and makes the paywall
untestable; gate that check behind a launch argument in debug builds.

Cache the result so a later launch does not depend on the store.

**Verify:** A sandbox run without the debug flag still shows the paywall.

*Source: AppTransaction.originalAppVersion or App information (version history, where the last paid build number is).*

## 9 — Test against the StoreKit file first, then the sandbox

Covered by the skill `@speccify/storekit-sandbox-testing@^1.0` — follow that one, then continue.

## Pitfalls

- StoreKit only runs a free trial through an introductory offer, and those are subscription-only. For "try then own" you build the clock yourself — Apple's tier-0 "XX-day Trial" product makes it visible, it does not count the days.
- Guideline 3.1.1 wants the trial's duration, its consequences and the eventual price stated *before* it starts; guideline 2.2 rejects apps that are merely trial versions.
- Product IDs allow no hyphens, so they often cannot mirror a hyphenated bundle ID. They are also permanent.
- Storing the trial start only in UserDefaults means deleting the app resets it; only in the Keychain means a new device starts over; only in iCloud means no trial without an iCloud account.
- Checking entitlements before subscribing to `Transaction.updates` drops purchases that land during startup.
- Treating `.pending` as a failure tells Ask-to-Buy users their purchase broke when it is merely waiting.
- Letting an expired trial outrank a purchase locks out paying users — and only shows up a week after release.
- `AppTransaction.originalAppVersion` reports "1.0" in sandbox, which silently unlocks everything unless the check is gated in debug builds.
- The grandfathering threshold is a build number you look up once in App Store Connect, not something you can compute — write down which marketing version it was.
- Products load as an empty list — with no error — while the paid applications agreement is unsigned.

## Acceptance

- Given a fresh install with no purchase, when the app launches for the first time, then it reports seven days remaining and allows full use.
- Given an expired trial and no purchase, when the app launches, then existing content stays usable and only creation is blocked.
- Given a purchase made on another device with the same Apple ID, when the app launches, then it unlocks without any user action.
- Given an expired trial on a device whose clock is set back one year, when the app launches, then the trial stays expired.

## Sources

- [In-app purchase types](https://developer.apple.com/help/app-store-connect/reference/in-app-purchase-types) — retrieved 2026-08-06
  Which product types exist, and which can carry offers.
- [Introductory offers](https://developer.apple.com/documentation/storekit/product/subscriptioninfo/introductoryoffer) — retrieved 2026-08-06
  Free trials are subscription offers — the reason a self-built clock is needed.
- [Create in-app purchases](https://developer.apple.com/help/app-store-connect/manage-in-app-purchases/create-consumable-or-non-consumable-in-app-purchases) — retrieved 2026-08-06
  Product ID rules and the permanence of the identifier.
- [Add platforms (universal purchase across macOS and iOS)](https://developer.apple.com/help/app-store-connect/create-an-app-record/add-platforms/) — retrieved 2026-08-06
  One app record with several platforms is what makes a single purchase unlock both. Separate records cannot be merged afterwards. (Replaced the former `reference/universal-purchase` page, which Apple removed — it answered 200 with a "Page Not Found" body.)
- [Setting up StoreKit testing in Xcode](https://developer.apple.com/documentation/xcode/setting-up-storekit-testing-in-xcode) — retrieved 2026-08-06
- [StoreKit Transaction](https://developer.apple.com/documentation/storekit/transaction) — retrieved 2026-08-06
  currentEntitlements, updates, finish() and VerificationResult.
- [AppStore.sync()](https://developer.apple.com/documentation/storekit/appstore/sync()) — retrieved 2026-08-06
  What "Restore Purchases" has to call.
- [App Review Guidelines — In-App Purchase](https://developer.apple.com/app-store/review/guidelines/) — retrieved 2026-08-06
  3.1.1 — restore mechanism required; also the tier-0 "XX-day Trial" product and the duty to state duration and consequences up front. 2.2 — demos and trial versions do not belong on the App Store.
- [DeviceCheck](https://developer.apple.com/documentation/devicecheck) — retrieved 2026-08-06
  Two bits per device, held by Apple — survives reinstalls and resets, needs a server.
- [App information (version history, where the last paid build number is)](https://developer.apple.com/help/app-store-connect/reference/app-information/) — retrieved 2026-08-06
  Where to read the build number of the last paid release.
- [AppTransaction.originalAppVersion](https://developer.apple.com/documentation/storekit/apptransaction/originalappversion) — retrieved 2026-08-06
  Build number on iOS, marketing version on macOS — and "1.0" in sandbox.
