// Aktionen-Tab (Plan projektfenster.md, P5/W5, D27/D28): benannte Kommandos
// aus `.agent/actions.json` — bestätigte Aktionen laufen nativ (Spawn im
// Projekt-cwd), Output streamt live, Stop killt. Vorschläge (unbestätigte
// Aktionen + abgelehnte Agent-Befehle aus exec-pending.json) werden mit
// EINEM Klick bestätigt: Aktion + permanenter Allowlist-Eintrag. Eine
// Ausgabezeile `{"kind":"chart",…}` wird live als Diagramm gerendert —
// kaputte Pflichtfelder fallen auf Text zurück, Output geht nie verloren.

import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { LoadingBoundary, useAsync } from "../../components/ui";

interface ActionInput {
  name: string;
  kind: string;
  label?: string | null;
  options?: string[];
  default?: string | null;
}

interface ProjectAction {
  name: string;
  command: string;
  description?: string | null;
  source: string;
  confirmed: boolean;
  toolbar?: boolean;
  shortcut?: string | null;
  inputs?: ActionInput[];
  target: string;
}

interface PendingCommand {
  command: string;
  requested_at?: string | null;
}

interface ActionsSnapshot {
  actions: ProjectAction[];
  pending: PendingCommand[];
}

interface ChartSeries {
  name: string;
  points: [number, number][];
}

interface ChartSpec {
  series: ChartSeries[];
  mark?: string;
  height?: number;
  xLabels?: string[];
}

type OutputItem = { kind: "line"; text: string } | { kind: "chart"; chart: ChartSpec };

interface RunState {
  items: OutputItem[];
  running: boolean;
  exitCode: number | null;
  durationMs: number | null;
  error: string | null;
}

const MAX_ITEMS = 2000;

/** Strikt bei Pflichtfeldern (sonst Text), tolerant bei allem Optionalen. */
function parseChart(line: string): ChartSpec | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("{") || !trimmed.includes('"chart"')) return null;
  try {
    const value = JSON.parse(trimmed);
    if (value?.kind !== "chart" || !Array.isArray(value.series)) return null;
    const series: ChartSeries[] = [];
    for (const entry of value.series) {
      if (typeof entry?.name !== "string" || !Array.isArray(entry.points)) return null;
      const points: [number, number][] = [];
      for (const point of entry.points) {
        if (!Array.isArray(point) || point.length < 2) return null;
        const x = Number(point[0]);
        const y = Number(point[1]);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
        points.push([x, y]);
      }
      series.push({ name: entry.name, points });
    }
    if (series.length === 0) return null;
    return {
      series,
      mark: typeof value.mark === "string" ? value.mark : undefined,
      height: Number.isFinite(value.height) ? Number(value.height) : undefined,
      xLabels: Array.isArray(value.xLabels) ? value.xLabels.map(String) : undefined,
    };
  } catch {
    return null;
  }
}

const CHART_COLORS = ["#0f766e", "#b45309", "#1d4ed8", "#be185d", "#4d7c0f", "#7c3aed"];

