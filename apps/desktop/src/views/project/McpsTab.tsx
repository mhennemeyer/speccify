// MCPs-Tab (Plan projektfenster.md, P3/F2): projektbezogene MCP-Server aus
// .mcp.json und die Claude-Allowlist aus .claude/settings(.local).json —
// lesend. Globale Server verwaltet weiterhin das Dashboard.

import { invoke } from "@tauri-apps/api/core";
import { LoadingBoundary, useAsync } from "../../components/ui";

interface McpInfo {
  servers: Record<string, unknown> | null;
  allow: string[];
  allow_local: string[];
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

export default function McpsTab({ project }: { project: string }) {
  const { data, loading, error } = useAsync(
    () => invoke<McpInfo>("project_mcps", { project }),
    `mcps:${project}`,
  );

  const servers = Object.entries(data?.servers ?? {});
  const allow = data?.allow ?? [];
  const allowLocal = data?.allow_local ?? [];
  const empty = servers.length === 0 && allow.length === 0 && allowLocal.length === 0;

  return (
    <LoadingBoundary loading={loading} error={error} label="MCPs lesen…">
      {empty ? (
        <p className="text-sm text-slate-500">
          Weder <code>.mcp.json</code> noch eine Allowlist in{" "}
          <code>.claude/settings.json</code> — dieses Projekt bringt keine
          eigenen MCPs mit.
        </p>
      ) : (
        <div className="max-w-2xl space-y-5 overflow-y-auto">
          {servers.length > 0 ? (
            <div>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Server (.mcp.json)
              </h2>
              <div className="space-y-2">
                {servers.map(([name, config]) => (
                  <ServerCard key={name} name={name} config={config} />
                ))}
              </div>
            </div>
          ) : null}
          <AllowList title="Allowlist (.claude/settings.json)" entries={allow} />
          <AllowList title="Allowlist (.claude/settings.local.json)" entries={allowLocal} />
        </div>
      )}
    </LoadingBoundary>
  );
}
