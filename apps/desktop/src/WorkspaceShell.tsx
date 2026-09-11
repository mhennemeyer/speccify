import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { createPortal } from "react-dom";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { PanelsContext, type Slots } from "./lib/panels";
import { ProjectActivity } from "./lib/projectActivity";
import { isDark, useTheme } from "./lib/theme";
import { isMac } from "./lib/platform";
import { ErrorBox } from "./components/ui";
import TerminalPanel from "./components/TerminalPanel";
import WorkspaceAgentContext from "./components/WorkspaceAgentContext";
import Toolbar, { ToolbarButton, PanelIcon, GearIcon, SunIcon, MoonIcon, GitIcon, TerminalIcon, PlayIcon, type ToolbarItem } from "./components/Toolbar";
import ProjectNavigation, { PROJECT_TABS, PROJECT_GROUPS, projectGroupOf, type ProjectTab } from "./components/ProjectNavigation";
import SplitHandle from "./components/SplitHandle";
import SettingsSheet from "./components/SettingsSheet";
import ActivityView from "./components/ActivityView";
import AgentStartup from "./components/AgentStartup";
import HelpView from "./views/HelpView";
import { DEFAULT_LAYOUT, DEFAULT_TOOLBAR_BUILTINS, TOOLBAR_BUILTINS, HANDLE_SIZE, LAYOUT_LIMITS, clamp, loadLayout, saveLayout, type ProjectLayout } from "./lib/layout";
import { AGENT_PRESETS } from "./lib/agents";
import { requestGit } from "./lib/git";
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
const tabs = PROJECT_TABS.map(({ id, label }) => [id, label] as const);
type Tab = ProjectTab;
interface ToolbarAction { name: string; command: string; confirmed: boolean; toolbar?: boolean; target: string; inputs?: unknown[] }
interface PaneToolbar { ready: boolean; actions: ToolbarAction[] }
const button = "rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-40";

