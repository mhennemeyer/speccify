// Aktionen-Tab (Plan projektfenster.md, P5/W5, D27/D28): benannte Kommandos
// aus `.agent/actions.json` — bestätigte Aktionen laufen nativ (Spawn im
// Projekt-cwd), Output streamt live, Stop killt. Vorschläge (unbestätigte
// Aktionen + abgelehnte Agent-Befehle aus exec-pending.json) werden mit
// EINEM Klick bestätigt: Aktion + permanenter Allowlist-Eintrag. Eine
// Ausgabezeile `{"kind":"chart",…}` wird live als Diagramm gerendert —
// kaputte Pflichtfelder fallen auf Text zurück, Output geht nie verloren.

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { LoadingBoundary, useAsync } from "../../components/ui";
import {
  InspectorButton,
  InspectorPanel,
  InspectorPortal,
  NavEmpty,
  NavigatorPortal,
  NavRow,
  inlineInspector,
  useInspector,
} from "../../lib/panels";
import { beginActivity, endActivity } from "../../lib/activity";
import { useProjectActivity } from "../../lib/projectActivity";

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
  name: string;
  items: OutputItem[];
  running: boolean;
  exitCode: number | null;
  durationMs: number | null;
  error: string | null;
}

export interface ActionOutputTab {
  id: string;
  name: string;
  running: boolean;
  failed: boolean;
  close: () => void;
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

function OutputPanel({ run, onStop, fill = false }: { run: RunState; onStop: () => void; fill?: boolean }) {
  const scroller = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const node = scroller.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [run.items, run.running]);
  const progress = run.running ? detectProgress(run.items) : null;
  return (
    <div className={`keep-dark border border-slate-700 bg-slate-900 p-2 ${fill ? "flex min-h-0 flex-1 flex-col" : "mt-2 rounded-lg"}`}>
      {fill ? <h2 className="mb-2 break-words text-xs font-semibold text-slate-200">{run.name}</h2> : null}
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
      <div ref={scroller} className={`${fill ? "min-h-0 flex-1" : "max-h-64"} overflow-y-auto break-words`}>
        {run.items.length === 0 && run.running ? <p className="text-xs text-slate-400">Warte auf Ausgabe …</p> : null}
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
  outputSlot,
  activeOutput,
  onOutputTabsChange,
  onRevealOutput,
  runNamespace,
}: {
  project: string;
  refresh?: number;
  outputSlot?: HTMLElement | null;
  activeOutput?: string | null;
  onOutputTabsChange?: (tabs: ActionOutputTab[]) => void;
  onRevealOutput?: (id: string) => void;
  runNamespace?: string;
}) {
  const runPrefix = runNamespace ? `${runNamespace}:` : "";
  const backendRunId = (id: string) => `${runPrefix}${id}`;
  const snapshot = useAsync(
    () => invoke<ActionsSnapshot>("project_actions", { project }),
    `actions:${project}`,
  );
  const [runs, setRuns] = useState<Record<string, RunState>>({});
  const runningIds = useRef(new Set<string>());
  const projectActive = useProjectActivity();
  const listenersReady = useRef<Promise<unknown>>(Promise.resolve());
  // Streaming lines must not rerender the entire project shell.
  const outputTabsKey = JSON.stringify(Object.entries(runs).map(([id, run]) => ({
    id, name: run.name, running: run.running,
    failed: Boolean(run.error) || (run.exitCode !== null && run.exitCode !== 0),
  })));
  useEffect(() => {
    const tabs = JSON.parse(outputTabsKey) as Omit<ActionOutputTab, "close">[];
    onOutputTabsChange?.(tabs.map((tab) => ({
      ...tab,
      close: () => setRuns((previous) => {
        if (runningIds.current.has(tab.id)) return previous;
        const next = { ...previous };
        delete next[tab.id];
        return next;
      }),
    })));
  }, [outputTabsKey, onOutputTabsChange]);
  const [inputValues, setInputValues] = useState<Record<string, Record<string, string>>>({});
  const [draft, setDraft] = useState({ name: "", command: "", description: "" });
  const [error, setError] = useState<string | null>(null);
  // W7: Auswahl aus dem Navigator → Inspektor zeigt Details und Aktionen.
  const [selected, setSelected] = useState<string | null>(null);
  const inspector = useInspector("actions");

  useEffect(() => {
    if (refresh) void snapshot.reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  useEffect(() => {
    const outputPromise = listen<{ run_id: string; line: string }>("action-output", (event) => {
      const { line } = event.payload;
      if (!event.payload.run_id.startsWith(runPrefix)) return;
      const run_id = event.payload.run_id.slice(runPrefix.length);
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
      const { exit_code, duration_ms, error } = event.payload;
      if (!event.payload.run_id.startsWith(runPrefix)) return;
      const run_id = event.payload.run_id.slice(runPrefix.length);
      runningIds.current.delete(run_id);
      const activity = activityIds.current[run_id];
      if (activity) {
        delete activityIds.current[run_id];
        endActivity(
          activity,
          error || (exit_code !== null && exit_code !== 0) ? "error" : "ok",
          error ?? (exit_code !== null && exit_code !== 0 ? `Exit ${exit_code}` : undefined),
        );
      }
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
    listenersReady.current = Promise.all([outputPromise, exitPromise]);
    // A failed subscription is reported in the output tab when a run is requested.
    void listenersReady.current.catch(() => {});
    return () => {
      void outputPromise.then((dispose) => dispose()).catch(() => {});
      void exitPromise.then((dispose) => dispose()).catch(() => {});
    };
  }, []);

  // W7d: Aktivitätsanzeige — run_id → Activity-Id, aufgelöst im exit-Event.
  const activityIds = useRef<Record<string, string>>({});

  const start = async (action: ProjectAction) => {
    onRevealOutput?.(action.command);
    if (runningIds.current.has(action.command)) return;
    runningIds.current.add(action.command);
    setError(null);
    const values = inputValues[action.command] ?? {};
    const commandLine = substitute(action.command, values);
    activityIds.current[action.command] = beginActivity("action", action.name, commandLine);
    setRuns((previous) => ({
      ...previous,
      [action.command]: {
        name: action.name,
        items: [],
        running: true,
        exitCode: null,
        durationMs: null,
        error: null,
      },
    }));
    try {
      await listenersReady.current;
      await invoke("project_action_run", {
        project,
        runId: backendRunId(action.command),
        commandLine,
      });
    } catch (e) {
      runningIds.current.delete(action.command);
      const activity = activityIds.current[action.command];
      if (activity) {
        delete activityIds.current[action.command];
        endActivity(activity, "error", String(e));
      }
      setRuns((previous) => ({
        ...previous,
        [action.command]: {
          ...previous[action.command],
          running: false,
          exitCode: null,
          durationMs: null,
          error: String(e),
        },
      }));
    }
  };

  // W7d: Toolbar-Knöpfe (ProjectShell) starten Aktionen über dieses Event —
  // die Lauf-Mechanik (Events, Output, Stop) bleibt hier an einer Stelle.
  const actionsRef = useRef<ProjectAction[]>([]);
  actionsRef.current = snapshot.data?.actions ?? [];
  const startRef = useRef(start);
  startRef.current = start;
  useEffect(() => {
    const handler = (event: Event) => {
      const command = (event as CustomEvent<string>).detail;
      if (!projectActive.current) return;
      const action = actionsRef.current.find((entry) => entry.command === command);
      if (action && action.confirmed && runnable(action)) void startRef.current(action);
    };
    window.addEventListener("speccify:run-action", handler);
    return () => window.removeEventListener("speccify:run-action", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const stop = async (id: string) => {
    try {
      await invoke("project_action_stop", { runId: backendRunId(id) });
    } catch (e) {
      setRuns((previous) => {
        const run = previous[id];
        if (!run) return previous;
        const item: OutputItem = { kind: "line", text: `Stop fehlgeschlagen: ${String(e)}` };
        return { ...previous, [id]: { ...run, items: [...run.items, item].slice(-MAX_ITEMS) } };
      });
    }
  };

  return (
    <>
      {outputSlot && activeOutput && runs[activeOutput] ? createPortal(
        <OutputPanel key={activeOutput} run={runs[activeOutput]} fill onStop={() => void stop(activeOutput)} />,
        outputSlot,
      ) : null}
    <LoadingBoundary loading={snapshot.loading} error={snapshot.error} label="Aktionen lesen…">
      <div className="max-w-3xl space-y-5 overflow-y-auto pr-1">
        <NavigatorPortal tab="actions" fallback={() => null}>
          {confirmed.length === 0 && proposals.length + pending.length === 0 ? (
            <NavEmpty
              title="Noch keine Aktionen"
              action={{
                label: "+ Aktion anlegen",
                onClick: () =>
                  document
                    .querySelector("[data-new-action]")
                    ?.scrollIntoView({ block: "start", behavior: "smooth" }),
              }}
            >
              Aktionen sind benannte Kommandos aus <code>.agent/actions.json</code> —
              Tests, Build, Start. Die App führt sie mit Live-Ausgabe aus. Unten
              anlegen, oder den Agenten im Terminal bitten, welche vorzuschlagen.
            </NavEmpty>
          ) : (
            <div className="space-y-0.5">
              {confirmed.map((action) => (
                <NavRow
                  key={action.command}
                  selected={selected === action.command}
                  subtitle={action.command}
                  onClick={() => {
                    setSelected(action.command);
                    inspector.reveal();
                    document
                      .querySelector(`[data-action="${CSS.escape(action.command)}"]`)
                      ?.scrollIntoView({ block: "start", behavior: "smooth" });
                  }}
                >
                  {action.name}
                </NavRow>
              ))}
              {proposals.length + pending.length > 0 ? (
                <p className="px-2 pt-2 text-[11px] text-amber-700">
                  {proposals.length + pending.length} Vorschläge des Agenten — unten im Inhalt.
                </p>
              ) : null}
            </div>
          )}
        </NavigatorPortal>
        {(() => {
          const action = confirmed.find((entry) => entry.command === selected);
          if (!action) return null;
          const run = runs[action.command];
          return (
            <InspectorPortal tab="actions" fallback={inlineInspector}>
              <InspectorPanel
                title={action.name}
                subtitle={action.command}
                meta={[
                  { label: "Beschreibung", value: action.description ?? "—" },
                  { label: "Quelle", value: action.source },
                  { label: "Ziel", value: action.target },
                  {
                    label: "Eingaben",
                    value: action.inputs?.length ? action.inputs.map((input) => input.name).join(", ") : "keine",
                  },
                  { label: "Toolbar", value: action.toolbar ? "ja" : "nein" },
                  {
                    label: "Letzter Lauf",
                    value: run
                      ? run.running
                        ? "läuft …"
                        : run.error
                          ? `Fehler: ${run.error}`
                          : `Exit ${run.exitCode ?? "?"}${run.durationMs !== null ? ` · ${Math.round(run.durationMs / 1000)} s` : ""}`
                      : "—",
                  },
                ]}
                actions={
                  <>
                    {runnable(action) ? (
                      <InspectorButton
                        tone="primary"
                        disabled={run?.running}
                        onClick={() => void start(action)}
                      >
                        {run?.running ? "läuft…" : "Ausführen"}
                      </InspectorButton>
                    ) : null}
                    <InspectorButton
                      onClick={() =>
                        void mutate(() =>
                          invoke("project_action_upsert", {
                            project,
                            action: { ...action, toolbar: !action.toolbar },
                          }),
                        )
                      }
                    >
                      {action.toolbar ? "Aus der Toolbar nehmen" : "In die Toolbar"}
                    </InspectorButton>
                  </>
                }
              />
            </InspectorPortal>
          );
        })()}
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
                  <div
                    key={action.command}
                    data-action={action.command}
                    className="rounded-lg border border-slate-200 bg-white p-3"
                  >
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
                            onClick={() =>
                              void mutate(() =>
                                invoke("project_action_upsert", {
                                  project,
                                  action: { ...action, toolbar: !action.toolbar },
                                }),
                              )
                            }
                            title={
                              action.toolbar
                                ? "Aus der Toolbar nehmen"
                                : "Als Knopf in die Toolbar legen"
                            }
                            aria-pressed={Boolean(action.toolbar)}
                            className={`rounded border px-2 py-1 text-xs ${
                              action.toolbar
                                ? "border-slate-700 bg-slate-700 text-white"
                                : "border-slate-300 text-slate-500 hover:bg-slate-100"
                            }`}
                          >
                            Toolbar
                          </button>
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
                    {run && onRevealOutput ? (
                      <button className="mt-2 text-xs text-blue-700 hover:underline" onClick={() => onRevealOutput(action.command)}>
                        Ausgabe anzeigen{run.running ? " · läuft …" : ""}
                      </button>
                    ) : run ? (
                      <OutputPanel
                        run={run}
                        onStop={() =>
                          void stop(action.command)
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

        <section data-new-action>
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
    </>
  );
}
