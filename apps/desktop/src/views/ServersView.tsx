// Server: Toolbox-MCPs mit Laufzeitstatus (Port-Probe), Start/Stop über den
// Rust-Supervisor und Client-Config zum Kopieren — komplett nativ (T8);
// die dotagent-CLI ist hier raus.

import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";
import type { ToolboxManifest } from "../lib/toolbox";
import {
  ActionButton,
  ErrorBox,
  LoadingBoundary,
  Spinner,
  useAsync,
} from "../components/ui";

interface McpServerStatus {
  manifest: ToolboxManifest;
  port: number | null;
  running: boolean | null;
  binary_found: boolean;
  /// Woher das Binary aufgelöst wurde (R5.1): Sidecar im App-Bundle, PATH,
  /// expliziter Pfad im Manifest oder gar nicht gefunden.
  binary_source: "bundled" | "path" | "explicit" | "missing";
  client_config: unknown;
  supervisor_id: string;
}

const BINARY_SOURCE_LABEL: Record<McpServerStatus["binary_source"], string> = {
  bundled: "mitgeliefert",
  path: "PATH",
  explicit: "Pfad im Manifest",
  missing: "nicht gefunden",
};

const fetchStatus = () => invoke<McpServerStatus[]>("mcp_status");

export default function ServersView() {
  const { data, loading, refreshing, error, reload } = useAsync(fetchStatus, "servers");
  const [actionError, setActionError] = useState<string | null>(null);
  // Von UNS gestartete Server (nur die können wir stoppen; extern
  // gestartete zeigen „läuft (extern)").
  const [startedIds, setStartedIds] = useState<Set<string>>(new Set());
  const [logs, setLogs] = useState<Record<string, string[]>>({});
  const [showConfig, setShowConfig] = useState<Record<string, boolean>>({});
  const [copied, setCopied] = useState<string | null>(null);
  const unlistenRef = useRef<UnlistenFn | null>(null);

  // Supervisor-Logs der von uns gestarteten Server einsammeln.
  useEffect(() => {
    void listen<{ id: string; line: string }>("proc-log", (event) => {
      if (!event.payload.id.startsWith("mcp-")) return;
      setLogs((current) => ({
        ...current,
        [event.payload.id]: [
          ...(current[event.payload.id] ?? []).slice(-60),
          event.payload.line,
        ],
      }));
    }).then((unlisten) => {
      unlistenRef.current = unlisten;
    });
    return () => {
      unlistenRef.current?.();
    };
  }, []);

  const start = async (server: McpServerStatus) => {
    setActionError(null);
    const run = server.manifest.run;
    if (!run) return;
    try {
      setLogs((current) => ({ ...current, [server.supervisor_id]: [] }));
      await invoke("spawn_process", {
        id: server.supervisor_id,
        command: run.command,
        args: run.args,
      });
      setStartedIds((current) => new Set(current).add(server.supervisor_id));
      // Port-Probe braucht einen Moment.
      setTimeout(() => void reload(), 800);
    } catch (e) {
      setActionError(String(e));
    }
  };

  const stop = async (server: McpServerStatus) => {
    setActionError(null);
    try {
      await invoke("kill_process", { id: server.supervisor_id });
      setStartedIds((current) => {
        const next = new Set(current);
        next.delete(server.supervisor_id);
        return next;
      });
      setTimeout(() => void reload(), 500);
    } catch (e) {
      setActionError(String(e));
    }
  };

  const copyConfig = async (server: McpServerStatus) => {
    const snippet = JSON.stringify(
      { [server.manifest.slug]: server.client_config },
      null,
      2,
    );
    await writeText(snippet);
    setCopied(server.manifest.slug);
    setTimeout(() => setCopied(null), 1500);
  };

  const servers = data ?? [];

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
        <span className="text-xs text-slate-400">
          Quelle: Toolbox-Manifeste · Start/Stop über den App-Supervisor
        </span>
      </div>

      <LoadingBoundary loading={loading} error={error} label="Server werden geladen…">
        <section className="space-y-3">
          {servers.map((server) => {
            const startedByUs = startedIds.has(server.supervisor_id);
            const isHttp = server.manifest.run?.transport === "http";
            const serverLogs = logs[server.supervisor_id];
            return (
              <article
                key={server.manifest.slug}
                className="rounded-lg border border-slate-200 bg-white p-4"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      server.running ? "bg-green-500" : "bg-slate-300"
                    }`}
                    title={
                      server.running === null
                        ? "stdio — wird vom Client gestartet"
                        : server.running
                          ? "läuft"
                          : "gestoppt"
                    }
                  />
                  <h3 className="font-medium text-slate-900">{server.manifest.name}</h3>
                  <span className="text-xs text-slate-400">
                    {server.manifest.slug}
                    {server.port ? ` · :${server.port}` : " · stdio"}
                    {server.running && !startedByUs ? " · läuft (extern)" : ""}
                    {server.binary_found
                      ? ` · Binary: ${BINARY_SOURCE_LABEL[server.binary_source]}`
                      : ""}
                  </span>
                  <div className="ml-auto flex gap-2">
                    {isHttp ? (
                      startedByUs ? (
                        <ActionButton
                          onClick={() => stop(server)}
                          className="bg-red-600 text-white hover:bg-red-500"
                        >
                          Stop
                        </ActionButton>
                      ) : (
                        <ActionButton
                          onClick={() => start(server)}
                          className="bg-green-600 text-white hover:bg-green-500"
                          title={
                            server.binary_found
                              ? undefined
                              : "Binary weder im App-Bundle noch im PATH — siehe docs/toolkit.md"
                          }
                        >
                          Start
                        </ActionButton>
                      )
                    ) : (
                      <span className="self-center text-xs text-slate-400">
                        stdio — startet der Client
                      </span>
                    )}
                    <ActionButton
                      onClick={async () =>
                        setShowConfig((current) => ({
                          ...current,
                          [server.manifest.slug]: !current[server.manifest.slug],
                        }))
                      }
                    >
                      Client-Config
                    </ActionButton>
                  </div>
                </div>

                {!server.binary_found && server.manifest.run ? (
                  <p className="mt-2 text-xs text-amber-600">
                    ⚠ <code>{server.manifest.run.command}</code> nicht gefunden — weder
                    im App-Bundle noch im PATH. Aus dem Repo:{" "}
                    <code>./scripts/build_sidecars.sh</code> vor{" "}
                    <code>pnpm run desktop:build</code> (oder{" "}
                    <code>cargo install --path crates/…</code>), siehe docs/toolkit.md.
                  </p>
                ) : null}

                {showConfig[server.manifest.slug] && server.client_config ? (
                  <div className="mt-3">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-xs text-slate-500">
                        Snippet für <code>.mcp.json</code> (Claude Code) u. a. MCP-Clients
                      </span>
                      <button
                        onClick={() => void copyConfig(server)}
                        className="rounded bg-slate-800 px-2 py-0.5 text-xs text-white hover:bg-slate-700"
                      >
                        {copied === server.manifest.slug ? "✓ kopiert" : "Kopieren"}
                      </button>
                    </div>
                    <pre className="max-h-40 overflow-auto rounded bg-slate-900 p-3 text-xs text-sky-200">
                      {JSON.stringify(
                        { [server.manifest.slug]: server.client_config },
                        null,
                        2,
                      )}
                    </pre>
                  </div>
                ) : null}

                {serverLogs !== undefined && serverLogs.length > 0 ? (
                  <pre className="mt-3 max-h-40 overflow-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
                    {serverLogs.join("\n")}
                  </pre>
                ) : null}
              </article>
            );
          })}
          {servers.length === 0 && (
            <p className="text-slate-500">Keine MCP-Server in der Toolbox.</p>
          )}
        </section>
      </LoadingBoundary>
    </div>
  );
}
