import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { PanelsContext, type Slots } from "./lib/panels";
import { ProjectActivity } from "./lib/projectActivity";
import { useTheme } from "./lib/theme";
import { isMac } from "./lib/platform";
import { ErrorBox } from "./components/ui";
import TerminalPanel from "./components/TerminalPanel";
import FilesTab from "./views/project/FilesTab";
import GitTab from "./views/project/GitTab";
import PlaybooksTab from "./views/project/PlaybooksTab";
import SkillsTab from "./views/project/SkillsTab";
import ToolsTab from "./views/project/ToolsTab";
import ActionsTab, { type ActionOutputTab } from "./views/project/ActionsTab";
import McpsTab from "./views/project/McpsTab";
import AgentTab from "./views/project/AgentTab";
import BoardTab from "./views/project/BoardTab";
import WorkspaceBoardView, { type WorkspaceSpecEntry } from "./views/WorkspaceBoardView";

interface Tree { id: string; path: string; relative_path: string; available: boolean }
interface Repository { id: string; name: string; worktrees: Tree[] }
interface Project { id: string; name: string; repository_ids: string[] }
interface Workspace { id: string; name: string; root: string; revision: number; projects: Project[]; repositories: Repository[]; partial: boolean; warnings: string[] }
const tabs = [
  ["board", "Gemeinsames Board"], ["files", "Dateien"], ["git", "Git"],
  ["playbooks", "Playbooks"], ["skills", "Skills"], ["tools", "Tools"],
  ["actions", "Aktionen"], ["mcps", "MCPs"], ["agent", "Agent"], ["terminal", "Terminals"],
] as const;
type Tab = typeof tabs[number][0];
const button = "rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-40";

