---
name: ui-browser-check
description: Reproduce and verify a Speccify desktop UI or layout issue in a browser against the mock bridge, without touching the user's running app — find the component, pick the fixture, shrink the window, measure, screenshot, turn it into a regression. Use for "man sieht X nicht", overflow, scrolling, dialogs, theming and other findings that need no native behaviour.
---

# UI check in the browser

The desktop frontend renders in plain Chrome through
`apps/desktop/dev/mock.html`, which replaces the Tauri bridge with fixtures. This
proves layout and interaction logic. It does not prove native behaviour (PTY,
file system, updater installation, WKWebView quirks) — use `local-app` for that.
The Chrome extension and OS-level remote control do not work for this app.

## 1. Find the place

Search the visible label in `apps/desktop/src` (`grep -rniE`); German UI texts
may differ slightly from how the user quotes them.

## 2. Own server, own port

```sh
pnpm --dir apps/desktop exec vite --host 127.0.0.1 --port 5199 --strictPort
```

Run it in the background and stop it when done. Never reuse or stop the user's
dev server (1420/1421) or the running app.

## 3. Pick the fixture by query parameter

`mock.html` installs fixtures only when asked: `?updates`, `?workspaces`,
`?playbook-drafts`, `?marketing`, `?dashboard`, `?terminaltest`,
`?agentsettingstest`, plus `project=`, `owner=`, `register=`, `workflow=`,
`session=`, `askwin=`. Read the top of `mock.html` and the matching
`dev/*-fixture.js`. State is steerable at runtime through
`window.__SPECCIFY_MOCK__` (for updates: `update`, `updateOffline`,
`updateProcessRunning`, `finishUpdateDownload()`); dialogs open through the same
window events the app uses (`speccify:updates`). Missing state → extend the
fixture, do not rewrite rendered DOM.

## 4. Reproduce, then measure

Make the bad case real: small viewport (900×420), long content, the error
state. Measure with `getBoundingClientRect()` against `innerHeight` and the
clipping container, then take a screenshot and look at it. Both: numbers catch
clipping, the image catches what numbers miss.

Playwright scrolls a target into view before clicking. For "visible without
scrolling", set scroll positions yourself before asserting.

## 5. Fix and keep it

Prefer structure over tricks: a fixed header/footer with one scrolling region
(`flex flex-col` + `min-h-0 flex-1 overflow-auto`) rather than `scrollIntoView`.
Check light and dark (`.agent/playbooks/ui-gestaltung.md`). Add the case to the
matching `scripts/test_*.mjs` and prove that it fails against the old code
(`project-checks` skill). Update `stand-und-ui.md` when behaviour changed.

## 6. Clean up

Stop the server, delete `.playwright-mcp/` from the repo root (Playwright MCP can
only write inside the repo), keep screenshots in the scratchpad.
