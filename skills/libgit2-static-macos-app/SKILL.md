---
name: libgit2-static-macos-app
description: 'Get real Git — clone, commit, push over HTTPS — inside a Mac app that has to
  pass App Review: libgit2 built from source with Apple''s TLS, merged to a universal static
  archive, wired into SwiftPM, and verified to be genuinely static rather than quietly linked
  against Homebrew. Use when working with swiftpm or xcode on macos, or when the user mentions
  libgit2, static-linking, sandbox, universal-binary, securetransport or app-store.'
license: MIT
compatibility: Requires CMake, Xcode command line tools and A SwiftPM package in the app
metadata:
  speccify.version: 1.0.0
  speccify.scope: speccify
  speccify.stack: swiftpm, xcode
  speccify.platforms: macos
---

## Prerequisites

- A local SwiftPM package inside the app repository (not a remote dependency — see the `unsafeFlags` step).
- Decide up front whether you need push/pull over HTTPS. It changes the build flags.

## 1 — Know why you are not shelling out to `git`

The tempting alternative is to run the `git` binary. In a Mac App Store
app it is not available to you: apps must be self-contained and

> may not download, install, or execute code which introduces or changes
> features or functionality of the app

and for the Mac App Store specifically, apps

> may not download or install standalone apps, kexts, additional code, or
> resources to add functionality.

Bundling a `git` binary and spawning it is exactly what that forbids, and
relying on the user having Xcode's `git` puts a system dependency in the
middle of your feature. Linking a library into your own binary is not
"downloading or executing code" — it is your app.

This also rules out Homebrew's libgit2 as a runtime dependency: a dylib
under `/opt/homebrew` will not exist on a customer's machine.

**Verify:** State the decision in the repository, so nobody re-opens it in six months.

*Source: App Store Review Guidelines — 2.5.2 and 2.4.5(iv).*

## 2 — Pin a libgit2 version deliberately

Check the current release rather than copying a version out of a blog
post — libgit2 ships security fixes, and vendored copies are exactly the
kind of thing that silently ages.

Record the version you vendored in a README next to the archive. Without
it, nobody can tell six months later what they are shipping.

**Verify:** The vendored directory contains a README naming the exact upstream tag.

*Source: libgit2 — releases.*

## 3 — Build it static, with Apple's TLS and without SSH

One CMake configure per architecture. The flags are the whole trick:

```bash
cmake -S . -B build-arm64 \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DUSE_HTTPS=SecureTransport \
  -DUSE_SSH=OFF \
  -DBUILD_TESTS=OFF -DBUILD_CLI=OFF -DBUILD_EXAMPLES=OFF \
  -DREGEX_BACKEND=builtin \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=14.0
```

Why each one:

* **`BUILD_SHARED_LIBS=OFF`** — defaults to `ON`. Without it you get a
  dylib and you are back to shipping a loose binary.
* **`USE_HTTPS=SecureTransport`** — uses Apple's system TLS instead of
  OpenSSL, so there is no OpenSSL to vendor, sign and keep patched. It is
  already the default on macOS; passing it explicitly documents the
  intent and fails loudly if that ever changes.
* **`USE_SSH=OFF`** — the default. libssh2 would add another vendored
  dependency and a credential story you probably do not want. HTTPS with
  a token covers GitHub, GitLab and friends.
* **`REGEX_BACKEND=builtin`** — avoids picking up PCRE from the build
  machine, which would then be missing on someone else's.
* **`BUILD_TESTS=OFF`, `BUILD_CLI=OFF`** — both default to `ON` and just
  cost build time.
* **`CMAKE_OSX_DEPLOYMENT_TARGET`** — must match your app's minimum, or
  the linker complains about objects built for a newer macOS.

**Verify:** Each build produces `build-<arch>/libgit2.a` and no `.dylib`.

*Source: libgit2 — README (build options).*

## 4 — Merge the architectures into one archive

Build `arm64` and `x86_64` separately, then merge:

```bash
lipo -create build-arm64/libgit2.a build-x86_64/libgit2.a \
  -output Vendor/libgit2/lib/libgit2.a
lipo -info Vendor/libgit2/lib/libgit2.a   # must list both
```

