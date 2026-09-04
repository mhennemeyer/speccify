// Projektfenster (Plan projektfenster.md, P1 → W7-Layout): das Xcode-/
// iKanban-Muster — Navigator links (Tabs), Inhalt in der Mitte, rechts der
// Inspektor mit eigenen Tabs; das Agent-Terminal lebt wahlweise als Tab in
// der rechten Seitenleiste oder als höhenverstellbare Bottom-Bar. Alles
// ist ein CSS-Grid: das Terminal bleibt dasselbe React-Element und wechselt
// nur seine Grid-Zelle — sonst würde der PTY beim Umdocken sterben.
// Die Wurzel kommt über `project_current` (Fenster-Label → Registry, D15).

import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import SplitHandle from "./components/SplitHandle";
import TerminalPanel from "./components/TerminalPanel";
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

/** Agent-Kommando pro Projekt (F3: `claude` als Default, `codex` oder frei
 *  wählbar). localStorage reicht für P1 — es ist eine UI-Präferenz. */
function agentCommandKey(project: string) {
  return `speccify.project.agentCommand:${project}`;
}

/** Xcode-artige Umschalter für die drei Bereiche. */
function PanelIcon({ part }: { part: "nav" | "right" | "bottom" }) {
  return (
    <svg width="16" height="14" viewBox="0 0 16 14" aria-hidden="true">
      <rect x="0.5" y="0.5" width="15" height="13" rx="2" fill="none" stroke="currentColor" />
      {part === "nav" ? <rect x="1" y="1" width="5" height="12" fill="currentColor" /> : null}
      {part === "right" ? <rect x="10" y="1" width="5" height="12" fill="currentColor" /> : null}
      {part === "bottom" ? <rect x="1" y="9" width="14" height="4" fill="currentColor" /> : null}
    </svg>
  );
}

function ToolbarToggle({
  active,
  title,
  onClick,
  children,
}: {
  active: boolean;
  title: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-pressed={active}
      className={`rounded px-1.5 py-1 ${
        active ? "text-slate-800 hover:bg-slate-200" : "text-slate-400 hover:bg-slate-200 hover:text-slate-700"
      }`}
    >
      {children}
    </button>
  );
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
        {/* Toolbar */}
        <header
          className="flex items-center gap-3 border-b border-slate-200 bg-white px-3 py-1"
          style={{ gridColumn: "1 / -1", gridRow: 1 }}
        >
          <h1 className="truncate text-sm font-bold text-slate-700" title={project}>
            {project.split(/[\\/]/).pop() || project}
          </h1>
          <p className="min-w-0 flex-1 truncate font-mono text-[10px] text-slate-400" title={project}>
            {project}
          </p>
          <div className="flex items-center gap-0.5">
            <ToolbarToggle
              active={navShown}
              title={navShown ? "Navigator ausblenden" : "Navigator einblenden"}
              onClick={() => updateLayout({ navShown: !navShown })}
            >
              <PanelIcon part="nav" />
            </ToolbarToggle>
            <ToolbarToggle
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
            </ToolbarToggle>
            <ToolbarToggle
              active={rightShown}
              title={rightShown ? "Inspektor ausblenden" : "Inspektor einblenden"}
              onClick={() => updateLayout({ rightShown: !rightShown })}
            >
              <PanelIcon part="right" />
            </ToolbarToggle>
          </div>
        </header>

        {/* Navigator: Icon-Tab-Leiste (iKanban SidebarTabBar) + Liste des Tabs */}
        <nav
          className={`${navShown ? "flex" : "hidden"} min-h-0 flex-col border-r border-slate-200 bg-white`}
          style={{ gridColumn: 1, gridRow: "2 / -1" }}
        >
          <div className="px-2 py-1.5">
            <div
              role="tablist"
              className="flex gap-0.5 rounded-full bg-slate-100 p-0.5"
            >
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  role="tab"
                  aria-selected={active === tab.id}
                  aria-label={tab.label}
                  title={tab.label}
                  onClick={() => setActive(tab.id)}
                  className={`flex min-h-6 flex-1 items-center justify-center rounded-full ${
                    active === tab.id
                      ? "bg-slate-800 text-white"
                      : "text-slate-500 hover:bg-slate-200 hover:text-slate-800"
                  }`}
                >
                  <TabIcon id={tab.id} />
                </button>
              ))}
            </div>
          </div>
          <h2 className="px-3 pb-1 text-xs font-semibold text-slate-500">
            {TABS.find((tab) => tab.id === active)?.label}
          </h2>
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
            Nichts ausgewählt. Der Inspektor zeigt das Detail der Auswahl — im Board
            das angeklickte Ticket.
          </p>
        </aside>

        {/* Agent-Terminal: ein Element, zwei mögliche Grid-Zellen */}
        <section
          className={`${terminalVisible ? "flex" : "hidden"} min-h-0 min-w-0 flex-col bg-slate-900 ${
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
    </PanelsContext.Provider>
  );
}
