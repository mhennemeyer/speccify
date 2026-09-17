---
name: local-app
description: Check, rebuild, restart or update the locally bundled Speccify app the user works in, without losing drafts or killing foreign processes, and drive it through the QA bridge for acceptance checks. Use when the user says "App neu starten", "neuen Build", "läuft die App", before and after desktop changes, and for the update proof at the end of a release.
---

# Local app

The user works productively in a bundled app without watcher
(`target/debug/bundle/macos/Speccify.app`, UI-MCP port **18768**, QA bridge
**18769**). Saved specs and playbooks are read live; program changes arrive only
with a new build or an installed update.

## Status — before and after every change

```sh
./scripts/dev.sh --status --ui-port=18768
```

"Running" means an executable mapping with a PID on the expected binary. An open
port alone proves nothing: 8768 belongs to Lima on this Mac, and read-only
handles of macOS services are not app instances. Never stop foreign port owners.

With the bridge on, `<tmp>/speccify-qa-bridge.json` (mode 0600) holds `url`,
`token` and `pid`:

```sh
curl -s -H "Authorization: Bearer $TOKEN" "$URL/health"     # {ok,pid,version}
curl -s -H "Authorization: Bearer $TOKEN" "$URL/windows"
```

## Restart rules

Restarts for updates are permitted and wanted; announce them briefly, do not ask
each time. A current "do not restart now" wins. Before stopping:

- Look for drafts, open editors, running terminals and actions. The update
  coordinator refuses installation while any exist — treat that as information,
  not as an obstacle to work around.
- Rust changes restart a `tauri dev` instance on save. Bundle Rust edits and
  announce them (text was lost that way on 2026-09-07).
- Afterwards start the app again and check that windows and sessions resumed.
  A reachable port is not a usable UI.

## Build and open

```sh
./scripts/dev.sh --open --ui-port=18768                       # reopen existing build
./scripts/dev.sh --app --prepared --ui-port=18768             # new build, deps known good
./scripts/dev.sh --app --prepared --skip-engine --ui-port=18768 --qa-bridge=18769   # for acceptance runs
./scripts/dev.sh --no-start                                   # prepare deps/sidecars/payload first
```

- `--prepared` only with matching deps, sidecars and payload. After changes in
  `crates/mcp-core` or the Rust MCPs: `scripts/build_sidecars.sh --debug` first.
- The build is signed with the Developer ID from the keychain so macOS folder
  permissions survive rebuilds (`--unsigned` opts out). If macOS asks for Desktop
  access, the user confirms; never bypass a system prompt.
- Do not run `cargo test` in parallel with the native build.

## Update through the real updater

The acceptance at the end of a release, on the installed previous version:

1. Status and windows noted; no drafts, editors, terminals or actions open.
   If your own session runs in a Speccify terminal (walk the parent processes
   with `ps -o ppid=,comm=`), the guard blocks the install and a restart would
   end you: ask the user to click instead.
2. Environment → Updates → search → download → **Installieren und neu starten**.
   Over the bridge the same steps are the Tauri commands `update_check`,
   `update_download`, `update_install`, observed with `update_snapshot`
   (`POST /invoke` with `{window, command}`).
3. After the restart: `/health` shows the new version, `update_snapshot` phase
   `current`, the same windows are back, and
   `codesign --verify --deep --strict <Speccify.app>` passes.

A blocked installation reports its reason in the dialog and in
`update_snapshot.error`; the verified download is kept. Every open terminal
counts as running work, also a plain shell after the agent quit
(`update_snapshot.active_work`, since 0.8.4). `update_stop_all` — the dialog's
confirmed **Alles stoppen** — ends all terminals, actions and supervised
processes. It interrupts the user's agents: never call it over the bridge
without the user's explicit request. Up to 0.8.3 a finished download also
suppressed every further search until the app restarted. Restarting the app
discards the in-memory download, not the settings.

## Driving the bundled app

Playwright cannot attach to WKWebView. Use the QA bridge (`docs/qa-bridge.md`):
`/eval` for DOM checks, `/invoke` for Tauri commands, `/focus` before terminal
checks (background WKWebViews defer `requestAnimationFrame`), `/screenshot` for a
window image. Repeatable acceptance suites live in the separate `speccify-qa`
repo (`python -m speccify_qa.cli`). Operation and handshake are not human
acceptance; name the build that was actually running.

For layout questions without native behaviour use the `ui-browser-check` skill.
