---
name: icloud-container-mac-ios
description: 'Two apps, two bundle ids, one iCloud container: entitlements on both sides,
  the portal registration nobody documents, and the four runtime rules that decide whether
  this works or corrupts data — resolve off the main thread, coordinate every read and write,
  resolve conflicts yourself, and never require the other device to be awake. Use when working
  with swift on macos or ios, or when the user mentions icloud, ubiquity-container, clouddocuments,
  nsfilecoordinator, nsfileversion, entitlements or companion-app.'
license: MIT
compatibility: Requires Apple Developer Program membership and Both apps under the same team
metadata:
  speccify.version: 1.0.0
  speccify.scope: speccify
  speccify.stack: swift
  speccify.platforms: macos, ios
---

## Prerequisites

- Both apps live under the same developer team. A shared container across teams is not a thing.
- Decide what the shared data *is* before wiring anything — see the first step.

## 1 — Decide what crosses the wire, and who writes it

The design decision comes before any entitlement, and it is the one that
determines whether the companion is useful.

The tempting shape is: the companion leaves a *command* and the main app
carries it out. It is easy to build, and it is useless — because the
whole point of a phone companion is that the Mac is closed. If an answer
only takes effect once the Mac wakes up, the user might as well have
waited.

So: **the companion writes the final state directly**, into the same
files the other side reads. That forces two consequences you should
accept up front:

* Both sides are writers, so you need real conflict handling (later
  steps), not an owner/follower shortcut.
* The file format has to be readable and writable by both — no
  Mac-only frameworks in the storage layer.

Also decide what stays local. Not every project needs to be in iCloud;
a per-project opt-in ("move to iCloud") is honest and keeps the blast
radius small.

**Verify:** Write down which side writes which fields. If the answer is "one side only", re-check whether the companion is worth building.

## 2 — Put the same container id in both apps' entitlements

Three keys, identical in both targets — the Mac app and the iOS app.
The container id is **one** string used by both; it is not derived from
the bundle id, and the two apps do **not** get one each:

```xml
<key>com.apple.developer.icloud-container-identifiers</key>
<array><string>iCloud.com.example.myapp</string></array>

<key>com.apple.developer.ubiquity-container-identifiers</key>
<array><string>iCloud.com.example.myapp</string></array>

<key>com.apple.developer.icloud-services</key>
<array><string>CloudDocuments</string></array>
```

`CloudDocuments` is the service for documents in iCloud Drive — that is
what you want for files two apps share. (CloudKit is a different
product with a different API; picking it here means rewriting the
storage layer.)

The Mac app additionally needs its sandbox entitlements; iCloud does
not replace them.

**Verify:** `codesign -d --entitlements - YourApp.app` shows the same container id as the iOS build.

## 3 — Register the container and hang it on both app ids

The entitlements are a request; the portal decides whether it is
granted. Until the container exists **and** both app ids carry the
iCloud capability pointing at it, iCloud stays silently inactive at
runtime — no crash, no error, just an app that never sees the container.

**Fast path (Xcode):** open each target → Signing & Capabilities → set
the team, enable automatic signing, and under iCloud Documents tick the
container (or create it with "+"). Confirm the "Register/Create"
prompts. Xcode creates the container and updates both app ids and the
profiles.

**Manual path (developer.apple.com → Certificates, Identifiers &
Profiles):**

1. Identifiers → filter **iCloud Containers** → "+" → id
   `iCloud.com.example.myapp` → Register.
2. The Mac app id → edit → enable iCloud → Configure → assign the
   container → Save.
3. The iOS app id → same container. Create the app id first if the
   companion is new.
4. Regenerate provisioning profiles if you sign manually.

If your `.xcodeproj` is generated (xcodegen and friends), remember that
UI changes to the project are lost on regeneration — but the **portal**
registration is not. Using Xcode here is a convenient way to create
portal entries, nothing more.

**Verify:** The container appears under Identifiers -> iCloud Containers, and both app ids list it under their iCloud capability.

*Source: Apple (archive) — iCloud Design Guide: iCloud Fundamentals.*

## 4 — Resolve the container off the main thread — always

This is documented and still gets ignored, because on a warm machine it
returns instantly and only hangs for other people:

> Always call the `URLForUbiquityContainerIdentifier:` method from a
> background thread—not from your app's main thread. This method depends
> on local and remote services and, for this reason, does not always
> return immediately.

