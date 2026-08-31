// MCPs-Tab: projektbezogene MCP-Server aus den nativen Host-Dateien —
// Claude `.mcp.json`, Codex `.codex/config.toml` — plus Claude-Allowlist.

import { useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { LoadingBoundary, useAsync } from "../../components/ui";

interface McpInfo {
  claude_servers: Record<string, unknown> | null;
  codex_servers: Record<string, unknown> | null;
  claude_allow: string[];
  claude_allow_local: string[];
}

function ServerCard({ name, config }: { name: string; config: unknown }) {
  const details = config as Record<string, unknown>;
  const command = [details.command, ...((details.args as string[]) ?? [])]
    .filter(Boolean)
    .join(" ");
  const url = typeof details.url === "string" ? details.url : null;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <h3 className="text-sm font-semibold text-slate-800">{name}</h3>
      {url ? (
        <p className="mt-1 font-mono text-xs text-slate-600">{url}</p>
      ) : command ? (
        <p className="mt-1 font-mono text-xs text-slate-600">{command}</p>
      ) : null}
      {typeof details.type === "string" ? (
        <p className="mt-1 text-[11px] text-slate-400">type: {details.type}</p>
      ) : null}
    </div>
  );
}

function AllowList({ title, entries }: { title: string; entries: string[] }) {
  if (entries.length === 0) return null;
  return (
    <div>
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h3>
      <ul className="space-y-1">
        {entries.map((entry) => (
          <li key={entry} className="rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-700">
            {entry}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ServerSection({
  title,
  servers,
}: {
  title: string;
  servers: Array<[string, unknown]>;
}) {
  if (servers.length === 0) return null;
  return (
    <div>
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      <div className="space-y-2">
        {servers.map(([name, config]) => (
          <ServerCard key={name} name={name} config={config} />
        ))}
      </div>
    </div>
  );
}

export default function McpsTab({ project, refresh }: { project: string; refresh?: number }) {
  const { data, loading, error, reload } = useAsync(
    () => invoke<McpInfo>("project_mcps", { project }),
    `mcps:${project}`,
  );

  useEffect(() => {
    if (refresh) void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  const claudeServers = Object.entries(data?.claude_servers ?? {});
  const codexServers = Object.entries(data?.codex_servers ?? {});
  const allow = data?.claude_allow ?? [];
  const allowLocal = data?.claude_allow_local ?? [];
  const empty =
    claudeServers.length === 0 &&
    codexServers.length === 0 &&
    allow.length === 0 &&
    allowLocal.length === 0;

  return (
    <LoadingBoundary loading={loading} error={error} label="MCPs lesen…">
      {empty ? (
        <p className="text-sm text-slate-500">
          Weder <code>.mcp.json</code> noch <code>.codex/config.toml</code>
          {" "}oder eine Claude-Allowlist — dieses Projekt bringt keine eigenen
          MCPs mit.
        </p>
      ) : (
        <div className="max-w-2xl space-y-5 overflow-y-auto">
          <ServerSection title="Claude (.mcp.json)" servers={claudeServers} />
          <ServerSection title="Codex (.codex/config.toml)" servers={codexServers} />
          <AllowList title="Claude-Allowlist (.claude/settings.json)" entries={allow} />
          <AllowList
            title="Claude-Allowlist (.claude/settings.local.json)"
            entries={allowLocal}
          />
        </div>
      )}
    </LoadingBoundary>
  );
}
