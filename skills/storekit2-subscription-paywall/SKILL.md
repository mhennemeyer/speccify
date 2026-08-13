---
name: storekit2-subscription-paywall
description: 'Free tier plus a Pro subscription with a free trial: the product id that must
  match in three places, what a subscription group irreversibly decides, the StoreKit 2 listener
  that has to run before anyone buys anything, and the disclosures App Review checks. Use
  when working with storekit on macos or ios, or when the user mentions subscription, paywall,
  free-trial, introductory-offer or app-review.'
license: MIT
compatibility: Requires App Store Connect access, Xcode and A paid Apple Developer Program
  membership
metadata:
  speccify.version: 1.0.0
  speccify.scope: speccify
  speccify.stack: storekit
  speccify.platforms: macos, ios
  speccify.uses: '@speccify/storekit-sandbox-testing@^1.0'
---

## Prerequisites

- The app id exists under your team and the app record exists in App Store Connect.
- You have decided which features are free. A paywall in front of everything is a different (worse) product.

## 1 — Pin the product id in three places at once

The product id appears in your code, in the local `.storekit`
configuration, and in App Store Connect. If any two disagree, the
product simply does not load — no error, no crash, just a paywall
saying it has nothing to sell. That symptom sends people debugging
StoreKit for an afternoon; the cause is a typo.

Put the ids in **one** constant in code and treat the other two as
copies of it:

```swift
public enum SubscriptionProduct {
    public static let proMonthly = "com.example.myapp.pro.monthly"
    public static let allProIDs: Set<String> = [proMonthly]
}
```

Write down, next to that constant, that changing it means changing the
`.storekit` file and App Store Connect too. Ids cannot be renamed in
App Store Connect once created, only replaced — so get it right rather
than clever.

The attached `Pro.storekit` is a working configuration for exactly this
shape — one group, one monthly subscription, a one-week free trial. Add
it to the scheme (Run → Options → StoreKit Configuration) and the app
buys against it locally, with no App Store Connect involved.

**Verify:** Change the id in code only, run, and confirm the paywall goes empty. Now you know the failure mode by sight.

## 2 — Understand what a subscription group decides — permanently

A subscription group is not a folder. It carries two rules that outlive
any single product:

* A customer holds **at most one active subscription per group**.
  Moving between products in the same group is an upgrade, downgrade or
  crossgrade, handled by the App Store. Products in *different* groups
  can be held simultaneously, which is almost never what you want.
* **One introductory offer per customer per group — ever.** Apple is
  explicit:

  > If a customer uses a free trial and then upgrades to a subscription
  > product in the same group that also has a free trial, they aren't
  > eligible for the second offer.

So a single group with monthly and yearly in it means: trial once,
switching tiers is a change rather than a new purchase. That is usually
right. Splitting them into separate groups to hand out a second trial
also lets a user hold both at once — a support problem you build for
yourself.

Start with one group and one product. Adding a yearly plan later is
easy; unpicking two groups is not.

**Verify:** The group contains every plan a user should be able to switch between, and nothing they should be able to hold simultaneously.

*Source: App Store Connect Help — Set up introductory offers for auto-renewable subscriptions or App Store Connect Help — In-app purchase types.*

## 3 — Create the subscription and its introductory offer

In App Store Connect, on the app: Subscriptions → create the group →
create the auto-renewable subscription. You need the product id (exactly
as in code), a reference name, a duration, and a price.

Then the introductory offer. Three types exist — **free trial**, **pay
up front**, **pay as you go** — and the durations available depend on
the subscription's own duration. A seven-day trial on a monthly
subscription is the "1 week" free-trial option.

Two things worth knowing before you click:

* **Introductory offers cannot be edited.** To change one you delete it
  and create a new one. Set the duration deliberately.
* You can schedule a current and a future offer per storefront, which is
  how you change terms later without editing anything.

Also fill in: localised display name and description, the review
screenshot of your paywall, and a review note. A subscription is
reviewed alongside the build.

**Verify:** The product shows "Ready to Submit" in App Store Connect and its id matches the constant in code byte for byte.

*Source: App Store Connect Help — Set up introductory offers for auto-renewable subscriptions.*

## 4 — Start the transaction listener at launch, not at purchase

