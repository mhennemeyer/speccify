---
name: build-libgit2
description: Builds libgit2 from a tagged source release as a universal
  (arm64 + x86_64) static archive with HTTPS over Apple's SecureTransport and no
  SSH, and lays it out as a SwiftPM-ready vendor directory — headers including
  the generated ones, a module map, a placeholder source and a README that says
  how it was built.
inputs:
  type: object
  required: [version, vendor_dir]
  additionalProperties: false
  properties:
    version: {type: string, description: libgit2 tag without the leading v, e.g. 1.9.6}
    vendor_dir: {type: string, description: Target directory; created if missing.}
    deployment_target: {type: string, default: "14.0"}
outputs:
  type: object
  required: [ok, archive, architectures, generated_headers_present]
  properties:
    ok: {type: boolean}
    archive: {type: string, description: Path to libgit2.a}
    architectures: {type: array, items: {type: string}}
    generated_headers_present: {type: boolean, description: version.h and
      experimental.h exist under include/git2 — they come from the build, not
      the source tree, and their absence looks like a broken checkout.}
    error: {type: string}
effects: downloads the source tarball from github.com; builds in a temp
  directory it removes afterwards; writes lib/, include/, module.modulemap,
  shim.c and README.md into `vendor_dir`, replacing an existing include/git2
requires: cmake, lipo, curl, tar
runtime: any
platforms: macos
---

## Behaviour

1. Fetch `https://github.com/libgit2/libgit2/archive/refs/tags/v<version>.tar.gz`.
2. Configure and build once per architecture with `BUILD_SHARED_LIBS=OFF`,
   `USE_HTTPS=SecureTransport`, `USE_SSH=OFF`, tests/CLI/examples off and
   `REGEX_BACKEND=builtin` (a stray PCRE on the build machine must not leak
   into the archive).
3. `lipo -create` the two archives into `<vendor_dir>/lib/libgit2.a`.
4. Copy `include/git2` and `git2.h` from the source tree, then overlay the
   build's generated `include/git2/` on top.
5. Write `module.modulemap` (module `Clibgit2`, header `git2.h`), an empty
   `shim.c` and a README with version, date, architectures and deployment
   target.
6. Verify with `lipo -info` and the presence of `include/git2/version.h`.
   `ok` is false, with `error`, if either fails.

## Examples

### clean build of a tagged release
input: {"version": "1.9.6", "vendor_dir": "Vendor/libgit2"}
output: {"ok": true, "archive": "Vendor/libgit2/lib/libgit2.a", "architectures": ["arm64", "x86_64"], "generated_headers_present": true}

### a tag that does not exist
input: {"version": "9.9.9", "vendor_dir": "Vendor/libgit2"}
output: {"ok": false, "archive": "", "architectures": [], "generated_headers_present": false, "error": "download failed: HTTP 404 for v9.9.9"}
