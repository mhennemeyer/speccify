---
description: Website positioning, feature order and repeatable product screenshots
---
# Website: show what makes Speccify different

Living playbook for `apps/marketing/`. Product direction: [Weiterentwicklung](weiterentwicklung.md).
Current work and verification: [Spec 023](../specs/023-landingpage-app-screenshots/SPEC.md).

## Editorial decision · 2026-09-11

The first visual direction was received positively. The user explicitly rejected
Git as a differentiating headline: it belongs near the end, with the other familiar
IDE capabilities. Lead with reusable knowledge and locally verified tool contracts.
MCP support connects that workflow to the chosen host; it is not the central promise.

The landing page keeps the large board image immediately after the hero. It shows
the whole workspace. The lower product section now shows a selected skill, its
source/version and related tool, with a link to **Features**. No carousel.

The new `/features/` page is a product tour, grouped by capability and ordered by
distinctiveness, not by implementation size or navigation order. Each group has
an actual app screenshot, explanatory copy and a deeper documentation link.

| Order | Feature group | Visible evidence / implementation source |
| --- | --- | --- |
| 1 | Reusable skills | SkillsTab: procedure, local guidance, source/version, related tools; source browsing, import/export terminal commands |
| 2 | Tool contracts | ToolsTab: inputs/outputs/effects/examples, per-platform state; CLI/core tool check and verify |
| 3 | Specs and acceptance | BoardTab: board/list, task inspector, questions/history, human review, measured run totals when recorded |
| 4 | Living playbooks | PlaybooksTab: product direction, UI map, standing procedures, editing and prompt copy |
| 5 | Agents and MCP | McpsTab: host-specific configuration, URLs/commands, allowlists; AgentTab/TerminalPanel startup and guidance; ServersView management |
| 6 | Actions and output | ActionsTab: named commands, approval, toolbar, independent output tabs, stop, structured charts |
| 7 | Files and editor | FilesTab: tree, file icons, tabs, code/Markdown, file operations/history; shell panels, theme/help/settings |
| 8 | Git | GitWorkspace/GitTab: composer, staged index, file/hunk diffs, local branches, tracking, fetch/pull/push |

Those are feature groups, not a screenshot of every dialog. Keep the functional UI
tree in [Stand und UI](stand-und-ui.md) as the completeness cross-check. Do not
advertise placeholder views, multi-repo workspaces, team-wide boards, semantic
refactoring, universal profiling or planned integrations as shipping features.
Configuration screenshots do not prove a live MCP connection; mock tool statuses
do not prove verification. Avoid guarantees about session resumption or context delivery.

## English first

User decision: defer German localization. New marketing copy, captions, alt text
and demo documents are English. `/de/` redirects to `/`; no duplicate DE Features
page. Existing translated documentation remains reachable and is not deleted or
translated further in this iteration. Full documentation-language cleanup is separate.
The actual app still has German controls. Do not disguise them in screenshots:
the Features introduction explains the current language mix. App localization is
not part of screenshot production.

## Canonical sources

- Pages: `apps/marketing/src/pages/index.astro`, `features.astro`, `de/index.astro`.
- Shared navigation: `layouts/MarketingLayout.astro`, Features in header/footer.
- `components/AppScreenshot.astro`: intrinsic dimensions, responsive WebP,
  first image eager/high, later images lazy; full-size links work without JS.
- Originals in `src/assets/landing/`: board, skills, tools, playbooks, mcps,
  actions, files, git. Keep existing documentation images in `assets/app/` separate.
- Public fixture: `apps/desktop/dev/marketing-fixture.js`, selected only by
  `dev/mock.html?marketing=1`. Fictional OrbitNotes, no personal files or sessions.
- Procedure: [app-screenshots](../skills/app-screenshots/SKILL.md). Extend this skill
  when adding motifs; do not duplicate it for each website page.

These are captures of the real React components through an isolated development
bridge on macOS, **not native-window captures**. Website-only traffic lights are
decorative framing. No redrawn product controls or post-processed UI text.
The board uses six specs and a selected search task list. Skills/Tools use a
Markdown export example. The benchmark chart contains explicitly synthetic values.

## Capture and review

From the repo root, macOS with Chrome installed:

```sh
pnpm install --frozen-lockfile
pnpm screenshots:app
pnpm marketing:build
pnpm marketing:preview --host 127.0.0.1 --port 4321
node scripts/test_landing_screenshots.mjs
```

Capture runs its own Vite server on a free loopback port and closes it afterward.
The personal app stays open. Viewport 1344 × 840, DPR 2, dark theme, en-US locale,
fixed demo clock. Board retains the terminal; feature details hide it for more
document space. Git captures the actual workspace element rather than a pixel crop.

Before review:

- Open every image: correct feature and document, useful context, no private
  remnants, no missing/loading states. Do not mistake automated success for approval.
- Capture twice and compare hashes on the same browser/machine. Resolve cursors,
  asynchronous loads and unstable metadata. Browser/font changes need visual review.
- Check `/` and `/features/` at 1440, 390 and 320 px: no overflow, readable copy,
  working section anchors, navigation, keyboard focus and full-size image links.
- Check the deferred `/de/` landing redirect and all new internal documentation links.
- Aim for under 200 KB per delivered WebP. Original PNG is only linked for enlargement.
- When changing the shared mock bridge, run the existing desktop UI suites too.
  Do not add screenshot-only CSS changes to the product UI.

## Ongoing maintenance and publication

When a visible feature changes, check its image and claims together. Update the
fixture, capture recipe, website and affected playbooks/spec in one change set.
Backend-only work does not automatically require new images. Add future features
where their distinctiveness warrants, keeping IDE essentials at the end.

The user accepted the local visual direction on 2026-09-11. It remains **local only**;
publication was not requested. No push or deployment:
a push to main deploys the website. General standing permissions remain unchanged;
the current local-only request governs this change. The app itself needs no restart.

Next review: does the skill image communicate reuse clearly? Is the full-width
lead on Features worth the space? Are any details too small at the two-column size?

UI change check, Spec 015: the new workspace entry changes the dashboard, not any
of the eight current project-window motifs. Keep the current images; verify
them with the capture recipe. Add a workspace image and update feature claims
after the new capability is accepted, rather than implying that aggregated boards
or team sync already exist. Screenshot upkeep is part of each visible UI change,
not a separate optional cleanup task.

Verification on 2026-09-11: all eight captures match the existing assets on the
repeat run. The initial MCP capture showed a tiny raster-only difference; inspect
such differences before replacing assets. Marketing build and responsive landing/
Features checks pass. No website publication in this change.
