---
name: project-checks
description: Run Speccify's verification set — targeted first, then Rust, Python, TypeScript, formatting, browser regressions and the marketing build — and report counts that can go into a spec or commit. Use before a commit, a push, a release, or when the user asks "sind die Tests grün", "prüf den Stand", "run the checks".
---

# Project checks

Targeted tests first, the broad set after the core path works. Write logs to the
scratchpad, not into the repo. Report numbers ("134 passed, 3 ignored"), not
"green". A skipped check is reported as skipped.

## The set

| Area | Command | Notes |
| --- | --- | --- |
| Desktop Rust | `cargo test -p speccify-desktop` | Sum all `test result:` lines; the last one is a doc-test with 0 tests. |
| Rust format | `cargo fmt --check` | |
| Desktop frontend | `pnpm --filter speccify-desktop typecheck` | |
| Python | `uv run pytest` | See "venv" below. Some tests start local servers and fail inside a sandbox. |
| Python lint | `uv run ruff check .` and `uv run ruff format --check .` | |
| Update manifest | `uv run pytest tests/test_update_manifest.py` | Needs `minisign` installed for the real signature check. |
| Website | `pnpm marketing:build` | Must list the new page under `apps/marketing/dist/`. |
| Drift | `speccify verify` | Lock, bundle, expansion and tool drift. Never edit `expansions.yaml` status by hand. |

Rust and the Python/TypeScript group can run in parallel. **Do not** run
`cargo test` in parallel with a native app build (`dev.sh --app`): the doc-test
step failed that way on 2026-09-11 and passed in isolation.

## venv: "No module named speccify_core"

`uv run` sets the macOS hidden flag on the `.pth` files. Fix and run directly:

```sh
sh scripts/fix-venv-hidden.sh
.venv/bin/python -m pytest
.venv/bin/speccify verify      # same failure shows as "No module named speccify_cli"
```

`uv run` hides the files again, so repeat the fix after every `uv run …`. With
the project's `addopts = -q` an extra `-q` drops the summary line: run plain
`.venv/bin/python -m pytest` to get "N passed", and check the exit code.

`speccify verify` lists tools without an implementation for this platform as
notes below its `ok` line; those are not drift.

## Browser regressions

`scripts/test_*.mjs` drive the real React components against
`apps/desktop/dev/mock.html` with Playwright and installed Chrome
(`SPECCIFY_TEST_BROWSER=chromium` for bundled Chromium).

- Scripts with `--serve` (`test_updates.mjs`, `test_markdown_mermaid.mjs`) or
  with a built-in server (`test_terminal_preferences.mjs`,
  `test_agent_settings.mjs`) start their own Vite on 127.0.0.1:1421.
- All others expect a server at `SPECCIFY_MOCK_URL`
  (default `http://127.0.0.1:1421/dev/mock.html`). Start one yourself on a free
  port and stop it afterwards; do not take over the user's dev server or port:

  ```sh
  pnpm --dir apps/desktop exec vite --host 127.0.0.1 --port 5199 --strictPort
  SPECCIFY_MOCK_URL=http://127.0.0.1:5199/dev/mock.html node scripts/test_workspace_ui.mjs
  ```

- Run the scripts that cover the changed area; before a release run all that CI
  runs (`.github/workflows/ci.yml`, job with "playwright install") plus the
  area-specific ones.
- A new regression must **fail against the old code**. Check it once by
  restoring the previous file version, then restore the fix
  (`git show <commit>~1:<path> > <path>` … `git checkout <path>`).
- Playwright scrolls targets into view before clicking. Assertions about
  "visible without scrolling" must set the scroll position themselves.

## Housekeeping

- iCloud conflict copies (`name 2.ext`) next to the original cause odd tool
  behaviour; untracked ones with the original present may be deleted.
- Playwright MCP writes `.playwright-mcp/` into the repo root: remove it after use.
- CI is the Windows and Linux evidence. It is not an installation or UI
  acceptance on those systems; say so in verification texts.
