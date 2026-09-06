// Projektfenster (Plan projektfenster.md, P1 → W7-Layout): das Xcode-/
// iKanban-Muster — Navigator links (Tabs), Inhalt in der Mitte, rechts der
// Inspektor mit eigenen Tabs; das Agent-Terminal lebt wahlweise als Tab in
// der rechten Seitenleiste oder als höhenverstellbare Bottom-Bar. Alles
// ist ein CSS-Grid: das Terminal bleibt dasselbe React-Element und wechselt
// nur seine Grid-Zelle — sonst würde der PTY beim Umdocken sterben.
// Die Wurzel kommt über `project_current` (Fenster-Label → Registry, D15).

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import SettingsSheet from "./components/SettingsSheet";
import SplitHandle from "./components/SplitHandle";
import TerminalPanel from "./components/TerminalPanel";
import ActivityView from "./components/ActivityView";
import Toolbar, {
  GearIcon,
  MoonIcon,
  PanelIcon,
  PlayIcon,
  SunIcon,
  ToolbarButton,
  type ToolbarItem,
} from "./components/Toolbar";
import { isDark, useTheme } from "./lib/theme";
import { recordActivity } from "./lib/activity";
import { isMac } from "./lib/platform";
import HelpView from "./views/HelpView";
import { ErrorBox, Spinner } from "./components/ui";
import { AGENT_PRESETS, DEFAULT_AGENT_COMMAND } from "./lib/agents";
import TabIcon from "./components/TabIcon";
import { PanelsContext, type Slots } from "./lib/panels";
import {
  DEFAULT_LAYOUT,
  HANDLE_SIZE,
  LAYOUT_LIMITS,
  clamp,
  loadLayout,
  saveLayout,
  type ProjectLayout,
} from "./lib/layout";
import ActionsTab from "./views/project/ActionsTab";
import AgentTab from "./views/project/AgentTab";
import BoardTab from "./views/project/BoardTab";
import McpsTab from "./views/project/McpsTab";
import PlansTab from "./views/project/PlansTab";
import PlaybooksTab from "./views/project/PlaybooksTab";
import SkillsTab from "./views/project/SkillsTab";
import ToolsTab from "./views/project/ToolsTab";
import WorkflowBanner from "./views/project/WorkflowBanner";

const TABS = [
  { id: "board", label: "Board" },
  { id: "playbooks", label: "Playbooks" },
  { id: "plans", label: "Pläne" },
  { id: "skills", label: "Skills" },
  { id: "tools", label: "Tools" },
  { id: "actions", label: "Aktionen" },
  { id: "mcps", label: "MCPs" },
  { id: "agent", label: "Agent" },
  { id: "help", label: "Hilfe" },
] as const;

type TabId = (typeof TABS)[number]["id"];

/** Zwei Tab-Ebenen im Navigator (BO 2026-09-05, Vorbild iKanban): oben die
 *  Gruppen als Icons, darunter die Tabs der Gruppe als Text. „Orga" ist ein
 *  Arbeitsname — Kandidaten: Vorhaben, Wissen, Steuerung. */
const GROUPS: ReadonlyArray<{ id: string; label: string; tabs: readonly TabId[] }> = [
  { id: "board", label: "Board", tabs: ["board"] },
  { id: "orga", label: "Orga", tabs: ["playbooks", "plans", "skills"] },
  { id: "technik", label: "Technik", tabs: ["tools", "actions", "mcps", "agent"] },
  { id: "help", label: "Hilfe", tabs: ["help"] },
];

function groupOf(tab: TabId) {
  return GROUPS.find((group) => group.tabs.includes(tab)) ?? GROUPS[0];
}

/** Aktion aus actions.json, soweit die Toolbar sie braucht. */
interface ToolbarAction {
  name: string;
  command: string;
  confirmed: boolean;
  toolbar?: boolean;
  target: string;
  inputs?: unknown[];
}

