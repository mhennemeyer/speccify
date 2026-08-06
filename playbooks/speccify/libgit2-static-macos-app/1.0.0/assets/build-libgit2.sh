#!/usr/bin/env bash
#
# Build libgit2 as a universal static archive for a sandboxed macOS app.
# HTTPS via Apple's SecureTransport, no SSH, no OpenSSL to vendor.
#
# Usage: ./build-libgit2.sh <version> <vendor-dir> [deployment-target]
#   ./build-libgit2.sh 1.9.6 ../Vendor/libgit2 14.0
#
# Produces:  <vendor-dir>/lib/libgit2.a   (arm64 + x86_64)
#            <vendor-dir>/include/        (headers incl. the generated ones)

set -euo pipefail

VERSION="${1:?libgit2 version, e.g. 1.9.6}"
VENDOR="${2:?target directory, e.g. ../Vendor/libgit2}"
DEPLOYMENT_TARGET="${3:-14.0}"

VENDOR="$(mkdir -p "$VENDOR" && cd "$VENDOR" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==> libgit2 $VERSION -> $VENDOR (deployment target $DEPLOYMENT_TARGET)"

curl -sSL -o "$WORK/libgit2.tar.gz" \
  "https://github.com/libgit2/libgit2/archive/refs/tags/v${VERSION}.tar.gz"
tar xzf "$WORK/libgit2.tar.gz" -C "$WORK"
SRC="$WORK/libgit2-${VERSION}"

for arch in arm64 x86_64; do
  echo "==> configure + build $arch"
  # BUILD_SHARED_LIBS/BUILD_TESTS/BUILD_CLI all default to ON upstream.
  # REGEX_BACKEND=builtin keeps a stray PCRE off the build machine out of it.
  cmake -S "$SRC" -B "$SRC/build-$arch" \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    -DUSE_HTTPS=SecureTransport \
    -DUSE_SSH=OFF \
    -DBUILD_TESTS=OFF -DBUILD_CLI=OFF -DBUILD_EXAMPLES=OFF \
    -DREGEX_BACKEND=builtin \
    -DCMAKE_OSX_ARCHITECTURES="$arch" \
    -DCMAKE_OSX_DEPLOYMENT_TARGET="$DEPLOYMENT_TARGET" >/dev/null
  cmake --build "$SRC/build-$arch" --config Release -j"$(sysctl -n hw.ncpu)" >/dev/null
done

echo "==> lipo"
mkdir -p "$VENDOR/lib" "$VENDOR/include"
lipo -create "$SRC/build-arm64/libgit2.a" "$SRC/build-x86_64/libgit2.a" \
  -output "$VENDOR/lib/libgit2.a"

echo "==> headers (including the generated ones)"
rm -rf "$VENDOR/include/git2" "$VENDOR/include/git2.h"
cp -R "$SRC/include/git2" "$VENDOR/include/"
cp    "$SRC/include/git2.h" "$VENDOR/include/"
# version.h and experimental.h are produced by the build, not shipped in the
# source tree. Omitting them fails to compile in a way that looks like a
# broken checkout.
cp -R "$SRC/build-arm64/include/git2/." "$VENDOR/include/git2/"

cat > "$VENDOR/include/module.modulemap" <<'MODULEMAP'
module Clibgit2 {
    header "git2.h"
    export *
}
MODULEMAP

cat > "$VENDOR/shim.c" <<'SHIM'
/* Placeholder source for the Clibgit2 target. The implementation lives in the
 * vendored, statically linked libgit2.a. SwiftPM needs at least one source
 * file; publicHeadersPath = include/ propagates the header path to dependents. */
SHIM

cat > "$VENDOR/README.md" <<README
# Vendored libgit2 (static, HTTPS via SecureTransport, no SSH)

- **Version:** libgit2 ${VERSION}
- **Built:** $(date -u +%Y-%m-%d) with \`build-libgit2.sh\`
- **Architectures:** universal (arm64 + x86_64)
- **Deployment target:** ${DEPLOYMENT_TARGET}

Rebuild with \`./build-libgit2.sh ${VERSION} <this-dir> ${DEPLOYMENT_TARGET}\`.

This is C code with a CVE history. Check
<https://github.com/libgit2/libgit2/releases> periodically and rebuild.
README

echo "==> verify"
lipo -info "$VENDOR/lib/libgit2.a"
test -f "$VENDOR/include/git2/version.h" \
  || { echo "FAIL: generated headers missing" >&2; exit 1; }
echo "OK — now link with -force_load, not -lgit2, and check otool -L on the app binary."
