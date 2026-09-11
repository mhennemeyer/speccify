// Curated public demo. Only applied by dev/mock.html?marketing=1.
export const marketingProject = "/Users/demo/Projects/OrbitNotes";

export function installMarketingFixture({ responses, tickets, base, gitState, branchState, emit }) {
  const skillBody = `# Reliable Markdown export

Turn local notes into portable Markdown without losing metadata.

## When to use

Ship an export feature or move notes between apps. Keep the procedure reusable;
put the destination and naming rules in the project section below.

## Execute

1. Read the note format and the validate-note tool contract.
2. Implement the tool for this machine, then run its examples.
3. Export a sample containing tags, links and non-ASCII text.

## Evaluate

Re-import the sample. Compare titles, tags and content with the original.
A passing tool check does not replace this end-to-end check.

## In this project

OrbitNotes exports to exports/. Use UTF-8 and ISO dates. Never overwrite an
existing export without confirmation.
`;
  const toolBody = `# validate-note

Check a note before export. One contract; an implementation for each platform.

## Inputs

\`path\` — relative path to a Markdown note.

## Outputs

\`ok\` — boolean. \`errors\` — list of invalid or missing fields.

## Effects

Reads one local file. No writes. No network access.

## Examples

| Input | Expected result |
| --- | --- |
| fixtures/valid.md | ok: true, errors: [] |
| fixtures/no-title.md | ok: false, errors: ["title is required"] |

## Verify

Run \`speccify tool check validate-note\` after implementing the contract.
The platform badges shown here are demo data, not a live test result.
`;
  const documents = {
    ".agent/skills/markdown-export/SKILL.md": skillBody,
    ".agent/skills/search-quality/SKILL.md": "# Search quality\n\nEvaluate ranking with exact matches, tags and Unicode queries.\n",
    ".agent/skills/release-check/SKILL.md": "# Release check\n\nReview the changelog, verify artifacts and ask for release approval.\n",
    ".agent/tools/validate-note/TOOL.md": toolBody,
    ".agent/tools/check-links/TOOL.md": "# check-links\n\nReport broken local links before export.\n",
    ".agent/playbooks/product.md": `# A quieter place for your notes

## Product direction

Local-first notes. Fast search. Portable Markdown. No account needed.

## Working agreements

- Specs describe a change; this playbook describes the product.
- Move a spec to Doing before implementation starts.
- Keep acceptance criteria and verification beside the work.

## Current focus

Search is in progress. Tagging is ready for human review.
Markdown export is next, using the shared markdown-export skill.

## UI map

Library → Notes → Editor\n\nSearch → Results → Preview\n\nExport → Destination → Validation
`,
    ".agent/playbooks/release.md": "# Release checklist\n\nReview completed specs, run tests, inspect artifacts and ask for approval before publishing.\n",
    ".agent/agent.md": "# OrbitNotes project guidance\n\nRead the product playbook and the active spec. Reuse project skills. Keep tool implementations local. Record verification before asking for acceptance.\n",
    "README.md": "# OrbitNotes\n\nA quieter place for your notes.\n\n## Development\n\nRun `pnpm dev` to start the app and `pnpm test` to check the search index.\n\n## Project knowledge\n\nSpecs, skills, tools and playbooks live in `.agent/`.\n",
    "src/search/index.ts": "export interface Note {\n  title: string;\n  body: string;\n}\n\nexport function search(notes: Note[], query: string): Note[] {\n  const term = query.trim().toLocaleLowerCase();\n  if (!term) return notes;\n\n  return notes.filter(note =>\n    `${note.title} ${note.body}`.toLocaleLowerCase().includes(term)\n  );\n}\n",
    "package.json": '{ "name": "orbit-notes", "private": true }\n',
  };
  responses.project_read_file = ({ file }) => {
    if (!(file in documents)) throw Error(`Missing public demo document: ${file}`);
    return documents[file];
  };
  responses.project_tree = ({ dir }) => {
    const prefix = dir ? `${dir}/` : "";
    const entries = new Map();
    for (const file of Object.keys(documents)) {
      if (!file.startsWith(prefix)) continue;
      const rest = file.slice(prefix.length), name = rest.split("/")[0];
      if (!entries.has(name)) entries.set(name, { name, path: prefix + name, is_dir: rest.includes("/"), size: documents[file].length });
    }
    return [...entries.values()].sort((a, b) => Number(b.is_dir) - Number(a.is_dir) || a.name.localeCompare(b.name));
  };
  responses.project_file_info = ({ file }) => ({ path: file, size: documents[file]?.length ?? 0,
    modified: "2026-09-01T10:00:00Z", lines: documents[file]?.split("\n").length ?? 0, binary: false });
  const source = "/Users/demo/Libraries/team-skills";
  responses.sources_list = () => [{ name: "Team skills", location: source, kind: "dir", scope: "project", path: source, state: "ready", detail: null }];
  responses.project_skill_sources = () => ({ default: source, sources: [] });
  responses.project_skills = () => [
    { name: "markdown-export", description: "Portable notes, verified before they leave the project", origin: { source, version: "1.2.0", expanded: "2026-09-01", tools: ["validate-note"] } },
    { name: "search-quality", description: "Evaluate ranking, previews and Unicode queries", origin: null },
    { name: "release-check", description: "A repeatable path from change to release", origin: { source, version: "1.0.0", expanded: "2026-09-01", tools: [] } },
  ].map(skill => ({ ...skill, file: `.agent/skills/${skill.name}/SKILL.md` }));
  responses.source_browse = () => responses.project_skills().map(skill => ({ ...skill, category: "Product", id: `@demo/${skill.name}` }));
  responses.source_skill_read = ({ file }) => responses.project_read_file({ file });
  responses.project_tools = () => [
    { name: "validate-note", description: "Validate Markdown metadata before export", from: ["markdown-export"], platforms: [{ name: "macos", status: "verified", checked: "2026-09-01" }, { name: "windows", status: null, checked: null }], files: ["macos.sh"] },
    { name: "check-links", description: "Find broken local links", from: ["markdown-export"], platforms: [{ name: "macos", status: null, checked: null }], files: [] },
  ].map(tool => ({ ...tool, file: `.agent/tools/${tool.name}/TOOL.md` }));
  responses.project_playbooks = () => [
    { file: ".agent/playbooks/product.md", title: "Product direction", description: "Vision, working agreements and UI map" },
    { file: ".agent/playbooks/release.md", title: "Release checklist", description: "A repeatable path to a reviewed release" },
  ];
  responses.project_agent_files = () => [".agent/agent.md"];
  responses.project_mcps = () => ({
    claude_servers: { speccify: { command: "speccify-mcp", args: [], type: "stdio" } },
    codex_servers: { speccify: { command: "speccify-mcp", args: [] }, "speccify-exec": { url: "http://127.0.0.1:8765/mcp" } },
    claude_allow: ["Bash(pnpm test*)"], claude_allow_local: [],
  });
  responses.project_action_run = ({ runId }) => {
    window.__SPECCIFY_MOCK__.actionStarts.push(runId);
    emit("action-output", { run_id: runId, line: "Demo benchmark · synthetic values, not product measurements" });
    emit("action-output", { run_id: runId, line: JSON.stringify({ kind: "chart", series: [{ name: "Search latency (ms)", points: [[100, 2], [250, 4], [500, 7], [750, 10], [1000, 13]] }] }) });
    emit("action-exit", { run_id: runId, exit_code: 0, duration_ms: 1000, error: null });
    return null;
  };
  const taskTexts = ["Index note titles and content", "Show matches with a preview", "Check keyboard navigation"];
  const definitions = [
    [7, "markdown-export", "Export notes as Markdown", "Backlog", 0, 3],
    [8, "shortcuts", "Everyday keyboard shortcuts", "Backlog", 0, 4],
    [5, "suche", "Find the note you need", "Doing", 2, 3],
    [6, "tags", "Organize notes with tags", "Doing", 3, 3],
    [3, "editor", "A calm Markdown editor", "Done", 4, 4],
    [4, "entwuerfe", "Keep drafts safe", "Done", 3, 3],
  ];
  tickets.splice(0, tickets.length, ...definitions.map(([number, slug, title, station, done, total]) => {
    const id = `${String(number).padStart(3, "0")}-${slug}`;
    const tasks = Array.from({ length: total }, (_, index) => ({ index, done: index < done,
      text: number === 5 ? taskTexts[index] : ["Specify the behavior", "Build the interface", "Verify the change", "Prepare for review"][index] }));
    return { ...base, id, number, file: `.agent/specs/${id}/SPEC.md`, title, station,
      parent: null, order: number, created: "2026-09-01", tasks_done: done, tasks_total: total, tasks,
      ready: number === 6, needs_human: number === 6,
      body: `## Why\nFind your notes as quickly as your thoughts arrive.\n\n## What\nSearch titles and content locally. Show a short preview for each match.\n\n## Tasks\n${tasks.map(t => `- [${t.done ? "x" : " "}] ${t.text}`).join("\n")}\n\n## Verification\nDemo: index and results checked. Keyboard review is next.`,
    };
  }));
  responses.project_board_kpis = () => ({ run_count: 0, tokens_in: 0, tokens_out: 0, duration_ms: 0, recent: [] });
  responses.project_ticket_history = () => [];
  responses.project_ticket_questions = () => [];
  responses.project_actions = () => ({ actions: [
    { name: "Tests", command: "pnpm test", description: "Run the local test suite", source: "actions.json", confirmed: true, toolbar: true, target: "local" },
    { name: "Search benchmark", command: "pnpm bench:search", description: "Inspect search latency with a chart", source: "actions.json", confirmed: true, target: "local" },
    { name: "Preview", command: "pnpm preview", description: "Open the local production preview", source: "actions.json", confirmed: true, target: "local" },
  ], pending: [] });
  const settings = responses.get_settings;
  responses.get_settings = () => ({ ...settings(), theme: "dark" });
  responses.terminal_open = ({ id }) => {
    window.__SPECCIFY_MOCK__.marketingTerminal = id;
    return { cwd: marketingProject, startup: null };
  };
  window.__SPECCIFY_MOCK__.marketingTerminalOutput = () => emit("term-out", {
    id: window.__SPECCIFY_MOCK__.marketingTerminal,
    data: "\x1b[2J\x1b[H\x1b[36mOrbitNotes\x1b[0m  ·  feature/search\r\n\r\n$ pnpm test\r\n\x1b[32m  ✓ search-index.test.ts\r\n  ✓ search-results.test.ts\x1b[0m\r\n\r\n  Demo run · Search index and results checked.\r\n\x1b[?25l",
  });
  Object.assign(gitState, { branch: "feature/search", upstream: "origin/feature/search", ahead: 1, behind: 0,
    entries: [
      { path: "src/search/index.ts", index: "M", worktree: ".", untracked: false, conflicted: false, renamed_from: null },
      { path: "src/search/results.tsx", index: "M", worktree: ".", untracked: false, conflicted: false, renamed_from: null },
      { path: "tests/search.test.ts", index: ".", worktree: "M", untracked: false, conflicted: false, renamed_from: null },
    ] });
  branchState.splice(0, branchState.length,
    { name: "feature/search", current: true, upstream: "origin/feature/search", remote: false, worktree: marketingProject },
    { name: "main", current: false, upstream: "origin/main", remote: false, worktree: null });
  responses.project_git_log = () => [{ hash: "8f3a021d", short: "8f3a021", author: "Demo Team", date: "2026-09-01T10:00:00Z", subject: "feat: keep drafts safe" }];
  responses.project_git_file_log = () => [];
  responses.project_git_diff = () => "diff --git a/src/search/index.ts b/src/search/index.ts\n--- a/src/search/index.ts\n+++ b/src/search/index.ts\n@@ -1,4 +1,6 @@\n export function search(notes, query) {\n-  return notes.filter(note => note.title.includes(query));\n+  const term = query.trim().toLocaleLowerCase();\n+  return notes.filter(note =>\n+    `${note.title} ${note.body}`.toLocaleLowerCase().includes(term)\n+  );\n }\n";
}
