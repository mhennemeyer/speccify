// Isolated UI contract fixture; never connected to the native workspace store.
export function installWorkspaceFixture(responses) {
  const key = "speccify.test.workspaces";
  const root = "/private/tmp/demo-workspace";
  const initial = () => ({ id: "workspace-demo", name: "demo-workspace", root, revision: 1, partial: false, warnings: [],
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
  window.__SPECCIFY_MOCK__.workspaceOpened = [];
  window.__SPECCIFY_MOCK__.workspaceStale = false;
  responses.workspace_list = () => read();
  responses.workspace_board = async ({ workspaceId }) => {
    const workspace = read().find(entry => entry.id === workspaceId);
    if (!workspace) throw Error("Workspace nicht gefunden");
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
    return { workspace_id: workspace.id, revision: workspace.revision, captured_at: Date.now(), specs,
      partial: !!flags.boardPartial, warnings: flags.boardPartial ? ["Nicht verfügbar: api-feature"] : [] };
  };
  responses.workspace_discover = ({ path }) => {
    if (path.includes("missing")) throw Error("Kein Verzeichnis: missing");
    const entries = read(); const workspace = entries[0] ?? initial();
    if (entries.length) workspace.revision++;
    if (path.includes("partial")) { workspace.partial = true; workspace.warnings = ["Suchtiefe von 16 Ebenen erreicht. Nicht durchsucht: api/deep/project. Diese Unterordner bei Bedarf separat öffnen."]; }
    else { workspace.partial = false; workspace.warnings = []; }
    write([workspace]); return workspace;
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
  responses.project_recent = () => [root + "/legacy"];
  responses.project_open = ({ path }) => { window.__SPECCIFY_MOCK__.workspaceOpened.push({ path }); return path; };
  responses.ask_bo_pending = () => [];
  const settings = responses.get_settings;
  responses.get_settings = () => ({ ...settings(), theme: "dark", terminal_autostart_command: "" });
}
