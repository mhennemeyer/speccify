// Isolated UI contract fixture; never connected to the native workspace store.
// With ?marketing=1 the public OrbitNotes demo workspace is used instead of the
// regression data (app-screenshots skill); paths stay under /Users/demo.
import { installWorkspaceKnowledgeFixture } from "./workspace-knowledge-fixture.js";
export function installWorkspaceFixture(responses) {
  const key = "speccify.test.workspaces";
  const marketing = new URLSearchParams(location.search).has("marketing");
  const root = marketing ? "/Users/demo/Projects" : "/private/tmp/demo-workspace";
  const marketingInitial = () => ({ id: "workspace-orbit", name: "Projects", root, revision: 3, partial: false, warnings: [],
    projects: [
      { id: "project-orbit", name: "OrbitNotes", repository_ids: ["repo-app", "repo-sync"] },
      { id: "project-sync", name: "orbitnotes-sync", repository_ids: [] },
      { id: "project-site", name: "Website", repository_ids: ["repo-site"] },
    ],
    repositories: [
      { id: "repo-app", name: "OrbitNotes", common_dir: `${root}/OrbitNotes/.git`, default_project_id: "project-orbit", worktrees: [
        { id: "tree-app", path: `${root}/OrbitNotes`, relative_path: "OrbitNotes", markers: [".agent/agent.md", "speccify.yaml"], available: true },
      ] },
      { id: "repo-sync", name: "orbitnotes-sync", common_dir: `${root}/orbitnotes-sync/.git`, default_project_id: "project-sync", worktrees: [
        { id: "tree-sync", path: `${root}/orbitnotes-sync`, relative_path: "orbitnotes-sync", markers: [".agent/agent.md"], available: true },
      ] },
      { id: "repo-site", name: "orbitnotes.app", common_dir: `${root}/orbitnotes.app/.git`, default_project_id: "project-site", worktrees: [
        { id: "tree-site", path: `${root}/orbitnotes.app`, relative_path: "orbitnotes.app", markers: ["AGENTS.md"], available: true },
      ] },
    ],
  });
  const marketingSpecs = tree => {
    const template = responses.project_board({ project: `${root}/OrbitNotes` })[0];
    const spec = (number, slug, title, station, done, total, texts) => ({ ...template, id: `${String(number).padStart(3, "0")}-${slug}`, number,
      file: `.agent/specs/${String(number).padStart(3, "0")}-${slug}/SPEC.md`, title, station, order: number, created: "2026-09-01", parent: null,
      ready: false, needs_human: false, tasks_done: done, tasks_total: total,
      tasks: texts.map((text, index) => ({ index, text, done: index < done })),
      body: `## Why\n${title}.\n\n## Tasks\n${texts.map((text, index) => `- [${index < done ? "x" : " "}] ${text}`).join("\n")}` });
    if (tree.id === "tree-app") return responses.project_board({ project: tree.path });
    if (tree.id === "tree-sync") return [
      spec(9, "sync-conflicts", "Resolve sync conflicts safely", "Doing", 1, 3, ["Detect concurrent edits", "Keep both versions", "Show a merge preview"]),
      spec(10, "offline-queue", "Queue changes while offline", "Backlog", 0, 2, ["Persist the queue", "Replay in order"]),
    ];
    return [spec(2, "download-page", "Download page for all platforms", "Done", 3, 3, ["List installers", "Explain first launch", "Link release notes"])];
  };
  const initial = () => marketing ? marketingInitial() : ({ id: "workspace-demo", name: "demo-workspace", root, revision: 1, partial: false, warnings: [],
    projects: [{ id: "project-api", name: "API", repository_ids: ["repo-api"] }, { id: "project-web", name: "Web", repository_ids: ["repo-web"] }],
    repositories: [
      { id: "repo-api", name: "API", common_dir: `${root}/api/.git`, default_project_id: "project-api", worktrees: [
        { id: "tree-api", path: `${root}/api`, relative_path: "api", markers: [".agent/agent.md"], available: true },
        { id: "tree-feature", path: `${root}/api-search`, relative_path: "api-search", markers: [".agent/agent.md"], available: true },
      ] },
      { id: "repo-web", name: "Web", common_dir: `${root}/web/.git`, default_project_id: "project-web", worktrees: [
        { id: "tree-web", path: `${root}/web`, relative_path: "web", markers: ["speccify.yaml"], available: true },
      ] },
    ],
  });
  const read = () => JSON.parse(localStorage.getItem(key) ?? "[]");
  const write = value => localStorage.setItem(key, JSON.stringify(value));
  const scope = workspace => {
    if (!workspace) return workspace;
    const result = structuredClone(workspace);
    const depth = responses.get_settings().project_discovery_depth ?? 1;
    for (const repo of result.repositories) repo.worktrees = repo.worktrees.filter(tree => tree.path.slice(result.root.length).split("/").filter(Boolean).length <= depth);
    result.repositories = result.repositories.filter(repo => repo.worktrees.length);
    for (const group of result.projects) group.repository_ids = group.repository_ids.filter(id => result.repositories.some(repo => repo.id === id));
    return result;
  };
  window.__SPECCIFY_MOCK__.workspaceOpened = [];
  window.__SPECCIFY_MOCK__.workspaceStale = false;
  responses.workspace_list = () => read().map(scope);
  responses.workspace_window_open = ({ workspaceId }) => { window.__SPECCIFY_MOCK__.workspaceOpened.push({ workspaceId, window: true }); };
  responses.workspace_window_current = () => scope(read()[0]);
  responses.workspace_registers = () => JSON.parse(localStorage.getItem(`${key}.registers`) ?? "null");
  responses.workspace_register_save = ({ manifest, bindings }) => {
    const value = { manifest: JSON.parse(manifest), bindings };
    const seen = new Set();
    for (const source of value.manifest.sources) {
      if (!bindings[source.id]?.length) throw Error("Registerbindung fehlt");
      for (const id of bindings[source.id]) { if (seen.has(id)) throw Error("Checkout darf nur einem Register zugeordnet sein"); seen.add(id); }
    }
    localStorage.setItem(`${key}.registers`, JSON.stringify(value)); return value;
  };
  responses.workspace_register_import = () => responses.workspace_registers()?.manifest;
  responses.workspace_agent_context = () => {
    const workspace = scope(read()[0]);
    return { root: workspace.root, revision: workspace.revision, markdown: `# Workspace context\n${JSON.stringify(workspace, null, 2)}` };
  };
  responses.workspace_resolve_target = ({ worktreeId }) => {
    if (window.__SPECCIFY_MOCK__.missingTarget === worktreeId) throw Error("Worktree nicht verfügbar");
    if (worktreeId === `root:${read()[0].id}`) return read()[0].root;
    return read()[0].repositories.flatMap(repo => repo.worktrees).find(tree => tree.id === worktreeId).path;
  };
  const shell = new URLSearchParams(location.search).has("workspace-shell");
  if (shell && !read().length) {
    const workspace = initial();
    if (!marketing) {
      workspace.projects.push({ id: "project-infra", name: "Infrastructure", repository_ids: ["repo-infra"] });
      workspace.repositories.push({ id: "repo-infra", name: "Infra", common_dir: `${root}/infra/.git`, default_project_id: "project-infra", worktrees: [{ id: "tree-infra", path: `${root}/infra`, relative_path: "infra", available: true, markers: [] }] });
    }
    write([workspace]);
  }
  responses.workspace_board = async ({ workspaceId }) => {
    const workspace = scope(read().find(entry => entry.id === workspaceId));
    if (!workspace) throw Error("Workspace nicht gefunden");
    if (marketing) {
      const specs = workspace.repositories.flatMap(repo => repo.worktrees.flatMap(tree => {
        const project = workspace.projects.find(project => project.repository_ids.includes(repo.id));
        return marketingSpecs(tree).map(spec => ({ key: JSON.stringify([workspace.id, repo.id, tree.id, spec.file]), project_id: project.id, project_name: project.name,
          repository_id: repo.id, repository_name: repo.name, worktree_id: tree.id, worktree_path: tree.path, worktree_label: tree.relative_path, spec }));
      }));
      return { workspace_id: workspace.id, root: workspace.root, revision: workspace.revision, captured_at: Date.parse("2026-09-01T10:00:00Z"), specs, partial: false, warnings: [] };
    }
    const specs = workspace.repositories.flatMap(repo => repo.worktrees.map(tree => {
      const project = workspace.projects.find(project => project.repository_ids.includes(repo.id));
      const file = ".agent/specs/001-shared/SPEC.md";
      const station = tree.id === "tree-feature" ? "Doing" : tree.id === "tree-web" ? "Done" : "Backlog";
      return { key: JSON.stringify([workspace.id, repo.id, tree.id, file]), project_id: project.id, project_name: project.name,
        repository_id: repo.id, repository_name: repo.name, worktree_id: tree.id, worktree_path: tree.path, worktree_label: tree.relative_path,
        spec: { file, id: "001-shared", number: 1, title: "Shared feature", station, order: 1, created: "2026-09-11", ready: true, needs_human: true,
          tasks_done: 1, tasks_total: 2, tasks: [], parent: null, assignee: null, open_question: null, archived: false,
          body: `# Shared feature\n\nOnly ${tree.relative_path}.\n\n- [x] Tested\n- [ ] Review` } };
    }));
    const flags = window.__SPECCIFY_MOCK__;
    if (flags.boardDelay) await new Promise(resolve => setTimeout(resolve, flags.boardDelay));
    if (flags.boardError) throw Error("Workspace nicht erreichbar");
    if (flags.boardUnknown && specs[0]) specs[0].spec.station = "Review";
    return { workspace_id: workspace.id, root: workspace.root, revision: workspace.revision, captured_at: Date.now(), specs,
      partial: !!flags.boardPartial, warnings: flags.boardPartial ? ["Nicht verfügbar: api-feature"] : [] };
  };
  responses.workspace_discover = ({ path }) => {
    if (path.includes("missing")) throw Error("Kein Verzeichnis: missing");
    const entries = read(); const workspace = entries[0] ?? initial();
    if (entries.length) workspace.revision++;
    if (path.includes("partial")) { workspace.partial = true; workspace.warnings = ["Suchbudget erreicht bei api/deep/project. Dieser und weitere ausstehende Ordner wurden nicht durchsucht."]; }
    else { workspace.partial = false; workspace.warnings = []; }
    write([workspace]); return scope(workspace);
  };
  responses.workspace_edit = ({ expectedRevision, change }) => {
    const [workspace] = read();
    if (window.__SPECCIFY_MOCK__.workspaceStale) { workspace.revision++; write([workspace]); window.__SPECCIFY_MOCK__.workspaceStale = false; }
    if (workspace.revision !== expectedRevision) throw Error("WORKSPACE_CHANGED: Neu laden und erneut prüfen.");
    if (change.kind === "group") {
      for (const project of workspace.projects) project.repository_ids = project.repository_ids.filter(id => !change.repository_ids.includes(id));
      workspace.projects.push({ id: `group-${workspace.revision}`, name: change.name, repository_ids: change.repository_ids });
    } else if (change.kind === "rename") workspace.projects.find(project => project.id === change.project_id).name = change.name;
    else {
      for (const project of workspace.projects) project.repository_ids = project.repository_ids.filter(id => id !== change.repository_id);
      const repo = workspace.repositories.find(repo => repo.id === change.repository_id);
      workspace.projects.find(project => project.id === repo.default_project_id).repository_ids.push(repo.id);
    }
    workspace.revision++; write([workspace]); return workspace;
  };
  responses.workspace_open = ({ workspaceId, worktreeId }) => { window.__SPECCIFY_MOCK__.workspaceOpened.push({ workspaceId, worktreeId }); return root; };
  // Spec 027: ein Einstieg. Pfade auf "/legacy" gelten als Einzelprojekt (Repo-Wurzel),
  // alles andere als Elternordner mit mehreren Repos → gespeicherter Workspace + Fenster.
  responses.folder_open = ({ path }) => {
    if (path.endsWith("/legacy")) { window.__SPECCIFY_MOCK__.workspaceOpened.push({ path }); return { kind: "project", root: path }; }
    const workspace = responses.workspace_discover({ path });
    window.__SPECCIFY_MOCK__.workspaceOpened.push({ workspaceId: workspace.id, window: true });
    return { kind: "workspace", workspace };
  };
  responses.project_recent = () => [root + "/legacy"];
  responses.project_open = ({ path }) => { window.__SPECCIFY_MOCK__.workspaceOpened.push({ path }); return path; };
  responses.ask_bo_pending = () => [];
  const settings = responses.get_settings;
  responses.get_settings = () => ({ ...settings(), theme: "dark", terminal_autostart_command: "" });
  if (shell && !marketing) {
    const calls = window.__SPECCIFY_MOCK__.workspaceCalls = [];
    const files = new Map();
    responses.project_tree = ({ project, dir: path }) => {
      if (project !== root) return path ? [] : [{ name: "shared.txt", path: "shared.txt", is_dir: false, size: 20 }];
      const entry = (name, path, is_dir = false) => ({ name, path, is_dir, size: 20 });
      if (!path) return [entry("Resourcen", "Resourcen", true), entry("notes.md", "notes.md"), entry("api", "api", true)];
      if (path === "Resourcen") return [entry("nested", "Resourcen/nested", true)];
      if (path === "Resourcen/nested") return [entry("info.md", "Resourcen/nested/info.md")];
      if (path === "api") return [entry("shared.txt", "api/shared.txt")];
      return [];
    };
    responses.project_read_file = ({ project, file }) => files.get(`${project}/${file}`) ?? `Only ${project === root && file.startsWith("api/") ? `${root}/api` : project}\n`;
    responses.project_write_file = ({ project, file, content, expectedContent }) => {
      const path = `${project}/${file}`;
      const baseline = project === root && file.startsWith("api/") ? `${root}/api` : project;
      const current = files.get(path) ?? `Only ${baseline}\n`;
      if (expectedContent !== undefined && current !== expectedContent) throw Error("Datei wurde zwischenzeitlich geändert. Entwurf bleibt erhalten.");
      files.set(path, content);
    };
    responses.terminal_open = ({ id, cwd }) => ({ cwd, startup: null });
    const originalBoard = responses.workspace_board;
    const done = new Set();
    responses.workspace_board = async args => {
      const snapshot = await originalBoard(args);
      for (const entry of snapshot.specs) {
        const review = done.has(entry.worktree_path);
        entry.spec.tasks = [{ index: 0, text: "Tested", done: true }, { index: 1, text: "Review", done: review }];
        entry.spec.tasks_done = review ? 2 : 1;
        entry.spec.body = `Only ${entry.worktree_label}.\n\n- [x] Tested\n- [${review ? "x" : " "}] Review`;
      }
      return snapshot;
    };
    responses.project_board = async ({ project }) => (await responses.workspace_board({ workspaceId: "workspace-demo" })).specs.filter(entry => entry.worktree_path === project).map(entry => entry.spec);
    responses.project_spec_toggle_task = ({ project, done: checked }) => { if (checked) done.add(project); else done.delete(project); };
    responses.project_ticket_create = () => ".agent/specs/002-shared-task/SPEC.md";
    if (new URLSearchParams(location.search).has("workspace-registers")) {
      const statuses = window.__SPECCIFY_MOCK__.workspaceRegisters = Object.fromEntries([
        ["api", "migratable"], ["api-search", "blocked"], ["web", "detached"], ["infra", "none"],
      ].map(([name, mode]) => [`${root}/${name}`, {
        mode, branch: "specs", remote: true, code_branch: "main", tracked_in_code: mode === "migratable" || mode === "blocked",
        ahead: 0, behind: 0, unsent: 0, rebasing: false, conflicts: [], last_sync: null, last_error: null,
        reason: mode === "blocked" ? "Alter Code-Branch trackt Specs noch." : "Register für dieses Repository einrichten.",
      }]));
      responses.project_register_status = ({ project }) => {
        if (window.__SPECCIFY_MOCK__.registerStatusError === project) throw Error("Status nicht erreichbar");
        return structuredClone(statuses[project]);
      };
      responses.project_register_setup = ({ project }) => {
        if (window.__SPECCIFY_MOCK__.registerSetupError === project) throw Error("Push fehlgeschlagen");
        Object.assign(statuses[project], { mode: "mounted", tracked_in_code: false, reason: null });
        return structuredClone(statuses[project]);
      };
      responses.project_register_sync = ({ project }) => ({ ...statuses[project], last_sync: "2026-09-15T10:00:00Z" });
      responses.project_register_resolve = ({ project }) => {
        Object.assign(statuses[project], { rebasing: false, conflicts: [], ahead: 0, behind: 0 });
        return structuredClone(statuses[project]);
      };
    }
    if (new URLSearchParams(location.search).has("workspace-knowledge")) installWorkspaceKnowledgeFixture(responses, root, () => scope(read()[0]));
    for (const [command, handler] of Object.entries(responses)) {
      responses[command] = args => { calls.push({ command, args: structuredClone(args ?? {}) }); return handler(args ?? {}); };
    }
  }
}
