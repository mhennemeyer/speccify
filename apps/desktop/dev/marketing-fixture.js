// Curated public demo. Only applied by dev/mock.html?marketing=1.
export const marketingProject = "/Users/demo/Projects/OrbitNotes";

export function installMarketingFixture({ responses, tickets, base, gitState, branchState, emit }) {
  const taskTexts = ["Suchindex für Titel und Text", "Treffer mit Vorschau anzeigen", "Tastaturbedienung prüfen"];
  const definitions = [
    [7, "markdown-export", "Notizen als Markdown exportieren", "Backlog", 0, 3],
    [8, "shortcuts", "Tastenkürzel für den Alltag", "Backlog", 0, 4],
    [5, "suche", "Notizen schnell wiederfinden", "Doing", 2, 3],
    [6, "tags", "Notizen mit Tags ordnen", "Doing", 3, 3],
    [3, "editor", "Ein ruhiger Markdown-Editor", "Done", 4, 4],
    [4, "entwuerfe", "Entwürfe automatisch sichern", "Done", 3, 3],
  ];
  tickets.splice(0, tickets.length, ...definitions.map(([number, slug, title, station, done, total]) => {
    const id = `${String(number).padStart(3, "0")}-${slug}`;
    const tasks = Array.from({ length: total }, (_, index) => ({ index, done: index < done,
      text: number === 5 ? taskTexts[index] : ["Verhalten spezifizieren", "Oberfläche umsetzen", "Änderung prüfen", "Abnahme vorbereiten"][index] }));
    return { ...base, id, number, file: `.agent/specs/${id}/SPEC.md`, title, station,
      parent: null, order: number, created: "2026-09-01", tasks_done: done, tasks_total: total, tasks,
      ready: number === 6, needs_human: number === 6,
      body: `## Why\nNotizen sollen sich so schnell finden lassen wie Gedanken entstehen.\n\n## What\nEine lokale Suche über Titel und Inhalt. Treffer zeigen eine kurze Vorschau.\n\n## Tasks\n${tasks.map(t => `- [${t.done ? "x" : " "}] ${t.text}`).join("\n")}\n\n## Verification\nSuchindex und Trefferliste geprüft. Tastaturbedienung folgt.`,
    };
  }));
  responses.project_board_kpis = () => ({ run_count: 0, tokens_in: 0, tokens_out: 0, duration_ms: 0, recent: [] });
  responses.project_ticket_history = () => [];
  responses.project_ticket_questions = () => [];
  responses.project_actions = () => ({ actions: [
    { name: "Tests", command: "pnpm test", description: "Lokale Tests ausführen", source: "actions.json", confirmed: true, toolbar: true, target: "local" },
  ], pending: [] });
  const settings = responses.get_settings;
  responses.get_settings = () => ({ ...settings(), theme: "dark" });
  responses.terminal_open = ({ id }) => {
    window.__SPECCIFY_MOCK__.marketingTerminal = id;
    return { cwd: marketingProject, startup: null };
  };
  window.__SPECCIFY_MOCK__.marketingTerminalOutput = () => emit("term-out", {
    id: window.__SPECCIFY_MOCK__.marketingTerminal,
    data: "\x1b[2J\x1b[H\x1b[36mOrbitNotes\x1b[0m  ·  feature/search\r\n\r\n$ pnpm test\r\n\x1b[32m  ✓ search-index.test.ts\r\n  ✓ search-results.test.ts\x1b[0m\r\n\r\n  Demo-Lauf · Suchindex und Trefferliste geprüft.\r\n\x1b[?25l",
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
  responses.project_git_log = () => [{ hash: "8f3a021d", short: "8f3a021", author: "Demo Team", date: "2026-09-01T10:00:00Z", subject: "feat: Entwürfe automatisch sichern" }];
  responses.project_git_file_log = () => [];
  responses.project_git_diff = () => "diff --git a/src/search/index.ts b/src/search/index.ts\n--- a/src/search/index.ts\n+++ b/src/search/index.ts\n@@ -1,4 +1,6 @@\n export function search(notes, query) {\n-  return notes.filter(note => note.title.includes(query));\n+  const term = query.trim().toLocaleLowerCase();\n+  return notes.filter(note =>\n+    `${note.title} ${note.body}`.toLocaleLowerCase().includes(term)\n+  );\n }\n";
}