function ChartBlock({ chart }: { chart: ChartSpec }) {
  const width = 560;
  const height = Math.min(Math.max(chart.height ?? 160, 80), 400);
  const pad = 28;
  const all = chart.series.flatMap((series) => series.points);
  if (all.length === 0) return null;
  const xs = all.map(([x]) => x);
  const ys = all.map(([, y]) => y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(0, ...ys);
  const maxY = Math.max(...ys);
  const sx = (x: number) =>
    pad + ((x - minX) / Math.max(maxX - minX, 1e-9)) * (width - 2 * pad);
  const sy = (y: number) =>
    height - pad - ((y - minY) / Math.max(maxY - minY, 1e-9)) * (height - 2 * pad);
  const bar = chart.mark === "bar";
  return (
    <div className="my-2 rounded border border-slate-200 bg-white p-2">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
        <line x1={pad} y1={sy(minY)} x2={width - pad} y2={sy(minY)} stroke="#cbd5e1" />
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="#cbd5e1" />
        <text x={pad - 4} y={sy(maxY) + 4} textAnchor="end" fontSize="10" fill="#64748b">
          {maxY}
        </text>
        <text x={pad - 4} y={sy(minY) + 4} textAnchor="end" fontSize="10" fill="#64748b">
          {minY}
        </text>
        {chart.series.map((series, index) => {
          const color = CHART_COLORS[index % CHART_COLORS.length];
          if (bar) {
            const groups = series.points.length;
            const band = (width - 2 * pad) / Math.max(groups, 1);
            const barWidth = Math.max(band / (chart.series.length + 1), 2);
            return series.points.map(([, y], pointIndex) => (
              <rect
                key={`${index}-${pointIndex}`}
                x={pad + pointIndex * band + index * barWidth}
                y={sy(y)}
                width={barWidth}
                height={Math.max(sy(minY) - sy(y), 1)}
                fill={color}
              />
            ));
          }
          const path = series.points
            .map(([x, y], pointIndex) => `${pointIndex === 0 ? "M" : "L"}${sx(x)},${sy(y)}`)
            .join(" ");
          return <path key={index} d={path} fill="none" stroke={color} strokeWidth={1.5} />;
        })}
      </svg>
      <div className="mt-1 flex flex-wrap gap-3 text-[10px] text-slate-600">
        {chart.series.map((series, index) => (
          <span key={series.name} className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-sm"
              style={{ background: CHART_COLORS[index % CHART_COLORS.length] }}
            />
            {series.name}
          </span>
        ))}
      </div>
    </div>
  );
}

/** `[3/20]` (bevorzugt) oder freistehendes `3/20` in den letzten Zeilen. */
function detectProgress(items: OutputItem[]): string | null {
  const tail = items.slice(-25);
  for (let index = tail.length - 1; index >= 0; index -= 1) {
    const item = tail[index];
    if (item.kind !== "line") continue;
    const bracket = item.text.match(/\[(\d+)\/(\d+)\]/);
    if (bracket) return `${bracket[1]}/${bracket[2]}`;
    const bare = item.text.match(/(?:^|\s)(\d+)\/(\d+)(?:\s|$)/);
    if (bare) return `${bare[1]}/${bare[2]}`;
  }
  return null;
}

function substitute(command: string, values: Record<string, string>): string {
  return command.replace(/\{([^}]+)\}/g, (whole, name: string) => values[name] ?? whole);
}

function InputField({
  input,
  value,
  onChange,
}: {
  input: ActionInput;
  value: string;
  onChange: (next: string) => void;
}) {
  const label = input.label ?? input.name;
  if (input.kind === "choice" && (input.options?.length ?? 0) > 0) {
    return (
      <label className="flex items-center gap-1.5 text-xs text-slate-600">
        {label}
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="rounded border border-slate-300 px-2 py-1"
        >
          <option value="">—</option>
          {input.options?.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
    );
  }
  if (input.kind === "file" || input.kind === "folder") {
    return (
      <label className="flex items-center gap-1.5 text-xs text-slate-600">
        {label}
        <button
          type="button"
          onClick={() =>
            void openDialog({ directory: input.kind === "folder" }).then((picked) => {
              if (typeof picked === "string") onChange(picked);
            })
          }
          className="max-w-48 truncate rounded border border-slate-300 px-2 py-1 font-mono"
          title={value}
        >
          {value || "wählen…"}
        </button>
      </label>
    );
  }
  if (input.kind === "color") {
    return (
      <label className="flex items-center gap-1.5 text-xs text-slate-600">
        {label}
        <input
          type="color"
          value={value || "#000000"}
          onChange={(event) => onChange(event.target.value)}
        />
      </label>
    );
  }
  return (
    <label className="flex items-center gap-1.5 text-xs text-slate-600">
      {label}
      <input
        value={value}
        type={input.kind === "number" ? "number" : "text"}
        onChange={(event) => onChange(event.target.value)}
        spellCheck={false}
        className="w-32 rounded border border-slate-300 px-2 py-1 font-mono"
      />
    </label>
  );
}

function OutputPanel({ run, onStop }: { run: RunState; onStop: () => void }) {
  const scroller = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const node = scroller.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [run.items.length, run.running]);
  const progress = run.running ? detectProgress(run.items) : null;
  return (
    <div className="mt-2 rounded-lg border border-slate-700 bg-slate-900 p-2">
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="text-slate-400">
          {run.running
            ? progress
              ? `läuft … ${progress}`
              : "läuft …"
            : run.error
              ? `Fehler: ${run.error}`
              : `exit ${run.exitCode ?? "?"} · ${Math.round((run.durationMs ?? 0) / 1000)}s`}
        </span>
        {run.running ? (
          <button
            onClick={onStop}
            className="rounded bg-red-700 px-2 py-0.5 text-[11px] text-white hover:bg-red-600"
          >
            Stop
          </button>
        ) : null}
      </div>
      <div ref={scroller} className="max-h-64 overflow-y-auto">
        {run.items.map((item, index) =>
          item.kind === "chart" ? (
            <ChartBlock key={index} chart={item.chart} />
          ) : (
            <div key={index} className="whitespace-pre-wrap font-mono text-[11px] leading-4 text-slate-200">
              {item.text}
            </div>
          ),
        )}
      </div>
    </div>
  );
}