Copy the headers too — **including the generated ones**. `version.h` and
`experimental.h` are produced by the build, not shipped in the source
tree, and a copy that misses them fails to compile in a way that looks
like a broken checkout:

```bash
cp -R include/git2 include/git2.h        Vendor/libgit2/include/
cp -R build-arm64/include/git2/.         Vendor/libgit2/include/git2/
```

**Verify:** `lipo -info` lists arm64 and x86_64, and `Vendor/libgit2/include/git2/version.h` exists.

*Source: libgit2 — README (build options).*

## 5 — Expose the headers through a C target

SwiftPM needs a C target to carry the headers. It needs at least one
source file, so give it a comment-only `shim.c` — the actual code lives
in the archive.

```
Vendor/libgit2/
├── include/
│   ├── git2.h
│   ├── git2/…
│   └── module.modulemap
├── lib/libgit2.a
└── shim.c
```

```swift
.target(
    name: "Clibgit2",
    path: "Vendor/libgit2",
    exclude: ["lib", "README.md"],
    sources: ["shim.c"],
    publicHeadersPath: "include"
)
```

`publicHeadersPath` is what makes this work under both `swift build` and
Xcode: SwiftPM propagates the include path to every dependent target, so
you do not hand-maintain `-I` flags in two build systems.

`module.modulemap` is three lines:

```
module Clibgit2 {
    header "git2.h"
    export *
}
```

**Verify:** `import Clibgit2` compiles in a Swift file, and `swift build` succeeds from a clean checkout.

*Source: Swift Package Manager — PackageDescription (linkerSettings, unsafeFlags, publicHeadersPath).*

## 6 — Link with -force_load, not -lgit2

This is the failure that eats an afternoon, because everything builds.

With a plain `-lgit2` the linker only pulls in object files that resolve
a symbol somebody references. libgit2's HTTPS transport **registers
itself** — nothing in your code names it — so it gets dead-stripped. The
app links, runs, does local Git perfectly, and then fails on the first
`push` with an error that reads like a network or credential problem.

Force the whole archive in:

```swift
.target(
    name: "InProcessGit",
    dependencies: ["Clibgit2"],
    linkerSettings: [
        .unsafeFlags(["-Xlinker", "-force_load",
                      "-Xlinker", "\(libgit2LibDir)/libgit2.a"]),
        .linkedLibrary("z"),
        .linkedLibrary("iconv"),
        .linkedFramework("Security"),        // SecureTransport
        .linkedFramework("CoreFoundation"),
    ]
)
```

`Security` and `CoreFoundation` are what SecureTransport needs; `z` and
`iconv` are libgit2's own system dependencies.

**Verify:** Clone over https:// from the built app — not just a local repo. That is the only test that exercises the transport.

*Source: Swift Package Manager — PackageDescription (linkerSettings, unsafeFlags, publicHeadersPath).*

## 7 — Accept what `unsafeFlags` costs you

`-force_load` has to go through `.unsafeFlags`, and that has a
consequence people discover much later:

> a product can't be used as a dependency in another package if one of
> its targets uses unsafe flags

So the package containing this target **cannot be consumed as a
versioned SwiftPM dependency by anyone**. That is fine for a local
package inside your app repository, and fatal if you planned to publish
it. Decide now, not after someone tries to depend on it.

If you must publish, the escape is to move the linking into the Xcode
target (Other Linker Flags) instead of the package manifest — at the
price of a build setting that `swift build` alone will not apply.

**Verify:** Nobody outside this repository declares a dependency on this package.

*Source: Swift Package Manager — PackageDescription (linkerSettings, unsafeFlags, publicHeadersPath).*

## 8 — Prove it is actually static

A build that succeeds on your machine proves nothing: Homebrew's libgit2
may be satisfying the link. Check the produced binary:

```bash
otool -L path/to/YourApp.app/Contents/MacOS/YourApp | \
  grep -Ei 'git2|ssl|crypto|ssh'
```

**Empty output is the pass.** Any hit means you are shipping a
dependency on a dylib that will not exist on a customer's Mac.

Run this against the **Release** build of the universal binary, not the
debug one, and ideally in CI — this is precisely the check that rots
silently when someone changes a build flag.