`Transaction.updates` delivers transactions that happen **outside** a
purchase call: a renewal, a purchase approved later under Ask to Buy, a
purchase that was interrupted, one made on another device. If you only
start listening while a purchase is in flight, those arrive to nobody
and the user has paid for something your app does not know about.

Start it once at app launch, and make it idempotent so a second call
does not create a second listener:

```swift
public func start() {
    if updatesTask == nil { updatesTask = listenForTransactions() }
    Task { await loadProducts(); await refreshEntitlements() }
}

private func listenForTransactions() -> Task<Void, Never> {
    Task { [weak self] in
        for await result in Transaction.updates {
            guard case .verified(let transaction) = result else { continue }
            await transaction.finish()
            await self?.refreshEntitlements()
        }
    }
}
```

Two rules inside that loop: ignore anything not `.verified` — an
unverified transaction is exactly what someone tampering would produce —
and call `finish()` once you have granted access, or the transaction is
redelivered forever.

**Verify:** Buy in the sandbox, force-quit before the purchase sheet finishes, relaunch — access is granted without any user action.

*Source: Apple Developer — StoreKit Transaction (updates, currentEntitlements).*

## 5 — Derive access from currentEntitlements, with the three filters

`Transaction.currentEntitlements` is the source of truth for what the
user is allowed to use right now. Iterate it on launch and after every
transaction, and apply three filters that are easy to forget:

```swift
for await result in Transaction.currentEntitlements {
    guard case .verified(let t) = result else { continue }
    guard t.revocationDate == nil else { continue }   // refunded
    guard !t.isUpgraded else { continue }             // superseded by a higher tier
    if let expiry = t.expirationDate, expiry <= Date() { continue }
    active.insert(t.productID)
}
```

* `revocationDate` — a refunded purchase still appears; access must stop.
* `isUpgraded` — after an upgrade the old transaction lingers; counting
  it double-counts the subscription.
* `expirationDate` — a lapsed subscription can still be listed.

Never cache the result across launches in a way that survives without
re-checking. A locally stored "user is Pro" flag is the one thing every
cracking guide starts with.

**Verify:** Cancel and let it lapse in the sandbox - the app returns to the free tier on the next launch without a reinstall.

*Source: Apple Developer — StoreKit Transaction (updates, currentEntitlements).*

## 6 — Keep the tier decision free of StoreKit

The rule "which product ids mean Pro" is business logic and deserves a
test. `Product` and `Transaction` cannot be constructed in a unit test,
so keep them out of the decision:

```swift
public enum SubscriptionTier {
    public static func tier(activeProductIDs: Set<String>,
                            proProductIDs: Set<String>) -> Tier {
        activeProductIDs.isDisjoint(with: proProductIDs) ? .free : .pro
    }
}
```

The StoreKit-facing store collects ids; this function decides. Now the
interesting cases — an unknown id, several active, an id that used to be
Pro — are testable headlessly, and the untested part is reduced to
plumbing.

Same for display: format the price, period and trial text from plain
values, so the paywall's wording is testable without a store.

**Verify:** The tier tests run in a plain `swift test` with no StoreKit configuration present.

## 7 — Put the disclosures on the paywall, because review checks them

Guideline 3.1.2(c) requires you to say clearly what the user gets for
the price, and to meet the disclosure requirements of Schedule 2 of the
Program License Agreement. In practice, visible on the purchase screen,
before the buy button:

* what the subscription unlocks,
* the **duration** of the period,
* the **price** per period (and, with a trial, what happens when it
  ends — "free for 7 days, then €4.99 per month"),
* that it renews automatically until cancelled, and how to cancel.

Plus two links that must actually work: **Terms of Use (EULA)** — the
standard Apple EULA is acceptable — and your **privacy policy**. Reviewers
click them. A placeholder URL is a rejection, and it is the single most
common one here.

Take the price and period from the loaded `Product` (`displayPrice`,
`subscription?.subscriptionPeriod`, `introductoryOffer`) rather than
hardcoding them — hardcoded prices are wrong in every other storefront.

**Verify:** Open the paywall in a non-Euro storefront - price, period and trial text all follow the storefront, and both legal links open a real page.

