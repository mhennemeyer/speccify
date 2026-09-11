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
  responses.workspace_discover = ({ path }) => {
    if (path.includes("missing")) throw Error("Kein Verzeichnis: missing");
    const entries = read(); const workspace = entries[0] ?? initial();
    if (entries.length) workspace.revision++;
    if (path.includes("partial")) { workspace.partial = true; workspace.warnings = ["Maximale Suchtiefe erreicht"]; }
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
