// Agent-Tab (Plan projektfenster.md, P3): CLAUDE.md/AGENTS.md anzeigen und
// das Agent-Kommando des Projekts umstellen (F3: Default claude, aber codex
// oder frei — nichts fest verdrahten). Das Kommando greift beim nächsten
// „Agent-Terminal starten" bzw. „Neu starten".

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { LoadingBoundary, useAsync } from "../../components/ui";
import { AGENT_PRESETS } from "../../lib/agents";
import {
  InspectorButton,
  InspectorPanel,
  InspectorPortal,
  NavEmpty,
  NavigatorPortal,
  NavRow,
  inlineInspector,
} from "../../lib/panels";
import { copyPrompt } from "../../lib/prompt";
import AgentStartup from "../../components/AgentStartup";

export default function AgentTab({
  project,
  refresh,
  agentCommand,
  onAgentCommand,
  commandRoot,
}: {
  project: string;
  commandRoot?: string;
  refresh?: number;
  agentCommand: string;
  onAgentCommand: (value: string) => void;
}) {
  const files = useAsync(
    () => invoke<string[]>("project_agent_files", { project }),
    `agent-files:${project}`,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const available = files.data ?? [];
  const current = selected ?? available[0] ?? null;
  const body = useAsync(
    () =>
      current
        ? invoke<string>("project_read_file", { project, file: current })
        : Promise.resolve(""),
    `agent-body:${project}:${current ?? ""}`,
  );

  useEffect(() => {
    if (refresh) {
      void files.reload();
      void body.reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="max-w-md">
        {commandRoot && <p className="mb-2 break-all text-xs text-slate-500">Gemeinsamer Workspace-Agent: {commandRoot}. Die Anweisungsdateien unten gehören weiterhin zu diesem Projekt.</p>}
        <label className="mb-1 block text-xs font-medium text-slate-500">
          Agent-Kommando (Terminal-Autostart, leer = nur Shell)
        </label>
        <input
          value={agentCommand}
          onChange={(event) => onAgentCommand(event.target.value)}
          spellCheck={false}
          className="w-full rounded border border-slate-300 px-3 py-1.5 font-mono text-sm"
        />
        <div className="mt-2 flex flex-wrap gap-1.5">
          {AGENT_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => onAgentCommand(preset.command)}
              className={`rounded border px-2 py-1 text-xs ${
                agentCommand === preset.command
                  ? "border-slate-700 bg-slate-700 text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>
      <AgentStartup project={commandRoot ?? project} command={agentCommand} />
      <LoadingBoundary loading={files.loading} error={files.error} label="Agent-Dateien suchen…">
        {available.length === 0 ? (
          <>
            <NavigatorPortal tab="agent" fallback={() => null}>
              <NavEmpty title="Noch keine Agent-Dateien">
                <code>CLAUDE.md</code>, <code>AGENTS.md</code> und <code>.agent/agent.md</code>{" "}
                legt das Workflow-Banner oben mit <em>Einrichten</em> an — sie sind der
                Vertrag zwischen Dir und dem Agenten.
              </NavEmpty>
            </NavigatorPortal>
            <p className="text-sm text-slate-500">
              Keine <code>CLAUDE.md</code>/<code>AGENTS.md</code> im Projekt.
            </p>
          </>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col">
            <NavigatorPortal
              tab="agent"
              fallback={(children) => <div className="mb-2 flex gap-1">{children}</div>}
            >
              {available.map((file) => (
                <NavRow key={file} selected={current === file} onClick={() => setSelected(file)}>
                  <span className="font-mono text-xs">{file}</span>
                </NavRow>
              ))}
            </NavigatorPortal>
            {current ? (
              <InspectorPortal tab="agent" fallback={inlineInspector}>
                <InspectorPanel
                  title={current}
                  subtitle="Agent-Einweisung"
                  meta={[
                    {
                      label: "Rolle",
                      value:
                        current === ".agent/agent.md"
                          ? "Kanonischer Vertrag — von jedem Agenten gelesen"
                          : "Host-Adapter — verweist auf .agent/agent.md",
                    },
                    { label: "Terminal-Kommando", value: agentCommand || "nur Shell" },
                  ]}
                  actions={
                    <InspectorButton
                      title="Pfad + Inhalt als Markdown-Prompt in die Zwischenablage"
                      disabled={body.data === null}
                      onClick={() => void copyPrompt(current, body.data ?? "")}
                    >
                      Als Prompt kopieren
                    </InspectorButton>
                  }
                />
              </InspectorPortal>
            ) : null}
            <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-5">
              <LoadingBoundary loading={body.loading} error={body.error} label="Datei lesen…">
                <Markdown text={stripFrontmatter(body.data ?? "")} />
              </LoadingBoundary>
            </div>
          </div>
        )}
      </LoadingBoundary>
    </div>
  );
}
