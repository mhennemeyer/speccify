// MCPs-Tab: projektbezogene MCP-Server aus den nativen Host-Dateien —
// Claude `.mcp.json`, Codex `.codex/config.toml` — plus Claude-Allowlist.
// W7: Server als Liste im Navigator, Details im Inspektor; ohne Inhalte
// ein Leerzustand mit dem nächsten Schritt (Prompt für den Agenten).

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";
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

interface McpInfo {
  claude_servers: Record<string, unknown> | null;
  codex_servers: Record<string, unknown> | null;
  claude_allow: string[];
  claude_allow_local: string[];
}

interface ServerEntry {
  key: string;
  host: "claude" | "codex";
  name: string;
  config: Record<string, unknown>;
}

const ADD_MCP_PROMPT = `Bitte richte in diesem Projekt einen MCP-Server ein:
- Für Claude Code in \`.mcp.json\` (Feld \`mcpServers\`),
- für Codex in \`.codex/config.toml\` (Tabelle \`[mcp_servers.<name>]\`).
Frag mich, welcher Server (Kommando oder URL) es sein soll, und trag ihn in beide Dateien ein.`;

function describe(config: Record<string, unknown>): string {
  const url = typeof config.url === "string" ? config.url : null;
  if (url) return url;
  const command = [config.command, ...((config.args as string[]) ?? [])]
    .filter(Boolean)
    .join(" ");
  return command;
}

function ServerCard({ entry }: { entry: ServerEntry }) {
  const line = describe(entry.config);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <h3 className="text-sm font-semibold text-slate-800">{entry.name}</h3>
      {line ? <p className="mt-1 font-mono text-xs text-slate-600">{line}</p> : null}
      {typeof entry.config.type === "string" ? (
        <p className="mt-1 text-[11px] text-slate-400">type: {entry.config.type}</p>
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

export default function McpsTab({ project, refresh }: { project: string; refresh?: number }) {
  const { data, loading, error, reload } = useAsync(
    () => invoke<McpInfo>("project_mcps", { project }),
    `mcps:${project}`,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const inspector = useInspector("mcps");

  useEffect(() => {
    if (refresh) void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  const servers: ServerEntry[] = [
    ...Object.entries(data?.claude_servers ?? {}).map(([name, config]) => ({
      key: `claude:${name}`,
      host: "claude" as const,
      name,
      config: config as Record<string, unknown>,
    })),
    ...Object.entries(data?.codex_servers ?? {}).map(([name, config]) => ({
      key: `codex:${name}`,
      host: "codex" as const,
      name,
      config: config as Record<string, unknown>,
    })),
  ];
  const allow = data?.claude_allow ?? [];
  const allowLocal = data?.claude_allow_local ?? [];
  const empty = servers.length === 0 && allow.length === 0 && allowLocal.length === 0;
  const current = servers.find((entry) => entry.key === selected) ?? null;

  const copyAddPrompt = async () => {
    await writeText(ADD_MCP_PROMPT);
    setNotice("Prompt in der Zwischenablage — ins Agent-Terminal einfügen.");
  };

  const navigator = (
    <NavigatorPortal tab="mcps">
      {servers.length === 0 ? (
        <NavEmpty
          title="Keine projekteigenen MCPs"
          action={{ label: "Prompt für den Agenten kopieren", onClick: () => void copyAddPrompt() }}
        >
          MCP-Server dieses Projekts stehen in <code>.mcp.json</code> (Claude) und{" "}
          <code>.codex/config.toml</code> (Codex). Am einfachsten trägt der Agent sie
          ein — der Prompt sagt ihm, wie. Globale Server verwaltet das Dashboard
          unter <em>Server</em>.
        </NavEmpty>
      ) : (
        <div className="space-y-0.5">
          {servers.map((entry) => (
            <NavRow
              key={entry.key}
              selected={selected === entry.key}
              onClick={() => {
                setSelected(entry.key);
                inspector.reveal();
              }}
              subtitle={describe(entry.config)}
              trailing={
                <span className="rounded-full bg-slate-100 px-1.5 text-[10px] text-slate-500">
                  {entry.host}
                </span>
              }
            >
              {entry.name}
            </NavRow>
          ))}
        </div>
      )}
    </NavigatorPortal>
  );

  const details = current ? (
    <InspectorPortal tab="mcps" fallback={inlineInspector}>
      <InspectorPanel
        title={current.name}
        subtitle={current.host === "claude" ? ".mcp.json" : ".codex/config.toml"}
        meta={[
          { label: "Host", value: current.host === "claude" ? "Claude Code" : "Codex" },
          {
            label: typeof current.config.url === "string" ? "URL" : "Kommando",
            value: <span className="font-mono">{describe(current.config) || "—"}</span>,
          },
          ...(typeof current.config.type === "string"
            ? [{ label: "Typ", value: String(current.config.type) }]
            : []),
        ]}
        actions={
          <InspectorButton
            title="Konfiguration als JSON in die Zwischenablage"
            onClick={() => void writeText(JSON.stringify(current.config, null, 2))}
          >
            Konfiguration kopieren
          </InspectorButton>
        }
      >
        <pre className="overflow-x-auto rounded bg-slate-100 p-2 font-mono text-[11px] text-slate-700">
          {JSON.stringify(current.config, null, 2)}
        </pre>
      </InspectorPanel>
    </InspectorPortal>
  ) : null;

  return (
    <LoadingBoundary loading={loading} error={error} label="MCPs lesen…">
      <div className="flex h-full min-h-0 gap-4">
        {navigator}
        <div className="min-w-0 flex-1 overflow-y-auto">
          {details}
          {notice ? (
            <p className="mb-3 rounded bg-sky-50 px-3 py-2 text-xs text-sky-800">{notice}</p>
          ) : null}
          {empty ? (
            <div className="max-w-xl space-y-3 text-sm text-slate-600">
              <p>
                Weder <code>.mcp.json</code> noch <code>.codex/config.toml</code> oder eine
                Claude-Allowlist — dieses Projekt bringt keine eigenen MCPs mit.
              </p>
              <p>
                <button
                  onClick={() => void copyAddPrompt()}
                  className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
                >
                  Prompt für den Agenten kopieren
                </button>
              </p>
            </div>
          ) : (
            <div className="max-w-2xl space-y-5">
              {current ? (
                <ServerCard entry={current} />
              ) : (
                servers.map((entry) => <ServerCard key={entry.key} entry={entry} />)
              )}
              <AllowList title="Claude-Allowlist (.claude/settings.json)" entries={allow} />
              <AllowList
                title="Claude-Allowlist (.claude/settings.local.json)"
                entries={allowLocal}
              />
            </div>
          )}
        </div>
      </div>
    </LoadingBoundary>
  );
}
