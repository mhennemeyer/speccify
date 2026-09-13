---
name: agent-ui
description: Ask the human through the Speccify app — quick choices with ask_bo, custom HTML/Tailwind forms and displays with show_ui, reusable UIs saved next to this skill. Use when a decision, a selection or a preview is faster on screen than in the terminal.
metadata:
  speccify-workflow-version: "1"
---

# agent-ui

The app hosts the MCP `speccify-desktop-ui` (see `.mcp.json`). Two tools:

- `ask_bo` — structured and fast: `kind: buttons` (one choice), `multi_select`
  (checkboxes), `form` (question list with recommended defaults).
- `show_ui` — an HTML fragment rendered in the app, Tailwind utility classes
  work, no external scripts. `mode: ask` (default) waits for the answer,
  `mode: show` only displays. Reusable UIs: save the HTML under
  `.agent/skills/agent-ui/ui/<name>.html` (or in your own skill) and call
  `show_ui` with `file: <absolute path>`.

How the answer comes back (`{answered: true, values}`):

- A `<form>` submit sends every field by `name`; checkboxes sharing a name
  become an array; the submit button's own `name`/`value` is included.
- A click on any element with `data-answer="…"` sends `{answer: "…"}` — the
  shortest way to a yes/no.
- On timeout (default 300 s) the UI stays open; poll `ui_result` with the
  `interaction_id` instead of showing it again.

Patterns (copy, adapt):

```html
<!-- yes/no -->
<p class="mb-3 text-sm">Deploy v1.4 to staging now?</p>
<div class="flex gap-2">
  <button data-answer="yes" class="rounded bg-emerald-600 px-3 py-1.5 text-white">Yes</button>
  <button data-answer="no" class="rounded border px-3 py-1.5">No</button>
</div>
```

```html
<!-- single choice + multi select + free text in one form -->
<form class="space-y-3 text-sm">
  <fieldset><legend class="font-medium">Target</legend>
    <label class="block"><input type="radio" name="target" value="staging" checked> staging</label>
    <label class="block"><input type="radio" name="target" value="prod"> prod</label>
  </fieldset>
  <fieldset><legend class="font-medium">Services</legend>
    <label class="block"><input type="checkbox" name="services" value="api"> api</label>
    <label class="block"><input type="checkbox" name="services" value="web"> web</label>
  </fieldset>
  <label class="block">Release note <input name="note" class="mt-1 w-full rounded border px-2 py-1"></label>
  <button class="rounded bg-slate-800 px-3 py-1.5 text-white">Send</button>
</form>
```

```html
<!-- question list: one input per question -->
<form class="space-y-2 text-sm">
  <label class="block">Which database? <input name="db" placeholder="postgres" class="mt-1 w-full rounded border px-2 py-1"></label>
  <label class="block">Keep the old API? <select name="keep_api" class="mt-1 rounded border px-2 py-1"><option>yes</option><option>no</option></select></label>
  <button class="rounded bg-slate-800 px-3 py-1.5 text-white">Answer</button>
</form>
```

```html
<!-- display only (mode: show): a table or a progress bar -->
<table class="w-full text-sm"><thead><tr class="text-left"><th>Check</th><th>Result</th></tr></thead>
<tbody><tr><td>Tests</td><td class="text-emerald-700">108 passed</td></tr><tr><td>Lint</td><td>clean</td></tr></tbody></table>
```

Keep UIs small and self-contained: plain HTML, Tailwind classes, at most a
few inline `<script>` lines that call `speccify.submit({...})` for custom
flows. Do not load remote resources; the frame is sandboxed. Ask once, then
act on the answer; record the decision in the spec.