**Verify:** `otool -L` on the release app binary shows no git2/ssl/crypto/ssh entries; `lipo -info` shows both architectures.

*Source: libgit2 — README (build options).*

## 9 — Give the sandbox exactly what Git needs

Two entitlements, and no more:

* `com.apple.security.network.client` — required for HTTPS fetch/push.
  Without it the connection fails inside the sandbox with an error that
  does not mention entitlements at all.
* `com.apple.security.files.user-selected.read-write` — the user picks
  the repository folder. Keep a **security-scoped bookmark** so the
  access survives a relaunch, and confine every path you touch to that
  root (a path that resolves outside it after following `..` and
  symlinks must be rejected, not clamped).

Note that libgit2 will happily follow a symlink out of the repository if
you hand it a path from user input. The containment check is yours to
write.

**Verify:** In a signed, sandboxed Release build, clone from https:// into a user-selected folder, quit, relaunch, and commit again without re-picking the folder.

*Source: Apple Developer — App Sandbox.*

## 10 — Sign and notarize without weakening anything you just gained

A statically linked archive needs no separate signature — it is part of
your binary, which is exactly the point. The usual distribution ritual
still applies (hardened runtime, signature, notarization, staple), and
for a Tauri-based app `@speccify/macos-notarize-tauri` walks through it.

What is specific to *this* change: check that nobody disabled a
protection while fighting the linker. If
`com.apple.security.cs.disable-library-validation` appeared in the
entitlements during debugging, remove it — a statically linked library
needs none of it, and leaving it in weakens the app permanently for a
problem that no longer exists.

Same for `com.apple.security.cs.allow-unsigned-executable-memory` and
friends: each one you keep is a question at review time that you would
have to answer.

**Verify:** `codesign -d --entitlements - YourApp.app` lists only entitlements you can justify — no library-validation opt-out.

*Source: App Store Review Guidelines — 2.5.2 and 2.4.5(iv).*

## Pitfalls

- `-lgit2` instead of `-force_load`: builds, runs, and breaks only on the first network operation, with an error that points at TLS or credentials rather than at the linker.
- Forgetting the generated headers (`version.h`, `experimental.h`). The compile error looks like a corrupt checkout of libgit2.
- Verifying with a debug build on the developer's machine, where Homebrew's libgit2 silently satisfies the link. Check the release binary with `otool -L`.
- Vendoring the archive and never touching it again. It is C code with a CVE history; put the upstream version in a README and re-check it on a schedule.
- SecureTransport is Apple's older TLS stack and has been deprecated in favour of Network.framework. It still works and libgit2 defaults to it on macOS, but check the situation before starting — if it is finally removed, the alternative is vendoring OpenSSL, which is a much larger job.

## Acceptance

- Given A signed, sandboxed, universal Release build on a Mac without Homebrew, when The user clones a repository over https:// and pushes a commit, then Both succeed, and `otool -L` on the binary shows no libgit2/OpenSSL/SSH dylib.

## Sources

- [libgit2 — README (build options)](https://github.com/libgit2/libgit2) — retrieved 2026-08-06
  Verified against CMakeLists.txt on the same day - BUILD_SHARED_LIBS, BUILD_TESTS and BUILD_CLI all default to ON; USE_SSH defaults to OFF; USE_HTTPS defaults to SecureTransport on macOS.
- [libgit2 — releases](https://github.com/libgit2/libgit2/releases) — retrieved 2026-08-06
  Latest release at the time of writing was v1.9.6 (2026-07-18).
- [Swift Package Manager — PackageDescription (linkerSettings, unsafeFlags, publicHeadersPath)](https://docs.swift.org/package-manager/PackageDescription/PackageDescription.html) — retrieved 2026-08-06
  Source of the rule that a product using unsafe flags cannot be a dependency of another package.
- [App Store Review Guidelines — 2.5.2 and 2.4.5(iv)](https://developer.apple.com/app-store/review/guidelines/) — retrieved 2026-08-06
  Self-contained apps; no downloading, installing or executing code; Mac App Store may not install standalone apps or additional code.
- [Apple Developer — App Sandbox](https://developer.apple.com/documentation/security/app-sandbox) — retrieved 2026-08-06