/** One immutable target per pane. Hiding never remounts editors or processes. */
function WorktreePane({ workspaceId, tree, repo, group, tab, visited, active, choose, mainHost, inspectorHost, refresh, spec, changed, showTab, boardSlot, navHost }: {
  workspaceId: string; tree: Tree; repo: Repository; group: Project; tab: Tab; visited: Tab[];
  active: boolean; choose: () => void; mainHost: HTMLElement | null; inspectorHost: HTMLElement | null;
  refresh: number; spec: WorkspaceSpecEntry | null; changed: () => void; showTab: (tab: Tab) => void;
  boardSlot: (id: string, node: HTMLElement | null) => void;
  navHost: HTMLElement | null;
}) {
  const [root, setRoot] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nav, setNav] = useState<Slots>({});
  const [inspector, setInspector] = useState<Slots>({});
  const [localRefresh, setLocalRefresh] = useState(0);
  const [started, setStarted] = useState(false);
  const [command, setCommand] = useState(() => {
    try { return localStorage.getItem(`speccify.project.agentCommand:${tree.path}`) ?? ""; } catch { return ""; }
  });
  const [outputSlot, setOutputSlot] = useState<HTMLDivElement | null>(null);
  const [outputs, setOutputs] = useState<ActionOutputTab[]>([]);
  const [activeOutput, setActiveOutput] = useState<string | null>(null);
  const [createRequest, setCreateRequest] = useState(0);
  const navRefs = useMemo(() => Object.fromEntries(tabs.map(([id]) => [id, (node: HTMLDivElement | null) => {
    setNav(old => old[id] === node ? old : { ...old, [id]: node });
    if (id === "board") boardSlot(tree.id, node);
  }])), [boardSlot, tree.id]);
  const inspectorRefs = useMemo(() => Object.fromEntries(tabs.map(([id]) => [id, (node: HTMLDivElement | null) => setInspector(old => old[id] === node ? old : { ...old, [id]: node })])), []);
  const totalRefresh = refresh + localRefresh;
  useEffect(() => {
    let cancelled = false;
    void invoke<string>("workspace_resolve_target", { workspaceId, worktreeId: tree.id }).then(path => {
      if (cancelled) return;
      if (path !== tree.path) { setError("Pfadbindung verändert. Workspace neu öffnen; laufende Prozesse behalten ihr bisheriges Ziel."); return; }
      setRoot(path); setError(null);
    }).catch(e => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, [workspaceId, tree.id, tree.path, refresh]);
  useEffect(() => {
    if (!root) return;
    let disposed = false;
    const watcherId = crypto.randomUUID();
    const watching = invoke("project_watch_start", { project: root, watcherId }).then(() => {
      if (disposed) return invoke("project_watch_stop", { project: root, watcherId });
    }).catch(e => { if (!disposed) setError(String(e)); });
    const listener = listen<{ project?: string; areas: string[] }>("project-changed", event => {
      if (event.payload.project !== root) return;
      setLocalRefresh(value => value + 1);
      if (event.payload.areas.includes("board")) changed();
    });
    return () => { disposed = true; void watching.then(() => invoke("project_watch_stop", { project: root, watcherId })); void listener.then(stop => stop()); };
  }, [root, changed]);
  const updateCommand = (value: string) => {
    setCommand(value);
    try { localStorage.setItem(`speccify.project.agentCommand:${tree.path}`, value); } catch { /* Local editing remains available. */ }
  };
  const revealOutput = useCallback((id: string) => { setActiveOutput(id); }, []);
  const context = useMemo(() => ({ navigator: nav, inspector, reveal: () => setActiveOutput(null) }), [nav, inspector]);
  const ownSpec = spec?.worktree_id === tree.id ? spec : null;
  const enabled = root !== null && error === null;
  return <ProjectActivity.Provider value={active && enabled}>
    <PanelsContext.Provider value={context}>
      <div onClickCapture={choose} onFocusCapture={choose}>
      {navHost && createPortal(<section aria-label={`Projektbereich ${group.name} / ${repo.name} / ${tree.relative_path}`} data-worktree-id={tree.id}
        onClickCapture={choose} onFocusCapture={choose} className="mb-2 min-w-0 rounded border border-slate-200 bg-white">
        <button aria-pressed={active} onClick={choose} data-tone="blue" className={`w-full rounded px-3 py-2 text-left text-xs ${active ? "tone-surface" : "text-slate-700"}`}>
          <span className="block font-semibold">{repo.name}{repo.worktrees.length > 1 ? ` · ${tree.relative_path}` : ""}</span>
          <span className="mt-1 block break-all font-mono text-[10px]">{tree.relative_path || "."}</span>
          {!tree.available && <span className="block">Nicht verfügbar</span>}
          {outputs.some(output => output.running) && <span className="block">● Aktion läuft</span>}
          {started && <span className="block">● Terminal gestartet</span>}
        </button>
        {error && <ErrorBox message={error} />}
        {!root && !error && <p className="p-2 text-xs text-slate-500">Ziel prüfen…</p>}
        <div inert={!enabled} className={!enabled ? "opacity-50" : ""}>
          {tabs.map(([id]) => <div key={id} ref={navRefs[id]} data-workspace-nav={id} className={tab === id ? "p-2" : "hidden"} />)}
          {tab === "board" && <button className={`${button} m-2`} disabled={!enabled} onClick={() => setCreateRequest(value => value + 1)}>+ Spec in {repo.name}</button>}
        </div>
      </section>, navHost)}
      {mainHost && root && createPortal(<section aria-label={`Arbeitsbereich ${tree.path}`} hidden={!active || tab === "board"} className="h-full min-h-0" inert={!enabled}>
        {error && <ErrorBox message={error} />}
        {visited.filter(id => id !== "board").map(id => <div key={id} className={tab === id ? "h-full min-h-0" : "hidden"}>
          {id === "files" && <FilesTab project={root} refresh={totalRefresh} visible={active && tab === id} />}
          {id === "git" && <GitTab project={root} refresh={totalRefresh} visible={active && tab === id} />}
          {id === "playbooks" && <PlaybooksTab project={root} refresh={totalRefresh} />}
          {id === "skills" && <SkillsTab project={root} refresh={totalRefresh} />}
          {id === "tools" && <ToolsTab project={root} refresh={totalRefresh} />}
          {id === "mcps" && <McpsTab project={root} refresh={totalRefresh} />}
          {id === "agent" && <AgentTab project={root} refresh={totalRefresh} agentCommand={command} onAgentCommand={updateCommand} />}
          {id === "actions" && <ActionsTab project={root} refresh={totalRefresh} outputSlot={outputSlot} activeOutput={activeOutput} onOutputTabsChange={setOutputs} onRevealOutput={revealOutput} />}
          {id === "terminal" && <div className="keep-dark flex h-full min-h-0 flex-col bg-slate-900">
            <p className="break-all p-3 font-mono text-xs text-slate-300">Terminal-Ziel: {root}</p>
            {started ? <TerminalPanel cwd={root} visible={active && tab === "terminal"} autostart={command} /> : <div className="space-y-3 p-4">
              <label className="block text-sm text-slate-300">Kommando (leer = Shell)<input aria-label={`Terminal-Kommando ${tree.relative_path}`} value={command} onChange={event => updateCommand(event.target.value)} className="mt-2 block w-full rounded border border-slate-600 bg-slate-800 p-2" /></label>
              <button className="rounded bg-slate-700 px-3 py-2 text-sm text-white" onClick={() => setStarted(true)}>Terminal starten: {repo.name}</button>
            </div>}
          </div>}
        </div>)}
      </section>, mainHost)}
      {inspectorHost && createPortal(<section hidden={!active} aria-label={`Inspektor ${tree.path}`} inert={!enabled} className="h-full min-h-0">
        <p data-tone="violet" className="tone-surface break-all border-b p-3 text-xs">{group.name} / {repo.name}<br /><span className="font-mono">{tree.path}</span></p>
        <div className="flex flex-wrap gap-1 border-b border-slate-200 p-2">
          <button className={button} onClick={() => setActiveOutput(null)}>Inspektor</button>
          {outputs.map(output => <button key={output.id} className={button} aria-pressed={output.id === activeOutput} onClick={() => setActiveOutput(output.id)}>{output.running ? "● " : output.failed ? "! " : "✓ "}{output.name}</button>)}
          <button className={button} onClick={() => showTab("terminal")}>Terminal</button>
        </div>
        <div ref={setOutputSlot} aria-label={`Aktionsausgabe ${tree.relative_path}`} className={activeOutput ? "h-[calc(100%-7rem)] min-h-64" : "hidden"} />
        {tabs.map(([id]) => <div key={id} ref={inspectorRefs[id]} data-workspace-inspector={id} className={!activeOutput && tab === id ? "min-h-0" : "hidden"} />)}
        {(ownSpec || createRequest > 0) && root && enabled && <div className={tab === "board" ? "contents" : "hidden"}>
          <BoardTab project={root} detailFile={ownSpec?.spec.file} detailOnly refresh={totalRefresh} onMutated={changed} createRequest={createRequest} />
        </div>}
        {tab === "board" && !ownSpec && <p className="p-3 text-xs text-slate-500">Eine Spec im gemeinsamen Board auswählen.</p>}
      </section>, inspectorHost)}
      </div>
    </PanelsContext.Provider>
  </ProjectActivity.Provider>;
}

export default function WorkspaceShell() {
  useTheme();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("board");
  const [visited, setVisited] = useState<Tab[]>(["files"]);
  const [selected, setSelected] = useState("");
  const [mainHost, setMainHost] = useState<HTMLDivElement | null>(null);
  const [inspectorHost, setInspectorHost] = useState<HTMLElement | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [boardRefresh, setBoardRefresh] = useState(0);
  const [spec, setSpec] = useState<WorkspaceSpecEntry | null>(null);
  const [boardSlots, setBoardSlots] = useState<Record<string, HTMLElement | null>>({});
  const [groupSlots, setGroupSlots] = useState<Record<string, HTMLElement | null>>({});
  const groupRefs = useMemo(() => Object.fromEntries((workspace?.projects ?? []).map(group => [group.id, (node: HTMLDivElement | null) => setGroupSlots(old => old[group.id] === node ? old : { ...old, [group.id]: node })])), [workspace?.projects]);
  const boardSlot = useCallback((id: string, node: HTMLElement | null) => setBoardSlots(old => old[id] === node ? old : { ...old, [id]: node }), []);
  const changed = useCallback(() => setBoardRefresh(value => value + 1), []);
  const activate = useCallback((value: Tab) => { setTab(value); setVisited(old => old.includes(value) ? old : [...old, value]); }, []);
  const selectSpec = useCallback((value: WorkspaceSpecEntry | null, focus = false) => { setSpec(value); if (value && focus) setSelected(value.worktree_id); }, []);
  useEffect(() => {
    let cancelled = false;
    void invoke<Workspace>("workspace_window_current").then(value => {
      if (cancelled) return;
      setWorkspace(value); setError(null);
      setSelected(old => old || value.repositories.flatMap(repo => repo.worktrees).find(tree => tree.available)?.id || "");
    }).catch(e => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, [refresh]);
  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail;
      if (tabs.some(([id]) => id === detail)) activate(detail as Tab);
    };
    const files = () => activate("files");
    const terminal = () => activate("terminal");
    window.addEventListener("speccify:show-tab", handler);
    window.addEventListener("speccify:open-file", files);
    window.addEventListener("speccify:type-command", terminal);
    return () => { window.removeEventListener("speccify:show-tab", handler); window.removeEventListener("speccify:open-file", files); window.removeEventListener("speccify:type-command", terminal); };
  }, [activate]);
  const target = workspace?.repositories.flatMap(repo => repo.worktrees).find(tree => tree.id === selected);
  return <div className="flex h-screen min-w-0 flex-col bg-slate-50 text-slate-900">
    <header data-tauri-drag-region className="flex min-h-14 flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-2" style={{ paddingLeft: isMac ? 88 : 16 }}>
      <h1 className="font-semibold">{workspace?.name ?? "Workspace laden…"} <span className="text-xs font-normal text-slate-500">Workspace</span></h1>
      <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-500" title={workspace?.root}>{workspace?.root}</span>
      <button className={button} onClick={() => { setRefresh(value => value + 1); changed(); }}>Aktualisieren</button>
    </header>
    <nav aria-label="Workspace-Bereiche" className="flex shrink-0 flex-wrap gap-1 border-b border-slate-200 bg-white p-2">
      {tabs.map(([id, label]) => <button key={id} data-tone={id === "git" || id === "files" ? "blue" : "violet"} aria-pressed={tab === id} onClick={() => activate(id)} className={`${button} ${tab === id ? "tone-surface" : ""}`}>{label}</button>)}
    </nav>
    {error && <ErrorBox message={error} />}
    <div className="grid min-h-0 flex-1 grid-cols-[minmax(14rem,19rem)_minmax(0,1fr)_minmax(17rem,23rem)]">
      <aside aria-label="Workspace-Projekte" className="min-w-0 overflow-auto border-r border-slate-200 p-2">
        {workspace?.projects.filter(group => group.repository_ids.length).map(group => <section key={group.id} aria-label={`Projektgruppe ${group.name}`} className="mb-4">
          <h2 data-tone="violet" className="tone-ink mb-2 px-2 text-sm font-semibold">{group.name}</h2>
          <div ref={groupRefs[group.id]} />
        </section>)}
      </aside>
      <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
        <p aria-label="Aktives Projektziel" className="break-all border-b border-slate-200 px-4 py-2 font-mono text-xs text-slate-500">{tab === "board" ? "Gemeinsames Board" : "Aktives Ziel"} · {target?.path ?? "Kein verfügbares Projekt"}</p>
        <div className={tab === "board" ? "min-h-0 flex-1 overflow-auto p-4" : "hidden"}>
          {workspace && <WorkspaceBoardView workspaceId={workspace.id} revision={workspace.revision} refresh={boardRefresh} onSelect={selectSpec} listSlots={boardSlots} />}
        </div>
        <div ref={setMainHost} className={tab === "board" ? "hidden" : "min-h-0 flex-1 overflow-auto p-4"} />
      </main>
      <aside ref={setInspectorHost} aria-label="Workspace-Inspektor" className="inspector-body min-w-0 overflow-auto border-l border-slate-200 bg-white" />
    </div>
    {workspace?.repositories.flatMap(repo => repo.worktrees.map(tree => {
      const group = workspace.projects.find(group => group.repository_ids.includes(repo.id));
      return group && <WorktreePane key={`${tree.id}:${tree.path}`} workspaceId={workspace.id} tree={tree} repo={repo} group={group} tab={tab} visited={visited}
        active={selected === tree.id} choose={() => setSelected(tree.id)} mainHost={mainHost} inspectorHost={inspectorHost} refresh={refresh} spec={spec} changed={changed} showTab={activate} boardSlot={boardSlot} navHost={groupSlots[group.id] ?? null} />;
    }))}
  </div>;
}
