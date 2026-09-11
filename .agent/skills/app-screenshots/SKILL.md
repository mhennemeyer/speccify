---
name: app-screenshots
description: Capture repeatable Speccify desktop UI screenshots with curated public demo data for the website or documentation. Use when refreshing product screenshots, selecting a shot, or checking screenshot drift; not for native OS dialogs or App Store submission screenshots.
---

# App screenshots

Capture the real desktop React components through the isolated development bridge.
The screenshots show the macOS layout, not a native window capture. Do not redraw
controls or use the user's live projects, terminal sessions, or filesystem data.

## In this project

- Read `.agent/playbooks/website.md` for the selected motifs, placement, and approval state.
- Public fixture: `apps/desktop/dev/marketing-fixture.js`, selected only by
  `apps/desktop/dev/mock.html?marketing=1`. Change demo data there, not by replacing
  rendered DOM text. The other mock profiles are regression fixtures: preserve them.
- From the repository root, after `pnpm install --frozen-lockfile`, run
  `pnpm screenshots:app`. The script starts an isolated Vite instance on a free
  loopback port, uses a fresh browser context, and closes both when finished.
- Default browser: installed Chrome on macOS. For bundled Chromium, first run
  `pnpm exec playwright install chromium`, then `SCREENSHOT_BROWSER=chromium pnpm screenshots:app`.
  Review font/rendering changes when switching browser or OS; published captures
  should be produced on macOS. The script requires macOS rather than disguising another OS.
- Outputs in `apps/marketing/src/assets/landing/`: `board.png`, `skills.png`,
  `tools.png`, `playbooks.png`, `mcps.png`, `actions.png`, `files.png`, `git.png`. Keep the
  existing documentation images under `assets/app/` untouched. Native title-bar
  decorations are not part of these images; website framing is presentation only.
  Astro delivers responsive WebP variants. Do not manually edit the bitmaps.
- `scripts/capture.mjs` fixes viewport, theme, panels, selected spec, terminal demo
  output, skill/tool/playbook selection, MCP selection, benchmark output, file and
  Git draft. English demo content, en-US browser locale; do not translate hardcoded
  product labels by replacing DOM text. The website is English-first for now.
  Assertions reject missing targets, JS errors, private fixture
  remnants and non-loopback network requests. It performs no native Git/shell actions.
  Only the synthetic benchmark action may run through the mock bridge. Tool-status
  badges and chart values are fixture illustrations, never product performance claims.

## Evaluate the result

1. Inspect every output image: complete labels, the intended feature selected, readable
   contrast, no blank/load states or unrelated personal content. A passing script
   alone is not visual approval. Update fixture/selection if the story is unclear.
2. Run the capture twice after changing its setup; compare image hashes on the
   same machine/browser. Resolve moving cursors, async loads or varying layout.
3. Build with `pnpm marketing:build`; run `pnpm marketing:preview --host 127.0.0.1`.
   Inspect `/` and `/features/` at desktop and phone widths; `/de/` currently redirects
   to English. Run `node scripts/test_landing_screenshots.mjs` against the preview.
   Images must not overflow;
   full-size image links must work with keyboard and without JavaScript.
4. Record checks and remaining limitations in the active spec. Keep the website
   playbook current if shot choice or framing changes. Capture/build does not
   authorize publishing or imply human acceptance; follow repository permissions.

## Choosing the next shot

Read the implemented view before writing public claims. Prefer a visible
relationship (skill → contract → platform status, spec → tasks → review) over a
generic editor screen. Extend the public fixture and capture sequence together;
wait for the actual selected document or result, not merely for the tab to appear.
Keep a screenshot with each feature group and verify its full-size link. Put the
editorial ranking in the website playbook, not in a second screenshot skill.

If the page fails a readiness assertion, fix the fixture or selector. Do not hide
errors by arbitrary DOM removal, wider timeouts or captures of the live personal app.
