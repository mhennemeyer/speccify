// Projektfenster (Plan projektfenster.md, P1): drei Bereiche — links die
// Bestände (Pläne, Skills, Tools, MCPs, Agent), Mitte der Inhalt des Tabs,
// rechts das Agent-Terminal im Projekt-cwd. Die Wurzel kommt über
// `project_current` (Fenster-Label → Registry, D15).

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import TerminalPanel from "./components/TerminalPanel";
import { ErrorBox, Spinner } from "./components/ui";
import AgentTab from "./views/project/AgentTab";
import BoardTab from "./views/project/BoardTab";
import McpsTab from "./views/project/McpsTab";
import PlansTab from "./views/project/PlansTab";
import SkillsTab from "./views/project/SkillsTab";
import ToolsTab from "./views/project/ToolsTab";

const TABS = [
  { id: "board", label: "Board" },
  { id: "plans", label: "Pläne" },
  { id: "skills", label: "Skills" },
  { id: "tools", label: "Tools" },
  { id: "mcps", label: "MCPs" },
  { id: "agent", label: "Agent" },
] as const;

type TabId = (typeof TABS)[number]["id"];

/** Agent-Kommando pro Projekt (F3: `claude` als Default, `codex` oder frei
 *  wählbar). localStorage reicht für P1 — es ist eine UI-Präferenz. */
function agentCommandKey(project: string) {
  return `speccify.project.agentCommand:${project}`;
}

/** Windows-Default `claude.cmd`: PowerShell verweigert das npm-Shim
 *  `claude.ps1` per ExecutionPolicy (P2-Befund) — das cmd-Shim läuft immer. */
const DEFAULT_AGENT_COMMAND = navigator.userAgent.includes("Windows")
  ? "claude.cmd"
  : "claude";

/** Terminal-Position pro Projekt (BO-Finding 2026-08-28: rechts ODER unten). */
type TerminalPosition = "right" | "bottom";

function terminalPositionKey(project: string) {
  return `speccify.project.terminalPosition:${project}`;
}

export default function ProjectShell() {
  const [project, setProject] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<TabId>("plans");
  const [agentCommand, setAgentCommand] = useState(DEFAULT_AGENT_COMMAND);
  const [terminalStarted, setTerminalStarted] = useState(false);
  const [terminalPosition, setTerminalPosition] = useState<TerminalPosition>("right");

  useEffect(() => {
    void invoke<string | null>("project_current")
      .then((root) => {
        if (!root) {
          setError("Dieses Fenster kennt kein Projekt (project_current leer).");
          return;
        }
        setProject(root);
        try {
          const stored = localStorage.getItem(agentCommandKey(root));
          if (stored !== null) setAgentCommand(stored);
          if (localStorage.getItem(terminalPositionKey(root)) === "bottom") {
            setTerminalPosition("bottom");
          }
        } catch {
          // localStorage nicht verfügbar — Default bleibt.
        }
      })
      .catch((e) => setError(String(e)));
  }, []);

  const toggleTerminalPosition = () => {
    const next: TerminalPosition = terminalPosition === "right" ? "bottom" : "right";
    setTerminalPosition(next);
    if (project) {
      try {
        localStorage.setItem(terminalPositionKey(project), next);
      } catch {
        // dito
      }
    }
  };

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

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <nav className="flex w-40 shrink-0 flex-col border-r border-slate-200 bg-white p-3">
        <h1
          className="mb-1 truncate px-2 text-sm font-bold text-slate-700"
          title={project}
        >
          {project.split(/[\\/]/).pop() || project}
        </h1>
        <p className="mb-4 truncate px-2 font-mono text-[10px] text-slate-400" title={project}>
          {project}
        </p>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`mb-1 rounded px-3 py-2 text-left text-sm ${
              active === tab.id
                ? "bg-slate-800 text-white"
                : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div
        className={`flex min-h-0 min-w-0 flex-1 ${
          terminalPosition === "right" ? "flex-row" : "flex-col"
        }`}
      >
      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden p-5">
        {/* Tabs bleiben gemountet (nur versteckt): Wechsel sofortig, Fetch-State erhalten. */}
        <div className={active === "board" ? "min-h-0 flex-1" : "hidden"}>
          <BoardTab project={project} />
        </div>
        <div className={active === "plans" ? "min-h-0 flex-1" : "hidden"}>
          <PlansTab project={project} />
        </div>
        <div className={active === "skills" ? "min-h-0 flex-1" : "hidden"}>
          <SkillsTab project={project} />
        </div>
        <div className={active === "tools" ? "min-h-0 flex-1" : "hidden"}>
          <ToolsTab project={project} />
        </div>
        <div className={active === "mcps" ? "min-h-0 flex-1" : "hidden"}>
          <McpsTab project={project} />
        </div>
        <div className={active === "agent" ? "min-h-0 flex-1" : "hidden"}>
          <AgentTab
            project={project}
            agentCommand={agentCommand}
            onAgentCommand={updateAgentCommand}
          />
        </div>
      </main>

      <aside
        className={`flex shrink-0 flex-col border-slate-700 bg-slate-900 ${
          terminalPosition === "right" ? "w-[480px] border-l" : "h-[320px] border-t"
        }`}
      >
        <div className="flex justify-end px-2 pt-1">
          <button
            onClick={toggleTerminalPosition}
            title={
              terminalPosition === "right"
                ? "Terminal nach unten legen"
                : "Terminal nach rechts legen"
            }
            className="rounded px-2 py-0.5 text-xs text-slate-500 hover:bg-slate-800 hover:text-slate-300"
          >
            {terminalPosition === "right" ? "⬓ unten" : "⬔ rechts"}
          </button>
        </div>
        {terminalStarted ? (
          <TerminalPanel visible cwd={project} autostart={agentCommand} />
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
            </label>
            <button
              onClick={() => setTerminalStarted(true)}
              className="rounded bg-slate-700 px-4 py-2 text-sm text-slate-200 hover:bg-slate-600"
            >
              Agent-Terminal starten
            </button>
            <p className="max-w-xs text-center text-xs text-slate-500">
              Startet im Projektverzeichnis — der Agent findet Skills und Pläne
              über <code>.claude/</code> und <code>.agent/</code> selbst.
            </p>
          </div>
        )}
      </aside>
      </div>
    </div>
  );
}