/** One immutable target per pane. Hiding never remounts editors or processes. */
function WorktreePane({ workspaceId, tree, repo, group, tab, visited, active, choose, mainHost, inspectorHost, refresh, spec, changed, boardSlot, navHost, agentRoot, command, updateCommand, outputHost, outputTabsHost, layout, updateLayout, reportToolbar }: {
  workspaceId: string; tree: Tree; repo: Repository; group: Project; tab: Tab; visited: Tab[];
  active: boolean; choose: () => void; mainHost: HTMLElement | null; inspectorHost: HTMLElement | null;
  refresh: number; spec: WorkspaceSpecEntry | null; changed: () => void;
  boardSlot: (id: string, node: HTMLElement | null) => void;
  navHost: HTMLElement | null;
  agentRoot: string; command: string; updateCommand: (value: string) => void;
  outputHost: HTMLElement | null; outputTabsHost: HTMLElement | null; layout: ProjectLayout;
  updateLayout: (patch: Partial<ProjectLayout>) => void;
  reportToolbar: (id: string, value: PaneToolbar) => void;
}) {
  const [root, setRoot] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nav, setNav] = useState<Slots>({});
  const [inspector, setInspector] = useState<Slots>({});
  const [localRefresh, setLocalRefresh] = useState(0);
  const [outputSlot, setOutputSlot] = useState<HTMLDivElement | null>(null);
  const [outputs, setOutputs] = useState<ActionOutputTab[]>([]);
  const activeOutput = layout.rightTab.startsWith("output:") ? layout.rightTab.slice(7) : null;
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
  const revealOutput = useCallback((id: string) => { choose(); updateLayout({ rightShown: true, rightTab: `output:${id}` }); }, [choose, updateLayout]);
  const context = useMemo(() => ({ navigator: nav, inspector, reveal: () => updateLayout({ rightTab: "inspector" }) }), [nav, inspector, updateLayout]);
  const ownSpec = spec?.worktree_id === tree.id ? spec : null;
  const enabled = root !== null && error === null;
  useEffect(() => {
    let cancelled = false;
    reportToolbar(tree.id, { ready: enabled, actions: [] });
    if (root && enabled) void invoke<{ actions: ToolbarAction[] }>("project_actions", { project: root }).then(snapshot => {
      if (!cancelled) reportToolbar(tree.id, { ready: true, actions: snapshot.actions.filter(action => action.confirmed && action.target === "local" && !action.command.startsWith("toolui:")) });
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [root, enabled, totalRefresh, tree.id, reportToolbar]);
  return <ProjectActivity.Provider value={active && enabled}>
    <PanelsContext.Provider value={context}>
      <div onClickCapture={choose} onFocusCapture={choose}>
      {navHost && createPortal(<section aria-label={`Projektbereich ${group.name} / ${repo.name} / ${tree.relative_path}`} data-worktree-id={tree.id}
        onClickCapture={choose} onFocusCapture={choose} className="mb-2 min-w-0">
        <button aria-pressed={active} onClick={choose} data-tone="blue" className={`w-full rounded px-2 py-1 text-left text-xs ${active ? "tone-surface" : "text-slate-700 hover:bg-slate-100"}`}>
          <span className="block font-semibold">{repo.name}{repo.worktrees.length > 1 ? ` · ${tree.relative_path}` : ""}</span>
          <span className="mt-1 block break-all font-mono text-[10px]">{tree.relative_path || "."}</span>
          {!tree.available && <span className="block">Nicht verfügbar</span>}
          {outputs.some(output => output.running) && <span className="block">● Aktion läuft</span>}
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
          {id === "agent" && <AgentTab commandRoot={agentRoot} project={root} refresh={totalRefresh} agentCommand={command} onAgentCommand={updateCommand} />}
          {id === "actions" && <ActionsTab project={root} runNamespace={`workspace:${workspaceId}:${tree.id}`} refresh={totalRefresh} outputSlot={outputSlot} activeOutput={activeOutput} onOutputTabsChange={setOutputs} onRevealOutput={revealOutput} />}
        </div>)}
      </section>, mainHost)}
      {inspectorHost && createPortal(<section hidden={!active} aria-label={`Inspektor ${tree.path}`} inert={!enabled} className="h-full min-h-0">
        <p className="truncate border-b border-slate-200 px-4 py-2 text-[11px] text-slate-500" title={tree.path}>{group.name} / {repo.name} · {tree.relative_path}</p>
        {tabs.map(([id]) => <div key={id} ref={inspectorRefs[id]} data-workspace-inspector={id} className={tab === id ? "min-h-0" : "hidden"} />)}
        {(ownSpec || createRequest > 0) && root && enabled && <div className={tab === "board" ? "contents" : "hidden"}>
          <BoardTab project={root} detailFile={ownSpec?.spec.file} detailOnly refresh={totalRefresh} onMutated={changed} createRequest={createRequest} />
        </div>}
        {tab === "board" && !ownSpec && <p className="p-3 text-xs text-slate-500">Eine Spec im gemeinsamen Board auswählen.</p>}
      </section>, inspectorHost)}
      {outputTabsHost && createPortal(<div className={active ? "flex" : "hidden"}>
        {outputs.map(output => <div key={output.id} className="flex shrink-0 items-center">
          <button className="px-3 py-1.5 text-xs" aria-label={`Ausgabe: ${output.name}`} aria-pressed={activeOutput === output.id} onClick={() => revealOutput(output.id)}>{output.running ? "● " : output.failed ? "! " : "✓ "}{output.name}</button>
          <button aria-label={`Ausgabe schließen: ${output.name}`} disabled={output.running} className="mr-1 px-1 disabled:opacity-25" onClick={() => { output.close(); if (activeOutput === output.id) updateLayout({ rightTab: "inspector" }); }}>×</button>
        </div>)}
      </div>, outputTabsHost)}
      {outputHost && createPortal(<div ref={setOutputSlot} aria-label={`Aktionsausgabe ${tree.relative_path}`} className={active && activeOutput ? "flex h-full min-h-0 flex-col" : "hidden"} />, outputHost)}

      </div>
    </PanelsContext.Provider>
  </ProjectActivity.Provider>;
}