In Swift, that means never calling it inside a SwiftUI `body`, a view
model's `init`, or anything `@MainActor` that runs at launch. Resolve it
once, off the main actor, cache the URL, and publish availability back
to the UI.

A `nil` return is not an error to show: it means document storage is not
available — no account, iCloud Drive off, or the capability was never
granted. Treat it as a state, not a failure.

**Verify:** Launch with iCloud signed out and with a cold container. The UI must stay responsive and show an "unavailable" state.

*Source: Apple (archive) — iCloud Design Guide: iCloud Fundamentals.*

## 5 — Make the container injectable, or you cannot test any of this

`FileManager.url(forUbiquityContainerIdentifier:)` needs an entitlement,
a signed-in account and a network. None of that belongs in a unit test.

Wrap the resolver in a closure with a production default:

```swift
public struct ICloudContainer: Sendable {
    private let resolveURL: @Sendable () -> URL?

    public init(resolveURL: @escaping @Sendable () -> URL? = {
        FileManager.default.url(forUbiquityContainerIdentifier: containerID)
    }) { self.resolveURL = resolveURL }

    public var isAvailable: Bool { resolveURL() != nil }
    public func documentsURL() -> URL? {
        resolveURL()?.appendingPathComponent("Documents", isDirectory: true)
    }
}
```

Tests hand in a `tmp` directory and exercise the entire layout, layering
and conflict logic without iCloud existing. The one thing this does not
test is iCloud itself — which is exactly what the device smoke test at
the end is for.

Note the `Documents` subdirectory: only what lives under it appears in
iCloud Drive for the user. Files directly in the container root sync but
stay invisible, which is either what you want or a bug you will spend an
hour on.

**Verify:** The storage tests pass on a machine signed out of iCloud.

## 6 — Fall back to local storage, and make the switch explicit

Most of the time iCloud is available. The interesting paths are the
others: never enabled, signed out mid-session, or the user declined.

Have one place that answers "where does this project's data live?" and
returns either the container path or the local one. Everything else asks
that, so the fallback is a single decision rather than a `if iCloud`
scattered through the code.

Make the migration a deliberate user action ("Move to iCloud"), not
something that happens silently on first launch. Silently moving a
user's files into a sync folder is the kind of surprise that produces
support mail about "my data disappeared".

**Verify:** Toggle iCloud off in system settings mid-session — the app keeps working against local storage and says which mode it is in.

## 7 — Route every read and write through NSFileCoordinator

Two devices writing the same file is exactly the case the file system
does not handle for you:

> Because the file system is shared by all running processes, problems
> can occur when two processes […] try to act on the same file at the
> same time. […] two threads acting on the file simultaneously can
> corrupt it and render it unusable.

So do not call `Data(contentsOf:)` and `write(to:)` directly on anything
in the container. Wrap them:

```swift
var coordError: NSError?
NSFileCoordinator().coordinate(readingItemAt: url, options: [], error: &coordError) { actual in
    data = try? Data(contentsOf: actual)   // note: `actual`, not `url`
}
```

Two details that cost debugging time:

* Use the URL the coordinator hands you (`actual`), not the one you
  passed in. They differ when the system substitutes a version.
* Coordinate **writes** with `.forReplacing` and deletes with
  `.forDeleting`, and write atomically inside the block.

Coordination is harmless for local files, so put *all* file access
behind it rather than branching on whether this project is in iCloud.
One code path, no "works locally, corrupts in iCloud" class of bug.

**Verify:** Grep the storage layer — no direct Data(contentsOf:)/write(to:) on container paths remains.

*Source: Apple (archive) — File System Programming Guide: The Role of File Coordinators and Presenters.*

## 8 — Resolve conflicts yourself, because nothing else will

Coordination prevents *simultaneous* corruption. It does not decide what
happens when two devices edited the same file while offline — that
leaves the file with unresolved conflict versions, and until someone
resolves them the file keeps handing you surprises.

The archive guide is explicit that documents get this for free and plain
files do not:

> Documents, as file presenters, automatically handle conflicts […] For
> files, you manually resolve conflicts using file presenters.

A workable policy for state that is small and idempotent is
last-writer-wins:

1. `NSFileVersion.unresolvedConflictVersionsOfItem(at:)` — if empty, done.
2. Compare their `modificationDate` against the current version.
3. If a conflict version is newer, `replaceItem(at:)` with it.
4. Mark every conflict `isResolved = true`, then
   `removeOtherVersionsOfItem(at:)`.

Do this **before** every read, not on a timer. And be honest about what
last-writer-wins costs: one side's edit disappears. If the data cannot
tolerate that — two people editing prose, say — you need per-field
merging, and that is a much bigger decision than this playbook.

Where you *can* avoid the question, do: an append-only structure (each
device appends its own entries) has no conflicts to resolve.

**Verify:** Put both devices in airplane mode, edit the same file on each, reconnect — the file ends up valid and the loser is logged, not silently gone.

*Source: Apple (archive) — iCloud Design Guide: iCloud Fundamentals.*

## 9 — Check that nothing requires the other device to be awake

Come back to the decision from the first step and verify it in practice,
because it is easy to reintroduce: a "pending action" file, a queue the
Mac drains, a notification the Mac turns into a write. Each of these
quietly makes the companion useless while the Mac is closed.

The test is blunt: **quit the Mac app entirely** — not just close the
window — then do the thing on the phone, and check that the result is
complete in the shared files without the Mac ever running.

Also handle the double-write: if both sides can act on the same item,
the second one must notice and refuse ("this is no longer open") rather
than appending a second, contradictory answer.

**Verify:** With the Mac app quit, act on the phone and inspect the container from a third machine - the change is complete and consistent.

## 10 — Smoke-test on real devices, with the failures you expect

None of this is testable in CI. The manual pass, in order:

1. Mac and phone signed into the **same** Apple Account, iCloud Drive on.
   (In the iOS simulator: Settings → sign in → iCloud Drive on.)
2. Mac app: the "move to iCloud" affordance is enabled rather than
   showing "iCloud unavailable".
3. Migrate a project, confirm the files appear in iCloud Drive under
   `Documents`.
4. Quit the Mac app. Act on the phone. Verify the file changed.
5. Reopen the Mac app — it shows the phone's change.

**Troubleshooting, in the order these actually occur:**

* *Still "unavailable"*: not signed in, iCloud Drive off, container id
  mismatch, or the app id lacks the capability.
* *Signing failure*: the capability is missing in the portal or the
  profile is stale — reload profiles.
* *A container path with the wrong team prefix* (`ABCD1234.` instead of
  your team): the target is signed with a different team, or the app id
  was registered under one. Fix the team, not the code.

**Verify:** The full sequence above passes on two physical devices, including the Mac-quit step.

## Pitfalls

- Calling `url(forUbiquityContainerIdentifier:)` on the main thread. It returns instantly on your machine and beachballs on a cold one.
- Writing outside `Documents/` in the container. It syncs, but the user never sees the files in iCloud Drive.
- Treating `nil` as an error. It is the normal state for a user who has not enabled iCloud, and an error dialog there is just noise.
- Coordinating reads but not writes (or the reverse). Both directions need it, and using the coordinator's substituted URL is not optional.
- Assuming conflicts resolve themselves. Plain files keep unresolved versions until you handle them, and the symptoms look like random data loss.
- Giving each app its own container "because they have different bundle ids". One container, listed identically in both entitlement files.

## Acceptance

- Given Mac app and iOS companion signed into the same account, project migrated to iCloud, when The Mac app is quit and the user acts on the phone, then The shared files contain the complete change, and the Mac shows it on next launch.
- Given A user who never enabled iCloud, when They use the app normally, then Everything works against local storage, with no error dialogs and no attempt to migrate.

## Sources

- [Apple (archive) — iCloud Design Guide: iCloud Fundamentals](https://developer.apple.com/library/archive/documentation/General/Conceptual/iCloudDesignGuide/Chapters/iCloudFundametals.html) — retrieved 2026-08-06
  Archived guide, but the source of the verbatim background-thread rule for URLForUbiquityContainerIdentifier, of "if the method returns nil, document storage is not available", and of the statement that plain files (unlike documents) need manual conflict resolution. The current API reference at developer.apple.com/documentation renders client-side and could not be quoted.
- [Apple (archive) — File System Programming Guide: The Role of File Coordinators and Presenters](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/FileCoordinators/FileCoordinators.html) — retrieved 2026-08-06
  Why uncoordinated concurrent access corrupts files; what a file presenter is for.
