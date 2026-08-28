// Tools-Tab (Plan projektfenster.md, P3): Specs aus .agent/tools/ mit
// Status je Plattform aus expansions.yaml. Die Lücke „fehlt auf dieser
// Plattform" ist prominent — sie ist die Aufgabenliste für den Agenten
// im Terminal rechts (expand implementiert, `tool check` verifiziert).

import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { LoadingBoundary, useAsync } from "../../components/ui";

interface ToolPlatform {
  name: string;
  status: string | null;
  checked: string | null;
}

export interface ToolEntry {
  name: string;
  file: string;
  description: string | null;
  from: string[];
  platforms: ToolPlatform[];
  files: string[];
}

function statusTone(status: string | null | undefined) {
  if (status === "verified") return "bg-emerald-100 text-emerald-800";
  if (status === "implemented") return "bg-sky-100 text-sky-800";
  return "bg-slate-200 text-slate-600";
}

export default function ToolsTab({ project }: { project: string }) {
  const list = useAsync(
    () => invoke<ToolEntry[]>("project_tools", { project }),
    `tools:${project}`,
  );
  const platform = useAsync(() => invoke<string>("project_platform"), "platform");
  const [selected, setSelected] = useState<string | null>(null);
  const spec = useAsync(
    () =>
      selected
        ? invoke<string>("project_read_file", { project, file: selected })
        : Promise.resolve(""),
    `tool-spec:${project}:${selected ?? ""}`,
  );

  const tools = list.data ?? [];
  const here = platform.data ?? "";
  const selectedTool = tools.find((tool) => tool.file === selected) ?? null;
  const hereStatus = (tool: ToolEntry) =>
    tool.platforms.find((entry) => entry.name === here)?.status ?? null;

  return (
    <LoadingBoundary loading={list.loading} error={list.error} label="Tools lesen…">
      {tools.length === 0 ? (
        <p className="text-sm text-slate-500">
          Keine Tools unter <code>.agent/tools/</code> — Tool-Specs kommen mit
          Skills über <code>speccify expand</code> ins Projekt.
        </p>
      ) : (
        <div className="flex h-full min-h-0 gap-4">
          <div className="w-72 shrink-0 overflow-y-auto pr-1">
            <ul className="space-y-1">
              {tools.map((tool) => (
                <li key={tool.file}>
                  <button
                    onClick={() => setSelected(tool.file)}
                    className={`w-full rounded px-2 py-1.5 text-left text-sm ${
                      selected === tool.file
                        ? "bg-slate-800 text-white"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    <span className="mr-2">{tool.name}</span>
                    <span
                      className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${statusTone(hereStatus(tool))}`}
                    >
                      {hereStatus(tool) ?? "fehlt hier"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="min-w-0 flex-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-5">
            {selectedTool ? (
              <>
                {hereStatus(selectedTool) === null && here ? (
                  <p className="mb-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    <span className="font-semibold">
                      Fehlt auf dieser Plattform ({here}).
                    </span>{" "}
                    Bitte den Agenten rechts, die Implementierung zu schreiben —
                    <code className="mx-1">speccify tool check {selectedTool.name}</code>
                    verifiziert sie.
                  </p>
                ) : null}
                <div className="mb-3 flex flex-wrap gap-2 text-xs text-slate-600">
                  {selectedTool.platforms.map((entry) => (
                    <span
                      key={entry.name}
                      className={`rounded-full px-2 py-0.5 font-medium ${statusTone(entry.status)}`}
                      title={entry.checked ? `geprüft ${entry.checked}` : undefined}
                    >
                      {entry.name}: {entry.status ?? "?"}
                    </span>
                  ))}
                  {selectedTool.from.length > 0 ? (
                    <span className="text-slate-400">
                      aus {selectedTool.from.join(", ")}
                    </span>
                  ) : null}
                </div>
                {selectedTool.files.length > 0 ? (
                  <p className="mb-3 text-xs text-slate-500">
                    Dateien:{" "}
                    {selectedTool.files.map((file) => (
                      <code key={file} className="mr-2">
                        {file}
                      </code>
                    ))}
                  </p>
                ) : null}
                <LoadingBoundary loading={spec.loading} error={spec.error} label="Spec lesen…">
                  <Markdown text={stripFrontmatter(spec.data ?? "")} />
                </LoadingBoundary>
              </>
            ) : (
              <p className="text-sm text-slate-400">Tool links auswählen.</p>
            )}
          </div>
        </div>
      )}
    </LoadingBoundary>
  );
}
