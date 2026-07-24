// Server: MCP-Server aus der Registry starten/stoppen (via CLI) +
// P0.1-Spike: Rust-Supervisor mit Live-Log-Streaming über Tauri-Events.

import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { fetchServers, runDotagent } from "../lib/dotagent";
import {
  ActionButton,
  ErrorBox,
  LoadingBoundary,
  Spinner,
  useAsync,
} from "../components/ui";

const SPIKE_ID = "spike-ticker";

export default function ServersView() {
  const { data, loading, refreshing, error, reload } = useAsync(fetchServers, "servers");
  const [actionError, setActionError] = useState<string | null>(null);
  const [logs, setLogs] = useState<Record<string, string>>({});
  const [configs, setConfigs] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState<string | null>(null);

  const servers = data?.servers ?? [];

  const act = async (slug: string, action: "start" | "stop") => {
    setActionError(null);
    try {
      await runDotagent(["mcp", action, slug]);
      await reload();
    } catch (e) {
      setActionError(String(e));
    }
  };

  const showLogs = async (slug: string) => {
    const output = await runDotagent(["mcp", "logs", slug, "-n", "20"]);
    setLogs((prev) => ({ ...prev, [slug]: output }));
  };

  const showConfig = async (slug: string) => {
    try {
      const snippet = await runDotagent(["mcp", "client-config", slug]);
      setConfigs((prev) => ({ ...prev, [slug]: snippet.trim() }));
    } catch (e) {
      setActionError(String(e));
    }
  };

  const copyConfig = async (slug: string) => {
    await navigator.clipboard.writeText(configs[slug]);
    setCopied(slug);
    setTimeout(() => setCopied(null), 1500);
  };

  return (
    <div className="space-y-6">
      {actionError && <ErrorBox message={actionError} />}

      <div className="flex items-center gap-2">
        <ActionButton
          onClick={reload}
          className="bg-slate-800 text-white hover:bg-slate-700"
        >
          Aktualisieren
        </ActionButton>
        {refreshing && <Spinner />}
      </div>

      <LoadingBoundary loading={loading} error={error} label="Server werden geladen…">
        <section className="space-y-3">
          {servers.map((s) => (
            <article
              key={s.slug}
              className="rounded-lg border border-slate-200 bg-white p-4"
            >
              <div className="flex items-center gap-3">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    s.running ? "bg-green-500" : "bg-slate-300"
                  }`}
                />
                <h3 className="font-medium text-slate-900">{s.name}</h3>
                <span className="text-xs text-slate-400">
                  {s.slug}
                  {s.pid ? ` · PID ${s.pid}` : ""}
                </span>
                <div className="ml-auto flex gap-2">
                  <ActionButton
                    onClick={() => act(s.slug, s.running ? "stop" : "start")}
                    className={
                      s.running
                        ? "bg-red-600 text-white hover:bg-red-500"
                        : "bg-green-600 text-white hover:bg-green-500"
                    }
                  >
                    {s.running ? "Stop" : "Start"}
                  </ActionButton>
                  <ActionButton onClick={() => showLogs(s.slug)}>Logs</ActionButton>
                  <ActionButton onClick={() => showConfig(s.slug)}>
                    Client-Config
                  </ActionButton>
                </div>
              </div>
              {logs[s.slug] !== undefined && (
                <pre className="mt-3 max-h-40 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
                  {logs[s.slug] || "(leer)"}
                </pre>
              )}
              {configs[s.slug] !== undefined && (
                <div className="mt-3">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-xs text-slate-500">
                      Snippet für <code>.mcp.json</code> (Claude Code) u. a. MCP-Clients
                    </span>
                    <button
                      onClick={() => copyConfig(s.slug)}
                      className="rounded bg-slate-800 px-2 py-0.5 text-xs text-white hover:bg-slate-700"
                    >
                      {copied === s.slug ? "✓ kopiert" : "Kopieren"}
                    </button>
                  </div>
                  <pre className="max-h-40 overflow-auto rounded bg-slate-900 p-3 text-xs text-sky-200">
                    {configs[s.slug]}
                  </pre>
                </div>
              )}
            </article>
          ))}
          {servers.length === 0 && (
            <p className="text-slate-500">Keine MCP-Server in der Registry.</p>
          )}
        </section>
      </LoadingBoundary>

      <SpikePanel />
    </div>
  );
}

/** P0.1-Akzeptanz: Spawn → Live-Log-Stream → Kill, rein über den Rust-Supervisor. */
function SpikePanel() {
  const [lines, setLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [starting, setStarting] = useState(false);
  const unlistenRef = useRef<UnlistenFn | null>(null);

  useEffect(() => {
    return () => {
      unlistenRef.current?.();
      invoke("kill_process", { id: SPIKE_ID }).catch(() => {});
    };
  }, []);

  const start = async () => {
    setStarting(true);
    setLines([]);
    try {
      unlistenRef.current = await listen<{ id: string; line: string }>(
        "proc-log",
        (event) => {
          if (event.payload.id !== SPIKE_ID) return;
          setLines((prev) => [...prev.slice(-100), event.payload.line]);
        },
      );
      await invoke("spawn_process", {
        id: SPIKE_ID,
        command: "/bin/sh",
        args: [
          "-c",
          'i=0; while true; do i=$((i+1)); echo "tick $i"; sleep 1; done',
        ],
      });
      setRunning(true);
    } finally {
      setStarting(false);
    }
  };

  const stop = async () => {
    await invoke("kill_process", { id: SPIKE_ID });
    unlistenRef.current?.();
    unlistenRef.current = null;
    setRunning(false);
  };

  return (
    <section className="rounded-lg border border-dashed border-slate-300 p-4">
      <div className="flex items-center gap-3">
        <h3 className="font-medium text-slate-700">
          P0.1-Spike: Rust-Supervisor (Spawn / Stream / Kill)
        </h3>
        <button
          onClick={running ? stop : start}
          disabled={starting}
          className={`ml-auto rounded px-3 py-1 text-sm text-white disabled:opacity-60 ${
            running ? "bg-red-600 hover:bg-red-500" : "bg-slate-800 hover:bg-slate-700"
          }`}
        >
          {starting ? <Spinner /> : running ? "Ticker stoppen" : "Ticker starten"}
        </button>
      </div>
      {lines.length > 0 && (
        <pre className="mt-3 max-h-32 overflow-auto rounded bg-slate-900 p-3 text-xs text-green-300">
          {lines.join("\n")}
        </pre>
      )}
    </section>
  );
}
