// Agent-Tab (Plan projektfenster.md, P3): CLAUDE.md/AGENTS.md anzeigen und
// das Agent-Kommando des Projekts umstellen (F3: Default claude, aber codex
// oder frei — nichts fest verdrahten). Das Kommando greift beim nächsten
// „Agent-Terminal starten" bzw. „Neu starten".

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { LoadingBoundary, useAsync } from "../../components/ui";
import { AGENT_PRESETS } from "../../lib/agents";
import { NavigatorPortal, NavRow } from "../../lib/panels";

export default function AgentTab({
  project,
  refresh,
  agentCommand,
  onAgentCommand,
}: {
  project: string;
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
      <LoadingBoundary loading={files.loading} error={files.error} label="Agent-Dateien suchen…">
        {available.length === 0 ? (
          <p className="text-sm text-slate-500">
            Keine <code>CLAUDE.md</code>/<code>AGENTS.md</code> im Projekt.
          </p>
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