export default function WorkspaceShell() {
  const [theme, setTheme] = useTheme();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("board");
  const [lastTab, setLastTab] = useState<Record<string, Tab>>({});
  const [visited, setVisited] = useState<Tab[]>(["files", "git", "actions"]);
  const [selected, setSelected] = useState("");
  const selectionRef = useRef("");
  const [mainHost, setMainHost] = useState<HTMLDivElement | null>(null);
  const [inspectorHost, setInspectorHost] = useState<HTMLElement | null>(null);
  const [outputHost, setOutputHost] = useState<HTMLDivElement | null>(null);
  const [outputTabsHost, setOutputTabsHost] = useState<HTMLDivElement | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [boardRefresh, setBoardRefresh] = useState(0);
  const [spec, setSpec] = useState<WorkspaceSpecEntry | null>(null);
  const [boardSlots, setBoardSlots] = useState<Record<string, HTMLElement | null>>({});
  const [groupSlots, setGroupSlots] = useState<Record<string, HTMLElement | null>>({});
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [layout, setLayout] = useState<ProjectLayout>({ ...DEFAULT_LAYOUT, resumeAgent: false });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [started, setStarted] = useState(false);
  const [command, setCommand] = useState("");
  useEffect(() => {
    if (workspace) { try { setCommand(localStorage.getItem(`speccify.workspace.agentCommand:${workspace.id}`) ?? ""); } catch { /* Session-only fallback. */ } }
  }, [workspace?.id]);
  const updateCommand = (value: string) => {
    setCommand(value);
    if (workspace) { try { localStorage.setItem(`speccify.workspace.agentCommand:${workspace.id}`, value); } catch { /* Session-only fallback. */ } }
  };
  const [paneToolbars, setPaneToolbars] = useState<Record<string, PaneToolbar>>({});
  const reportToolbar = useCallback((id: string, value: PaneToolbar) => setPaneToolbars(old => ({ ...old, [id]: value })), []);
  const layoutKey = workspace ? `workspace:${workspace.id}` : null;
  useEffect(() => { if (layoutKey) setLayout({ ...loadLayout(layoutKey), resumeAgent: false }); }, [layoutKey]);
  const updateLayout = useCallback((patch: Partial<ProjectLayout> | ((old: ProjectLayout) => Partial<ProjectLayout>)) => {
    setLayout(old => {
      const next = { ...old, ...(typeof patch === "function" ? patch(old) : patch) };
      if (layoutKey) saveLayout(layoutKey, next);
      return next;
    });
  }, [layoutKey]);
  const choose = useCallback((id: string) => {
    if (selectionRef.current === id) return;
    selectionRef.current = id;
    setSelected(id);
    updateLayout(previous => previous.rightTab.startsWith("output:") ? { rightTab: "inspector" } : {});
  }, [updateLayout]);
  const groupRefs = useMemo(() => Object.fromEntries((workspace?.projects ?? []).map(group => [group.id, (node: HTMLDivElement | null) => setGroupSlots(old => old[group.id] === node ? old : { ...old, [group.id]: node })])), [workspace?.projects]);
  const boardSlot = useCallback((id: string, node: HTMLElement | null) => setBoardSlots(old => old[id] === node ? old : { ...old, [id]: node }), []);
  const changed = useCallback(() => setBoardRefresh(value => value + 1), []);
  const activate = useCallback((value: Tab) => {
    setTab(value);
    setLastTab(old => ({ ...old, [projectGroupOf(value).id]: value }));
    setVisited(old => old.includes(value) ? old : [...old, value]);
  }, []);
  const selectSpec = useCallback((value: WorkspaceSpecEntry | null, focus = false) => {
    setSpec(value);
    if (value && focus) { choose(value.worktree_id); updateLayout({ rightShown: true, rightTab: "inspector" }); }
  }, [choose, updateLayout]);
  const showTerminal = useCallback(() => updateLayout(old => old.terminalDock === "bottom"
    ? { bottomShown: true } : { rightShown: true, rightTab: "terminal" }), [updateLayout]);
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
    window.addEventListener("speccify:show-tab", handler);
    window.addEventListener("speccify:open-file", files);
    window.addEventListener("speccify:type-command", showTerminal);
    return () => {
      window.removeEventListener("speccify:show-tab", handler);
      window.removeEventListener("speccify:open-file", files);
      window.removeEventListener("speccify:type-command", showTerminal);
    };
  }, [activate, showTerminal]);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (!(isMac ? event.metaKey : event.ctrlKey)) return;
      const target = event.target as HTMLElement | null;
      const typing = target && (["INPUT", "TEXTAREA"].includes(target.tagName) || target.isContentEditable);
      if (event.key === "0") {
        event.preventDefault();
        updateLayout(old => event.altKey ? { rightShown: !old.rightShown } : { navShown: !old.navShown });
      } else if (event.shiftKey && event.key.toLowerCase() === "y") {
        event.preventDefault();
        updateLayout(old => old.terminalDock === "bottom" ? { bottomShown: !old.bottomShown }
          : { terminalDock: "bottom", bottomShown: true, rightTab: "inspector" });
      } else if (!typing && !event.altKey && !event.shiftKey && /^[1-5]$/.test(event.key)) {
        event.preventDefault();
        const group = PROJECT_GROUPS[Number(event.key) - 1];
        activate(lastTab[group.id] ?? group.tabs[0]);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [activate, lastTab, updateLayout]);
  const target = workspace?.repositories.flatMap(repo => repo.worktrees).find(tree => tree.id === selected);
  const activeToolbar = paneToolbars[selected];
  const toolbarActions = activeToolbar?.actions ?? [];
  const defaults = [...DEFAULT_TOOLBAR_BUILTINS, ...toolbarActions.filter(action => action.toolbar).map(action => `action:${action.command}`)];
  const toolbarIds = layout.toolbar ?? defaults;
  const builtins: ToolbarItem[] = TOOLBAR_BUILTINS.map(item => ({
    ...item, disabled: item.id === "terminal" ? !workspace : !activeToolbar?.ready, icon: item.id === "terminal" ? <TerminalIcon /> : <GitIcon />,
    onClick: () => {
      if (item.id === "terminal") { showTerminal(); setStarted(true); }
      else { activate("git"); requestGit(item.id === "git-commit" ? "commit" : item.id === "git-pull" ? "pull" : "push"); }
    },
  }));
  const actionItems: ToolbarItem[] = toolbarActions.map(action => ({
    id: `action:${action.command}`, title: `${action.name} — ${target?.path}\n${action.command}`,
    label: action.name, icon: <PlayIcon />, disabled: !activeToolbar?.ready,
    onClick: () => {
      if (action.inputs?.length) activate("actions");
      else window.dispatchEvent(new CustomEvent("speccify:run-action", { detail: action.command }));
    },
  }));
  const toolbarItems = toolbarIds.map(id => [...builtins, ...actionItems].find(item => item.id === id)).filter((item): item is ToolbarItem => !!item);
  const toolbarChoices = [...TOOLBAR_BUILTINS.map(item => ({ id: item.id, label: item.label, hint: item.title })),
    ...toolbarActions.map(action => ({ id: `action:${action.command}`, label: action.name, hint: action.command }))];
  const { navShown, rightShown, terminalDock } = layout;
  const bottomVisible = terminalDock === "bottom" && layout.bottomShown;
  const terminalVisible = terminalDock === "right" ? rightShown && layout.rightTab === "terminal" : bottomVisible;
  const outputVisible = rightShown && layout.rightTab.startsWith("output:");
  const gridStyle: CSSProperties = {
    display: "grid",
    gridTemplateColumns: `${navShown ? layout.navWidth : 0}px ${navShown ? HANDLE_SIZE : 0}px minmax(0,1fr) ${rightShown ? HANDLE_SIZE : 0}px ${rightShown ? layout.rightWidth : 0}px`,
    gridTemplateRows: `auto auto minmax(0,1fr) ${bottomVisible ? HANDLE_SIZE : 0}px ${bottomVisible ? layout.bottomHeight : 0}px`,
  };
  const toggleDock = () => updateLayout(old => old.terminalDock === "right"
    ? { terminalDock: "bottom", bottomShown: true, rightTab: "inspector" }
    : { terminalDock: "right", rightShown: true, rightTab: "terminal" });
  return <>
    <div className="h-screen min-w-0 bg-slate-50 text-slate-900" style={gridStyle}>
      <div style={{ gridColumn: "1 / -1", gridRow: 1 }}>
        <Toolbar title={workspace?.name ?? "Workspace laden…"} subtitle={workspace?.root} items={toolbarItems} center={<ActivityView />}
          trailing={<>
            <ToolbarButton active={navShown} title={`${navShown ? "Navigator ausblenden" : "Navigator einblenden"} (${isMac ? "⌘" : "Strg+"}0)`} onClick={() => updateLayout({ navShown: !navShown })}><PanelIcon part="nav" /></ToolbarButton>
            <ToolbarButton active={bottomVisible} title={terminalDock === "bottom" ? bottomVisible ? "Terminal unten ausblenden" : "Terminal unten einblenden" : "Terminal nach unten legen"} onClick={() => terminalDock === "bottom" ? updateLayout({ bottomShown: !layout.bottomShown }) : toggleDock()}><PanelIcon part="bottom" /></ToolbarButton>
            <ToolbarButton active={rightShown} title={`${rightShown ? "Inspektor ausblenden" : "Inspektor einblenden"} (${isMac ? "⌥⌘" : "Strg+Alt+"}0)`} onClick={() => updateLayout({ rightShown: !rightShown })}><PanelIcon part="right" /></ToolbarButton>
            <span className="mx-1 h-4 w-px bg-slate-200" aria-hidden="true" />
            <ToolbarButton title={isDark(theme) ? "Hell schalten" : "Dunkel schalten"} onClick={() => void setTheme(isDark(theme) ? "light" : "dark")}>{isDark(theme) ? <SunIcon /> : <MoonIcon />}</ToolbarButton>
            <ToolbarButton title="Einstellungen" active={settingsOpen} onClick={() => setSettingsOpen(true)}><GearIcon /></ToolbarButton>
          </>} />
      </div>
      <nav aria-label="Workspace-Projekte" className={`${navShown ? "flex" : "hidden"} min-h-0 flex-col border-r border-slate-200 bg-white`} style={{ gridColumn: 1, gridRow: "2 / -1" }}>
        <ProjectNavigation active={tab} lastTab={lastTab} activate={activate} />
        <div className="flex items-center justify-between border-b border-slate-200 px-3 py-1 text-[11px] text-slate-500">
          <span>Projekte · {workspace?.repositories.length ?? 0}</span>
          <button title="Workspace-Zuordnung aktualisieren" onClick={() => { setRefresh(value => value + 1); changed(); }} className="rounded px-1 hover:bg-slate-100">Aktualisieren</button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
          {workspace?.projects.filter(group => group.repository_ids.length).map(group => <section key={group.id} aria-label={`Projektgruppe ${group.name}`} className="mt-2">
            <button aria-expanded={!collapsed[group.id]} onClick={() => setCollapsed(old => ({ ...old, [group.id]: !old[group.id] }))}
              className="flex w-full items-center gap-1 rounded px-1 py-1 text-left text-xs font-semibold text-slate-500 hover:bg-slate-100">
              <span aria-hidden="true">{collapsed[group.id] ? "▸" : "▾"}</span>{group.name}
            </button>
            <div ref={groupRefs[group.id]} className={collapsed[group.id] ? "hidden" : ""} />
          </section>)}
        </div>
      </nav>
      {navShown && <SplitHandle axis="x" size={layout.navWidth} onResize={next => updateLayout({ navWidth: clamp(next, LAYOUT_LIMITS.nav) })} onReset={() => updateLayout({ navWidth: DEFAULT_LAYOUT.navWidth })} style={{ gridColumn: 2, gridRow: "2 / -1" }} />}
      <main className="flex min-h-0 min-w-0 flex-col overflow-hidden p-5" style={{ gridColumn: 3, gridRow: "2 / 4" }}>
        {error && <ErrorBox message={error} />}
        <p aria-label="Aktives Projektziel" className="mb-3 truncate text-[11px] text-slate-500" title={target?.path}>
          {tab === "board" ? "Gemeinsames Board" : "Aktives Ziel"} · {target?.path ?? "Kein verfügbares Projekt"}
        </p>
        <div className={tab === "board" ? "min-h-0 flex-1 overflow-auto" : "hidden"}>
          {workspace && <WorkspaceBoardView workspaceId={workspace.id} revision={workspace.revision} refresh={boardRefresh} onSelect={selectSpec} listSlots={boardSlots} />}
        </div>
        <div className={tab === "help" ? "min-h-0 flex-1" : "hidden"}>{visited.includes("help") && <HelpView />}</div>
        <div ref={setMainHost} className={tab === "board" || tab === "help" ? "hidden" : "min-h-0 flex-1 overflow-auto"} />
      </main>
      {bottomVisible && <SplitHandle axis="y" size={layout.bottomHeight} invert onResize={next => updateLayout({ bottomHeight: clamp(next, LAYOUT_LIMITS.bottom) })} onReset={() => updateLayout({ bottomHeight: DEFAULT_LAYOUT.bottomHeight })} style={{ gridColumn: 3, gridRow: 4 }} />}
      {rightShown && <SplitHandle axis="x" size={layout.rightWidth} invert onResize={next => updateLayout({ rightWidth: clamp(next, LAYOUT_LIMITS.right) })} onReset={() => updateLayout({ rightWidth: DEFAULT_LAYOUT.rightWidth })} style={{ gridColumn: 4, gridRow: "2 / -1" }} />}
      <div aria-label="Rechte Seitenleiste" className={`${rightShown ? "flex" : "hidden"} min-w-0 items-stretch overflow-x-auto border-b border-l border-slate-200 bg-white text-xs`} style={{ gridColumn: 5, gridRow: 2 }}>
        {(terminalDock === "right" ? [["inspector", "Inspektor"], ["terminal", "Terminal"]] as const : [["inspector", "Inspektor"]] as const).map(([id, label]) => <button key={id} aria-pressed={layout.rightTab === id} onClick={() => updateLayout({ rightTab: id })} className={`shrink-0 px-3 py-1.5 font-medium ${layout.rightTab === id ? "border-b-2 border-slate-800 text-slate-800" : "text-slate-400 hover:text-slate-700"}`}>{label}</button>)}
        <div ref={setOutputTabsHost} className="flex" />
      </div>
      <div ref={setOutputHost} aria-label="Aktionsausgabe" className={`${outputVisible ? "flex" : "hidden"} min-h-0 min-w-0 flex-col overflow-hidden`} style={{ gridColumn: 5, gridRow: "3 / -1" }} />
      <aside ref={setInspectorHost} aria-label="Workspace-Inspektor" className={`inspector-body ${rightShown && layout.rightTab === "inspector" ? "flex" : "hidden"} min-h-0 min-w-0 flex-col overflow-y-auto border-l border-slate-200 bg-white`} style={{ gridColumn: 5, gridRow: "3 / -1" }} />
      <section aria-label="Agent-Terminal" className={`keep-dark ${terminalVisible ? "flex" : "hidden"} min-h-0 min-w-0 flex-col bg-slate-900 ${terminalDock === "right" ? "border-l" : "border-t"} border-slate-700`} style={terminalDock === "right" ? { gridColumn: 5, gridRow: "3 / -1" } : { gridColumn: 3, gridRow: 5 }}>
        <div className="flex justify-end px-2 pt-1"><button onClick={toggleDock} title={terminalDock === "right" ? "Terminal nach unten legen" : "Terminal nach rechts legen"} className="rounded px-2 py-0.5 text-xs text-slate-500 hover:bg-slate-800 hover:text-slate-300">{terminalDock === "right" ? "⬓ nach unten" : "⬔ nach rechts"}</button></div>
        {workspace && <section aria-label={`Terminal ${workspace.root}`} className="flex min-h-0 flex-1 flex-col">
          <div className="flex items-center justify-between gap-2 px-3 py-1">
            <p className="truncate font-mono text-[10px] text-slate-400" title={workspace.root}>Workspace-Terminal · {workspace.root}</p>
            {!started && <button className="shrink-0 rounded bg-slate-700 px-3 py-1 text-xs text-slate-200" onClick={() => setStarted(true)}>Agent-Terminal starten</button>}
          </div>
          <p className="px-3 text-[10px] text-slate-400">Eine gemeinsame Sitzung für alle Repos · Projektwechsel ändert das Terminal-Ziel nicht.</p>
          <WorkspaceAgentContext revision={workspace.revision + refresh} />
          {started ? <TerminalPanel workspaceId={workspace.id} cwd={workspace.root} visible={terminalVisible} autostart={command} /> : <div className="flex min-h-0 flex-1 flex-col items-center gap-3 overflow-auto p-4">
            <label className="w-full max-w-md text-xs text-slate-400">Agent-Kommando (leer = nur Shell)
              <input aria-label="Workspace-Terminal-Kommando" value={command} onChange={event => updateCommand(event.target.value)} className="mt-1 block w-full rounded border border-slate-600 bg-slate-800 px-3 py-2 font-mono text-sm text-slate-100" />
            </label>
            <div className="flex flex-wrap gap-1.5">{AGENT_PRESETS.map(preset => <button key={preset.id} onClick={() => updateCommand(preset.command)} className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400 hover:text-slate-200">{preset.label}</button>)}</div>
            <p className="max-w-md text-xs text-slate-400">Die Presets Codex und Claude erhalten die Workspace-Struktur automatisch. Bei eigenen Kommandos: Kontextdatei aus SPECCIFY_WORKSPACE_CONTEXT an den Host übergeben. Repo-Anweisungen bleiben getrennt; Berechtigungen des Hosts gelten weiterhin.</p>
            {terminalVisible && <div className="w-full max-w-md text-slate-400"><AgentStartup project={workspace.root} command={command} /></div>}
          </div>}
        </section>}
      </section>
    </div>
    {workspace?.repositories.flatMap(repo => repo.worktrees.map(tree => {
      const group = workspace.projects.find(group => group.repository_ids.includes(repo.id));
      return group && <WorktreePane key={`${tree.id}:${tree.path}`} workspaceId={workspace.id} tree={tree} repo={repo} group={group} tab={tab} visited={visited}
        active={selected === tree.id} choose={() => choose(tree.id)} mainHost={mainHost} inspectorHost={inspectorHost} refresh={refresh} spec={spec} changed={changed} boardSlot={boardSlot} navHost={groupSlots[group.id] ?? null}
        agentRoot={workspace.root} command={command} updateCommand={updateCommand} outputHost={outputHost} outputTabsHost={outputTabsHost} layout={layout} updateLayout={updateLayout} reportToolbar={reportToolbar} />;
    }))}
    {settingsOpen && <SettingsSheet theme={theme} onTheme={next => void setTheme(next)} layout={layout}
      onDock={dock => updateLayout(dock === "bottom" ? { terminalDock: dock, bottomShown: true, rightTab: "inspector" } : { terminalDock: dock, rightShown: true, rightTab: "terminal" })}
      toolbar={toolbarIds} toolbarChoices={toolbarChoices} onToolbar={ids => updateLayout({ toolbar: ids })}
      onResetLayout={() => updateLayout({ ...DEFAULT_LAYOUT, resumeAgent: false, toolbar: undefined })} onClose={() => setSettingsOpen(false)} />}
  </>;
}