/** Agent-Kommando pro Projekt (F3: `claude` als Default, `codex` oder frei
 *  wählbar). localStorage reicht für P1 — es ist eine UI-Präferenz. */
function agentCommandKey(project: string) {
  return `speccify.project.agentCommand:${project}`;
}

export default function ProjectShell() {
  const [project, setProject] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<TabId>("plans");
  const [agentCommand, setAgentCommand] = useState(DEFAULT_AGENT_COMMAND);
  const [terminalStarted, setTerminalStarted] = useState(false);
  const [layout, setLayout] = useState<ProjectLayout>(DEFAULT_LAYOUT);
  const [navSlots, setNavSlots] = useState<Slots>({});
  const [inspectorSlots, setInspectorSlots] = useState<Slots>({});
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [theme, setTheme] = useTheme();
  // Zuletzt aktiver Tab je Gruppe — ein Gruppenwechsel kehrt dorthin zurück.
  const [lastTab, setLastTab] = useState<Record<string, TabId>>({});
  const activateTab = (tab: TabId) => {
    setActive(tab);
    setLastTab((previous) => ({ ...previous, [groupOf(tab).id]: tab }));
  };
  // W7d: Aktionen mit `toolbar: true` als Knöpfe in der Toolbar.
  const [toolbarActions, setToolbarActions] = useState<ToolbarAction[]>([]);

  useEffect(() => {
    void invoke<string | null>("project_current")
      .then((root) => {
        if (!root) {
          setError("Dieses Fenster kennt kein Projekt (project_current leer).");
          return;
        }
        setProject(root);
        setLayout(loadLayout(root));
        try {
          const stored = localStorage.getItem(agentCommandKey(root));
          if (stored !== null) setAgentCommand(stored);
        } catch {
          // localStorage nicht verfügbar — Default bleibt.
        }
      })
      .catch((e) => setError(String(e)));
  }, []);

  // W2: Watcher-Basisdienst — der Rust-Poll meldet geänderte Bereiche,
  // die Tabs laden dann nach (statt „Aktualisieren"-Knopf).
  const [refresh, setRefresh] = useState<Record<string, number>>({});
  useEffect(() => {
    if (!project) return;
    void invoke("project_watch_start", { project });
    const unlisten = listen<{ areas: string[] }>("project-changed", (event) => {
      setRefresh((previous) => {
        const next = { ...previous };
        for (const area of event.payload.areas) next[area] = (next[area] ?? 0) + 1;
        return next;
      });
    });
    return () => {
      void unlisten.then((dispose) => dispose());
      void invoke("project_watch_stop");
    };
  }, [project]);

  // Agent-Läufe als Aktivität: der Watcher meldet Board-Änderungen, die
  // KPI-Liste liefert die letzten agent_run-Events — neue seit dem letzten
  // Blick landen als abgeschlossene Aktivität mit Ticket und Tokens.
  const lastRunSeen = useRef<string | null>(null);
  useEffect(() => {
    if (!project) return;
    void invoke<{
      recent: Array<{
        ticket_id: string;
        timestamp: string;
        summary: string;
        tokens_in: number;
        tokens_out: number;
        duration_ms: number;
      }>;
    }>("project_board_kpis", { project })
      .then((kpis) => {
        const runs = kpis.recent;
        if (lastRunSeen.current === null) {
          lastRunSeen.current = runs[0]?.timestamp ?? "";
          return;
        }
        const fresh = runs.filter((run) => run.timestamp > (lastRunSeen.current ?? ""));
        for (const run of [...fresh].reverse()) {
          recordActivity("agent", `Agent: ${run.summary}`, {
            detail: `${run.ticket_id} · ↑${run.tokens_in} ↓${run.tokens_out}`,
            durationMs: run.duration_ms,
            outcome: /abort|fail|error/i.test(run.summary) ? "error" : "ok",
          });
        }
        if (runs[0]) lastRunSeen.current = runs[0].timestamp;
      })
      .catch(() => {});
  }, [project, refresh.board]);

  // Tabs aus anderen Bereichen anspringen (lib/panels.ts `showTab`) —
  // etwa der Leerzustand von Tools, der zu den Skills schickt.
  useEffect(() => {
    const handler = (event: Event) => {
      const id = (event as CustomEvent<string>).detail as TabId;
      if (TABS.some((tab) => tab.id === id)) activateTab(id);
    };
    window.addEventListener("speccify:show-tab", handler);
    return () => window.removeEventListener("speccify:show-tab", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!project) return;
    void invoke<{ actions: ToolbarAction[] }>("project_actions", { project })
      .then((snapshot) =>
        setToolbarActions(
          snapshot.actions.filter(
            (action) =>
              action.toolbar &&
              action.confirmed &&
              action.target === "local" &&
              !action.command.startsWith("toolui:"),
          ),
        ),
      )
      .catch(() => setToolbarActions([]));
  }, [project, refresh.actions]);

  const updateLayout = useCallback(
    (patch: Partial<ProjectLayout> | ((previous: ProjectLayout) => Partial<ProjectLayout>)) => {
      setLayout((previous) => {
        const next = { ...previous, ...(typeof patch === "function" ? patch(previous) : patch) };
        if (project) saveLayout(project, next);
        return next;
      });
    },
    [project],
  );

  // Tastaturkürzel wie in Xcode: Cmd/Ctrl+0 Navigator, Cmd/Ctrl+Alt+0
  // Inspektor, Cmd/Ctrl+Shift+Y Terminal unten, Cmd/Ctrl+1…4 Bereiche.
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const mod = isMac ? event.metaKey : event.ctrlKey;
      if (!mod) return;
      const target = event.target as HTMLElement | null;
      const typing =
        target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
      if (event.key === "0" && !event.altKey) {
        event.preventDefault();
        updateLayout((previous) => ({ navShown: !previous.navShown }));
      } else if (event.key === "0" && event.altKey) {
        event.preventDefault();
        updateLayout((previous) => ({ rightShown: !previous.rightShown }));
      } else if (event.shiftKey && event.key.toLowerCase() === "y") {
        event.preventDefault();
        updateLayout((previous) =>
          previous.terminalDock === "bottom"
            ? { bottomShown: !previous.bottomShown }
            : { terminalDock: "bottom", bottomShown: true, rightTab: "inspector" },
        );
      } else if (!typing && !event.altKey && !event.shiftKey && /^[1-4]$/.test(event.key)) {
        const group = GROUPS[Number(event.key) - 1];
        if (group) {
          event.preventDefault();
          activateTab(lastTab[group.id] ?? group.tabs[0]);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastTab, updateLayout]);

  const updateAgentCommand = (value: string) => {
    setAgentCommand(value);
    if (project) {
      try {
        localStorage.setItem(agentCommandKey(project), value);
      } catch {
        // dito
      }
    }
  };

  // Stabile Ref-Callbacks je Tab: ein inline erzeugter Ref würde bei jedem
  // Render neu gesetzt (null → Element) und über setSlots eine Endlosschleife
  // auslösen. So feuern sie nur bei Mount/Unmount des Slots.
  const [navRefs, inspectorRefs] = useMemo(() => {
    const make = (setter: typeof setNavSlots) => {
      const refs: Record<string, (element: HTMLElement | null) => void> = {};
      for (const tab of TABS) {
        refs[tab.id] = (element) =>
          setter((previous) =>
            previous[tab.id] === element ? previous : { ...previous, [tab.id]: element },
          );
      }
      return refs;
    };
    return [make(setNavSlots), make(setInspectorSlots)];
  }, []);

  const panelsApi = useMemo(
    () => ({
      navigator: navSlots,
      inspector: inspectorSlots,
      reveal: () => updateLayout((previous) => (previous.rightShown ? { rightTab: "inspector" } : {})),
    }),
    [navSlots, inspectorSlots, updateLayout],
  );

  if (error) {
    return (
      <div className="p-6">
        <ErrorBox message={error} />
      </div>
    );
  }
  if (!project) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Spinner large />
      </div>
    );
  }

  const { navShown, rightShown, terminalDock } = layout;
  const bottomVisible = terminalDock === "bottom" && layout.bottomShown;
  const terminalVisible =
    terminalDock === "right" ? rightShown && layout.rightTab === "terminal" : bottomVisible;
  const inspectorVisible = rightShown && (terminalDock === "bottom" || layout.rightTab === "inspector");

  // Spalten: Navigator | Griff | Inhalt | Griff | rechte Seitenleiste.
  // Zeilen: Toolbar | Tabzeile rechts | Körper | Griff | Bottom-Bar.
  const gridStyle: CSSProperties = {
    display: "grid",
    gridTemplateColumns: [
      `${navShown ? layout.navWidth : 0}px`,
      `${navShown ? HANDLE_SIZE : 0}px`,
      "minmax(0, 1fr)",
      `${rightShown ? HANDLE_SIZE : 0}px`,
      `${rightShown ? layout.rightWidth : 0}px`,
    ].join(" "),
    gridTemplateRows: [
      "auto",
      "auto",
      "minmax(0, 1fr)",
      `${bottomVisible ? HANDLE_SIZE : 0}px`,
      `${bottomVisible ? layout.bottomHeight : 0}px`,
    ].join(" "),
  };
  const terminalCell: CSSProperties =
    terminalDock === "right"
      ? { gridColumn: 5, gridRow: "3 / -1" }
      : { gridColumn: 3, gridRow: 5 };

  const activeGroup = groupOf(active);
  const toolbarItems: ToolbarItem[] = toolbarActions.map((action) => ({
    id: action.command,
    title: `${action.name} — ${action.command}`,
    label: action.name,
    icon: <PlayIcon />,
    onClick: () => {
      if (action.inputs && action.inputs.length > 0) {
        // Mit Eingaben: im Aktionen-Tab ausfüllen und starten.
        activateTab("actions");
        return;
      }
      window.dispatchEvent(new CustomEvent("speccify:run-action", { detail: action.command }));
    },
  }));

  const dockLabel = terminalDock === "right" ? "⬓ nach unten" : "⬔ nach rechts";
  const toggleDock = () =>
    updateLayout((previous) =>
      previous.terminalDock === "right"
        ? { terminalDock: "bottom", bottomShown: true, rightTab: "inspector" }
        : { terminalDock: "right", rightShown: true, rightTab: "terminal" },
    );

  return (
    <PanelsContext.Provider value={panelsApi}>
      <div className="h-screen bg-slate-50 text-slate-900" style={gridStyle}>
        {/* Toolbar (components/Toolbar.tsx) — Mitte für konfigurierbare Knöpfe
            und ein Aktivitäts-Fenster vorbereitet (`items`), rechts die Schalter. */}
        <div style={{ gridColumn: "1 / -1", gridRow: 1 }}>
          <Toolbar
            title={project.split(/[\\/]/).pop() || project}
            subtitle={project}
            items={toolbarItems}
            center={<ActivityView />}
            trailing={
              <>
            <ToolbarButton
              active={navShown}
              title={`${navShown ? "Navigator ausblenden" : "Navigator einblenden"} (${isMac ? "⌘" : "Strg+"}0)`}
              onClick={() => updateLayout({ navShown: !navShown })}
            >
              <PanelIcon part="nav" />
            </ToolbarButton>
            <ToolbarButton
              active={bottomVisible}
              title={
                terminalDock === "bottom"
                  ? bottomVisible
                    ? "Terminal unten ausblenden"
                    : "Terminal unten einblenden"
                  : "Terminal nach unten legen"
              }
              onClick={() =>
                terminalDock === "bottom"
                  ? updateLayout({ bottomShown: !layout.bottomShown })
                  : toggleDock()
              }
            >
              <PanelIcon part="bottom" />
            </ToolbarButton>
            <ToolbarButton
              active={rightShown}
              title={`${rightShown ? "Inspektor ausblenden" : "Inspektor einblenden"} (${isMac ? "⌥⌘" : "Strg+Alt+"}0)`}
              onClick={() => updateLayout({ rightShown: !rightShown })}
            >
              <PanelIcon part="right" />
            </ToolbarButton>
            <span className="mx-1 h-4 w-px bg-slate-200" aria-hidden="true" />
            <ToolbarButton
              title={isDark(theme) ? "Hell schalten" : "Dunkel schalten"}
              onClick={() => void setTheme(isDark(theme) ? "light" : "dark")}
            >
              {isDark(theme) ? <SunIcon /> : <MoonIcon />}
            </ToolbarButton>
            <ToolbarButton
              title="Einstellungen"
              onClick={() => setSettingsOpen(true)}
              active={settingsOpen}
            >
              <GearIcon />
            </ToolbarButton>
              </>
            }
          />
        </div>

        {/* Navigator: Icon-Tab-Leiste (iKanban SidebarTabBar) + Liste des Tabs */}
        <nav
          className={`${navShown ? "flex" : "hidden"} min-h-0 flex-col border-r border-slate-200 bg-white`}
          style={{ gridColumn: 1, gridRow: "2 / -1" }}
        >
          {/* Ebene 1: Gruppen als Icons */}
          <div className="px-2 py-1.5">
            <div
              role="tablist"
              aria-label="Bereiche"
              className="flex gap-0.5 rounded-full bg-slate-100 p-0.5"
            >
              {GROUPS.map((group) => (
                <button
                  key={group.id}
                  role="tab"
                  aria-selected={activeGroup.id === group.id}
                  aria-label={group.label}
                  title={`${group.label} (${isMac ? "⌘" : "Strg+"}${GROUPS.indexOf(group) + 1})`}
                  onClick={() => activateTab(lastTab[group.id] ?? group.tabs[0])}
                  className={`flex min-h-6 flex-1 items-center justify-center rounded-full ${
                    activeGroup.id === group.id
                      ? "bg-slate-800 text-white"
                      : "text-slate-500 hover:bg-slate-200 hover:text-slate-800"
                  }`}
                >
                  <TabIcon id={group.id} />
                </button>
              ))}
            </div>
          </div>
          {/* Ebene 2: Tabs der Gruppe (nur wenn es mehr als einen gibt) */}
          {activeGroup.tabs.length > 1 ? (
            <div role="tablist" aria-label={activeGroup.label} className="flex gap-1 px-2 pb-1">
              {activeGroup.tabs.map((id) => {
                const tab = TABS.find((entry) => entry.id === id);
                if (!tab) return null;
                return (
                  <button
                    key={id}
                    role="tab"
                    aria-selected={active === id}
                    onClick={() => activateTab(id)}
                    className={`rounded px-2 py-1 text-xs font-medium ${
                      active === id
                        ? "bg-slate-200 text-slate-900"
                        : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>
          ) : (
            <h2 className="px-3 pb-1 text-xs font-semibold text-slate-500">
              {TABS.find((tab) => tab.id === active)?.label}
            </h2>
          )}
          {/* Ein Listen-Slot pro Tab — die Tabs portalen ihre Liste hinein
              (lib/panels.tsx); nur der aktive ist sichtbar. */}
          <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
            {/* Slots nur bei sichtbarem Navigator — sonst rendern die Tabs
                ihre Liste inline (Fallback). */}
            {navShown
              ? TABS.map((tab) => (
                  <div
                    key={tab.id}
                    ref={navRefs[tab.id]}
                    data-nav-slot={tab.id}
                    className={active === tab.id ? "block" : "hidden"}
                  />
                ))
              : null}
          </div>
        </nav>
        {navShown ? (
          <SplitHandle
            axis="x"
            size={layout.navWidth}
            onResize={(next) => updateLayout({ navWidth: clamp(next, LAYOUT_LIMITS.nav) })}
            onReset={() => updateLayout({ navWidth: DEFAULT_LAYOUT.navWidth })}
            style={{ gridColumn: 2, gridRow: "2 / -1" }}
          />
        ) : null}

        {/* Inhalt */}
        <main
          className="flex min-h-0 min-w-0 flex-col overflow-hidden p-5"
          style={{ gridColumn: 3, gridRow: "2 / 4" }}
        >
          <WorkflowBanner project={project} />
          {/* Tabs bleiben gemountet (nur versteckt): Wechsel sofortig, Fetch-State erhalten. */}
          <div className={active === "board" ? "min-h-0 flex-1" : "hidden"}>
            <BoardTab project={project} refresh={refresh.board} planRefresh={refresh.plans} />
          </div>
          <div className={active === "plans" ? "min-h-0 flex-1" : "hidden"}>
            <PlansTab project={project} refresh={refresh.plans} />
          </div>
          <div className={active === "playbooks" ? "min-h-0 flex-1" : "hidden"}>
            <PlaybooksTab project={project} refresh={refresh.playbooks} />
          </div>
          <div className={active === "skills" ? "min-h-0 flex-1" : "hidden"}>
            <SkillsTab project={project} refresh={refresh.skills} />
          </div>
          <div className={active === "tools" ? "min-h-0 flex-1" : "hidden"}>
            <ToolsTab project={project} refresh={refresh.tools} />
          </div>
          <div className={active === "actions" ? "min-h-0 flex-1" : "hidden"}>
            <ActionsTab project={project} refresh={refresh.actions} />
          </div>
          <div className={active === "mcps" ? "min-h-0 flex-1" : "hidden"}>
            <McpsTab project={project} refresh={refresh.mcps} />
          </div>
          <div className={active === "help" ? "min-h-0 flex-1" : "hidden"}>
            <HelpView />
          </div>
          <div className={active === "agent" ? "min-h-0 flex-1" : "hidden"}>
            <AgentTab
              project={project}
              refresh={refresh.agent}
              agentCommand={agentCommand}
              onAgentCommand={updateAgentCommand}
            />
          </div>
        </main>

        {/* Bottom-Bar-Griff (nur bei Terminal unten) */}
        {bottomVisible ? (
          <SplitHandle
            axis="y"
            size={layout.bottomHeight}
            invert
            onResize={(next) => updateLayout({ bottomHeight: clamp(next, LAYOUT_LIMITS.bottom) })}
            onReset={() => updateLayout({ bottomHeight: DEFAULT_LAYOUT.bottomHeight })}
            style={{ gridColumn: 3, gridRow: 4 }}
          />
        ) : null}

        {/* Rechte Seitenleiste: Griff, Tabzeile, Inspektor */}
        {rightShown ? (
          <SplitHandle
            axis="x"
            size={layout.rightWidth}
            invert
            onResize={(next) => updateLayout({ rightWidth: clamp(next, LAYOUT_LIMITS.right) })}
            onReset={() => updateLayout({ rightWidth: DEFAULT_LAYOUT.rightWidth })}
            style={{ gridColumn: 4, gridRow: "2 / -1" }}
          />
        ) : null}
        <div
          className={`${rightShown ? "flex" : "hidden"} items-stretch border-b border-l border-slate-200 bg-white text-xs`}
          style={{ gridColumn: 5, gridRow: 2 }}
        >
          {(terminalDock === "right"
            ? ([
                ["inspector", "Inspektor"],
                ["terminal", "Terminal"],
              ] as const)
            : ([["inspector", "Inspektor"]] as const)
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => updateLayout({ rightTab: id })}
              className={`px-3 py-1.5 font-medium ${
                layout.rightTab === id || terminalDock === "bottom"
                  ? "border-b-2 border-slate-800 text-slate-800"
                  : "text-slate-400 hover:text-slate-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <aside
          className={`inspector-body ${inspectorVisible ? "flex" : "hidden"} min-h-0 flex-col overflow-y-auto border-l border-slate-200 bg-white`}
          style={{ gridColumn: 5, gridRow: "3 / -1" }}
        >
          {/* Ein Slot pro Tab — nur der aktive ist sichtbar; die Tabs
              portalen ihr Detail hinein (lib/panels.tsx). */}
          {rightShown
            ? TABS.map((tab) => (
                <div
                  key={tab.id}
                  ref={inspectorRefs[tab.id]}
                  data-slot={tab.id}
                  className={`${active === tab.id ? "flex" : "hidden"} min-h-0 flex-1 flex-col`}
                />
              ))
            : null}
          <p className="inspector-placeholder p-4 text-xs text-slate-400">
            Nichts ausgewählt. Der Inspektor zeigt Details und Aktionen zur Auswahl —
            wähle links etwas aus der Liste oder im Board ein Ticket.
          </p>
        </aside>

        {/* Agent-Terminal: ein Element, zwei mögliche Grid-Zellen */}
        <section
          className={`keep-dark ${terminalVisible ? "flex" : "hidden"} min-h-0 min-w-0 flex-col bg-slate-900 ${
            terminalDock === "right" ? "border-l border-slate-700" : "border-t border-slate-700"
          }`}
          style={terminalCell}
        >
          <div className="flex justify-end px-2 pt-1">
            <button
              onClick={toggleDock}
              title={
                terminalDock === "right" ? "Terminal nach unten legen" : "Terminal nach rechts legen"
              }
              className="rounded px-2 py-0.5 text-xs text-slate-500 hover:bg-slate-800 hover:text-slate-300"
            >
              {dockLabel}
            </button>
          </div>
          {terminalStarted ? (
            <TerminalPanel visible={terminalVisible} cwd={project} autostart={agentCommand} />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6">
              <label className="w-full max-w-xs">
                <span className="mb-1 block text-xs font-medium text-slate-400">
                  Agent-Kommando (leer = nur Shell)
                </span>
                <input
                  value={agentCommand}
                  onChange={(event) => updateAgentCommand(event.target.value)}
                  placeholder="claude"
                  spellCheck={false}
                  className="w-full rounded border border-slate-600 bg-slate-800 px-3 py-2 font-mono text-sm text-slate-100"
                />
                <span className="mt-2 flex flex-wrap gap-1.5">
                  {AGENT_PRESETS.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => updateAgentCommand(preset.command)}
                      className={`rounded px-2 py-1 text-xs ${
                        agentCommand === preset.command
                          ? "bg-slate-600 text-white"
                          : "bg-slate-800 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </span>
              </label>
              <button
                onClick={() => setTerminalStarted(true)}
                className="rounded bg-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-600"
              >
                Agent-Terminal starten
              </button>
              <p className="max-w-xs text-center text-xs text-slate-500">
                Startet im Projektverzeichnis — Skills leben unter{" "}
                <code>.agent/skills</code> und werden für den gewählten Host verlinkt.
              </p>
            </div>
          )}
        </section>
      </div>
      {settingsOpen ? (
        <SettingsSheet
          theme={theme}
          onTheme={(next) => void setTheme(next)}
          layout={layout}
          onDock={(dock) =>
            updateLayout(
              dock === "bottom"
                ? { terminalDock: "bottom", bottomShown: true, rightTab: "inspector" }
                : { terminalDock: "right", rightShown: true, rightTab: "terminal" },
            )
          }
          onResetLayout={() => updateLayout({ ...DEFAULT_LAYOUT })}
          onClose={() => setSettingsOpen(false)}
        />
      ) : null}
    </PanelsContext.Provider>
  );
}