*Source: App Store Review Guidelines — 3.1.1 (restore mechanism) and 3.1.2 (subscriptions).*

## 8 — Give it a Restore button

A restore mechanism is required for restorable purchases:

> you should make sure you have a restore mechanism for any restorable
> in-app purchases

With StoreKit 2 this is `AppStore.sync()` followed by re-reading
entitlements. It is rarely needed — `currentEntitlements` already spans
the user's devices — but reviewers look for the button, and the case
where it matters (a fresh install on a second machine that has not
synced yet) is real.

Put it on the paywall, plainly labelled, and let it report "nothing to
restore" rather than failing silently.

**Verify:** On a second machine with a fresh install, Restore grants Pro; on an account without a subscription it says so and leaves the tier at free.

*Source: App Store Review Guidelines — 3.1.1 (restore mechanism) and 3.1.2 (subscriptions) or Apple Developer — AppStore.sync().*

## 9 — Test locally against a .storekit file, then in the sandbox

Covered by the skill `@speccify/storekit-sandbox-testing@^1.0` — follow that one, then continue.

## 10 — Make the "no products" state say something useful

Products fail to load more often than anything else in this feature:
ids out of sync, the product not yet approved in App Store Connect, no
network, the paid-apps agreement not signed, or a build whose bundle id
does not match the app record.

Whatever the cause, the user sees an empty paywall. Give that state a
real message ("Subscriptions aren't available right now") plus a retry,
and log the underlying error where you can find it.

The one thing not to do is hide the paywall when nothing loaded — then
the locked features look broken instead of locked.

**Verify:** With an intentionally wrong product id, the paywall shows the message and a retry rather than an empty list.

## Pitfalls

- Starting the transaction listener when the purchase begins. Renewals and Ask-to-Buy approvals then land nowhere, and the user pays without getting access.
- Forgetting `revocationDate` or `isUpgraded` when reading entitlements — refunded users keep access, upgraded ones get counted twice.
- Calling `finish()` before granting access, or never calling it. The first loses purchases, the second replays them forever.
- Hardcoded prices on the paywall. Wrong in every storefront but yours, and a guideline problem when they disagree with the store.
- Placeholder EULA or privacy URLs at submission. The most common rejection reason in this area, and the cheapest to avoid.
- Splitting plans into separate subscription groups to hand out a second free trial. It also lets one customer hold both plans at once.
- Storing "is Pro" in UserDefaults as the source of truth. Re-derive from `currentEntitlements`; the local flag is only a cache for the UI.

## Acceptance

- Given A fresh install on an account with no subscription, when The user opens a locked feature, then The paywall shows price, period, trial terms, working legal links and a restore button.
- Given A subscriber who cancels and lets the period lapse, when They relaunch the app, then The app returns to the free tier without a reinstall, and locked features show the paywall again.

## Sources

- [App Store Review Guidelines — 3.1.1 (restore mechanism) and 3.1.2 (subscriptions)](https://developer.apple.com/app-store/review/guidelines/) — retrieved 2026-08-06
  3.1.2(c) requires clearly describing what the customer gets for the price and meeting Schedule 2 disclosure requirements; 3.1.1 requires a restore mechanism for restorable purchases.
- [App Store Connect Help — Set up introductory offers for auto-renewable subscriptions](https://developer.apple.com/help/app-store-connect/manage-subscriptions/set-up-introductory-offers-for-auto-renewable-subscriptions/) — retrieved 2026-08-06
  Three offer types; one introductory offer per customer per subscription group, including after an upgrade; offers cannot be edited after creation.
- [App Store Connect Help — In-app purchase types](https://developer.apple.com/help/app-store-connect/reference/in-app-purchase-types) — retrieved 2026-08-06
  Definitions of consumable, non-consumable, auto-renewable and non-renewing subscriptions.
- [Apple Developer — StoreKit Transaction (updates, currentEntitlements)](https://developer.apple.com/documentation/storekit/transaction) — retrieved 2026-08-06
  API reference. The page renders client-side and could not be quoted here; the behaviour described in this playbook is from a shipping implementation and should be re-checked against the reference when it changes.
- [Apple Developer — AppStore.sync()](https://developer.apple.com/documentation/storekit/appstore/sync()) — retrieved 2026-08-06