export default function ActionsTab({
  project,
  refresh,
}: {
  project: string;
  refresh?: number;
}) {
  const snapshot = useAsync(
    () => invoke<ActionsSnapshot>("project_actions", { project }),
    `actions:${project}`,
  );
  const [runs, setRuns] = useState<Record<string, RunState>>({});
  const [inputValues, setInputValues] = useState<Record<string, Record<string, string>>>({});
  const [draft, setDraft] = useState({ name: "", command: "", description: "" });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (refresh) void snapshot.reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  useEffect(() => {
    const outputPromise = listen<{ run_id: string; line: string }>("action-output", (event) => {
      const { run_id, line } = event.payload;
      setRuns((previous) => {
        const run = previous[run_id];
        if (!run) return previous;
        const chart = parseChart(line);
        const item: OutputItem = chart ? { kind: "chart", chart } : { kind: "line", text: line };
        const items = [...run.items, item].slice(-MAX_ITEMS);
        return { ...previous, [run_id]: { ...run, items } };
      });
    });
    const exitPromise = listen<{
      run_id: string;
      exit_code: number | null;
      duration_ms: number;
      error: string | null;
    }>("action-exit", (event) => {
      const { run_id, exit_code, duration_ms, error } = event.payload;
      setRuns((previous) => {
        const run = previous[run_id];
        if (!run) return previous;
        return {
          ...previous,
          [run_id]: {
            ...run,
            running: false,
            exitCode: exit_code,
            durationMs: duration_ms,
            error,
          },
        };
      });
    });
    return () => {
      void outputPromise.then((dispose) => dispose());
      void exitPromise.then((dispose) => dispose());
    };
  }, []);

  const start = async (action: ProjectAction) => {
    setError(null);
    const values = inputValues[action.command] ?? {};
    const commandLine = substitute(action.command, values);
    setRuns((previous) => ({
      ...previous,
      [action.command]: {
        items: [],
        running: true,
        exitCode: null,
        durationMs: null,
        error: null,
      },
    }));
    try {
      await invoke("project_action_run", {
        project,
        runId: action.command,
        commandLine,
      });
    } catch (e) {
      setRuns((previous) => ({
        ...previous,
        [action.command]: {
          items: [],
          running: false,
          exitCode: null,
          durationMs: null,
          error: String(e),
        },
      }));
    }
  };

  const mutate = async (call: () => Promise<unknown>) => {
    setError(null);
    try {
      await call();
      await snapshot.reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const actions = snapshot.data?.actions ?? [];
  const confirmed = actions.filter((action) => action.confirmed);
  const proposals = actions.filter((action) => !action.confirmed);
  const pending = snapshot.data?.pending ?? [];

  const runnable = (action: ProjectAction) =>
    action.target === "local" && !action.command.startsWith("toolui:");

  return (
    <LoadingBoundary loading={snapshot.loading} error={snapshot.error} label="Aktionen lesen…">
      <div className="max-w-3xl space-y-5 overflow-y-auto pr-1">
        {error ? <p className="text-xs text-red-600">{error}</p> : null}

        <section>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Aktionen ({confirmed.length})
          </h2>
          {confirmed.length === 0 ? (
            <p className="text-sm text-slate-500">
              Keine Aktionen in <code>.agent/actions.json</code> — unten anlegen, oder den
              Agenten bitten, welche vorzuschlagen.
            </p>
          ) : (
            <div className="space-y-3">
              {confirmed.map((action) => {
                const run = runs[action.command];
                return (
                  <div key={action.command} className="rounded-lg border border-slate-200 bg-white p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="text-sm font-semibold text-slate-800">{action.name}</h3>
                        {action.description ? (
                          <p className="text-xs text-slate-500">{action.description}</p>
                        ) : null}
                        <p className="mt-1 truncate font-mono text-[11px] text-slate-400">
                          {action.command}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        {action.target === "parallels" ? (
                          <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] text-slate-600">
                            Parallels — folgt
                          </span>
                        ) : null}
                        {action.command.startsWith("toolui:") ? (
                          <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] text-slate-600">
                            App-Panel — folgt
                          </span>
                        ) : null}
                        {runnable(action) ? (
                          <button
                            onClick={() => void start(action)}
                            disabled={run?.running}
                            className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
                          >
                            {run?.running ? "läuft…" : "Ausführen"}
                          </button>
                        ) : null}
                        <button
                          onClick={() =>
                            void mutate(() =>
                              invoke("project_action_delete", {
                                project,
                                command: action.command,
                              }),
                            )
                          }
                          className="rounded px-2 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-red-600"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                    {(action.inputs?.length ?? 0) > 0 ? (
                      <div className="mt-2 flex flex-wrap gap-3">
                        {action.inputs?.map((input) => (
                          <InputField
                            key={input.name}
                            input={input}
                            value={inputValues[action.command]?.[input.name] ?? input.default ?? ""}
                            onChange={(next) =>
                              setInputValues((previous) => ({
                                ...previous,
                                [action.command]: {
                                  ...previous[action.command],
                                  [input.name]: next,
                                },
                              }))
                            }
                          />
                        ))}
                      </div>
                    ) : null}
                    {run ? (
                      <OutputPanel
                        run={run}
                        onStop={() =>
                          void invoke("project_action_stop", { runId: action.command })
                        }
                      />
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {proposals.length > 0 || pending.length > 0 ? (
          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Vorschläge des Agenten ({proposals.length + pending.length})
            </h2>
            <div className="space-y-2">
              {proposals.map((action) => (
                <div
                  key={action.command}
                  className="flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-amber-900">{action.name}</p>
                    <p className="truncate font-mono text-[11px] text-amber-700">
                      {action.command}
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      void mutate(() =>
                        invoke("project_action_confirm", { project, command: action.command }),
                      )
                    }
                    className="shrink-0 rounded bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
                  >
                    Bestätigen
                  </button>
                </div>
              ))}
              {pending.map((entry) => (
                <div
                  key={entry.command}
                  className="flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="truncate font-mono text-xs text-amber-900">{entry.command}</p>
                    <p className="text-[11px] text-amber-700">
                      Vom Exec-Server abgelehnt{entry.requested_at ? ` · ${entry.requested_at}` : ""}
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      void mutate(() =>
                        invoke("project_action_confirm", { project, command: entry.command }),
                      )
                    }
                    className="shrink-0 rounded bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
                  >
                    Bestätigen + freigeben
                  </button>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <section>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Neue Aktion
          </h2>
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-xs text-slate-600">
              Name
              <input
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                className="mt-0.5 block w-40 rounded border border-slate-300 px-2 py-1.5 text-sm"
              />
            </label>
            <label className="text-xs text-slate-600">
              Kommando (argv, ohne Shell)
              <input
                value={draft.command}
                onChange={(event) => setDraft({ ...draft, command: event.target.value })}
                spellCheck={false}
                className="mt-0.5 block w-72 rounded border border-slate-300 px-2 py-1.5 font-mono text-sm"
              />
            </label>
            <label className="text-xs text-slate-600">
              Beschreibung
              <input
                value={draft.description}
                onChange={(event) => setDraft({ ...draft, description: event.target.value })}
                className="mt-0.5 block w-56 rounded border border-slate-300 px-2 py-1.5 text-sm"
              />
            </label>
            <button
              onClick={() =>
                void mutate(async () => {
                  await invoke("project_action_upsert", {
                    project,
                    action: {
                      name: draft.name,
                      command: draft.command,
                      description: draft.description || null,
                      source: "bo",
                      confirmed: true,
                      toolbar: false,
                      shortcut: null,
                      inputs: [],
                      target: "local",
                    },
                  });
                  setDraft({ name: "", command: "", description: "" });
                })
              }
              disabled={draft.name.trim() === "" || draft.command.trim() === ""}
              className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              Anlegen
            </button>
          </div>
        </section>
      </div>
    </LoadingBoundary>
  );
}
