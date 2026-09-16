export function installWorkspaceKnowledgeFixture(responses, root, workspace) {
  const paths = [root, `${root}/api`, `${root}/web`];
  const files = new Map();
  for (const project of paths) {
    files.set(`${project}/.agent/skills/review/SKILL.md`, `---\nname: review\n---\n# Review\nRead only ${project}.`);
    files.set(`${project}/.agent/tools/check/TOOL.md`, `---\nname: check\n---\n# Check\nRun with cwd ${project}.`);
    files.set(`${project}/.agent/playbooks/ideas.md`, `---\nstatus: draft\ncustom: keep\n---\n# Ideas\nIdeas from ${project}.`);
  }
  const tree = project => workspace().repositories.flatMap(repo => repo.worktrees).find(tree => tree.path === project)?.id ?? `root:${workspace().id}`;
  responses.project_skills = ({ project }) => paths.includes(project) ? [{ name: "review", file: ".agent/skills/review/SKILL.md", description: `Review ${project}`, origin: null }] : [];
  responses.project_tools = ({ project }) => paths.includes(project) ? [{ name: "check", file: ".agent/tools/check/TOOL.md", description: `Check ${project}`, from: [], platforms: [], files: ["macos.py"] }] : [];
  responses.project_mcps = ({ project }) => ({ claude_servers: paths.includes(project) ? { same: { command: "fixture", args: [project], env: { TOKEN: "never-in-catalog" } } } : {}, codex_servers: paths.includes(project) ? { same: { url: `http://localhost:${project === root ? 19000 : project.endsWith("api") ? 19001 : 19002}/mcp` } } : {}, claude_allow: [], claude_allow_local: [] });
  responses.project_playbooks = ({ project }) => [...files].filter(([path]) => path.startsWith(`${project}/.agent/playbooks/`)).map(([path, content]) => ({ file: path.slice(project.length + 1), title: content.match(/^# (.+)/m)?.[1] ?? "Ideas", description: null, status: content.match(/^status: (.+)/m)?.[1] ?? "active" }));
  const read = responses.project_read_file;
  responses.project_read_file = args => files.get(`${args.project}/${args.file}`) ?? read(args);
  const write = responses.project_write_file;
  responses.project_write_file = args => {
    const path = `${args.project}/${args.file}`;
    if (!files.has(path)) return write(args);
    if (args.expectedContent !== undefined && files.get(path) !== args.expectedContent) throw Error("Datei wurde inzwischen geändert.");
    files.set(path, args.content);
  };
  responses.project_playbook_create = ({ project, name, status }) => { const file = `.agent/playbooks/${name.toLowerCase().replaceAll(" ", "-")}.md`; files.set(`${project}/${file}`, `---\nstatus: ${status}\n---\n# ${name}\n`); return file; };
  responses.project_playbook_delete = ({ project, file }) => files.delete(`${project}/${file}`);
  responses.workspace_knowledge = () => {
    const flags = window.__SPECCIFY_MOCK__;
    const all = [{ id: `root:${workspace().id}`, path: root, relative_path: "Root" }, ...workspace().repositories.flatMap(repo => repo.worktrees)];
    const sources = all.map(value => ({ id: value.id, name: value.relative_path, path: value.path, available: flags.knowledgeOffline !== value.id, errors: flags.knowledgeOffline === value.id ? ["Quelle nicht verfügbar"] : [] }));
    const entries = [];
    for (const project of paths) {
      if (flags.knowledgeOffline === tree(project)) continue;
      for (const kind of ["skills", "tools", "playbooks", "mcps"]) {
        const values = kind === "mcps" ? ["claude", "codex"].map(host => ({ name: "same", file: host === "claude" ? ".mcp.json" : ".codex/config.toml", host })) : responses[`project_${kind}`]({ project });
        for (const entry of values) {
          const key = JSON.stringify([workspace().id, tree(project), kind, entry.file, entry.host ?? ""]);
          if (flags.knowledgeRemoved === key) continue;
          entries.push({ key, kind, name: entry.name ?? entry.title, title: entry.title ?? entry.name, file: entry.file, absolute_path: `${project}/${entry.file}`, worktree_id: tree(project), source: project === root ? "Root" : project.split("/").at(-1), root: project, status: entry.status ?? (kind === "mcps" ? "host-unconfirmed" : kind === "tools" ? "contract" : "readable"), host: entry.host ?? null });
        }
      }
    }
    return { entries, sources, warnings: [] };
  };
  flagsExpose();
  function flagsExpose() { window.__SPECCIFY_MOCK__.knowledgeFiles = files; }
}
