// Agents-Bereich im Dashboard (Plan projektfenster.md, D23): die globale
// Konfiguration der Terminal-Agents anzeigen und editieren. Whitelist im
// Rust-Backend — nur die bekannten Dateien je Host (Claude:
// ~/.claude/settings.json + CLAUDE.md; Codex: ~/.codex/config.toml +
// AGENTS.md). Fehlende Dateien entstehen erst beim Speichern.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { ErrorBox, LoadingBoundary, useAsync } from "../components/ui";

interface AgentConfigFile {
  id: string;
  host: string;
  path: string;
  hint: string;
  exists: boolean;
}

export default function AgentsView() {
  const list = useAsync(() => invoke<AgentConfigFile[]>("agent_config_list"), "agent-configs");
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);

  const files = list.data ?? [];
  const current = files.find((file) => file.id === selected) ?? files[0] ?? null;

  useEffect(() => {
    if (!current || loadedFor === current.id) return;
    setError(null);
    setStatus("");
    void invoke<string>("agent_config_read", { id: current.id })
      .then((text) => {
        setContent(text);
        setLoadedFor(current.id);
        setDirty(false);
      })
      .catch((e) => setError(String(e)));
  }, [current, loadedFor]);

  const save = async () => {
    if (!current) return;
    setError(null);
    try {
      await invoke("agent_config_write", { id: current.id, content });
      setDirty(false);
      setStatus("Gespeichert.");
      void list.reload();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <LoadingBoundary loading={list.loading} error={list.error} label="Agent-Configs suchen…">
      <div className="flex h-full min-h-0 gap-4">
        <nav className="w-64 shrink-0 space-y-3 overflow-y-auto pr-1">
          {["claude", "codex"].map((host) => (
            <div key={host}>
              <h3 className="mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {host}
              </h3>
              <ul className="space-y-1">
                {files
                  .filter((file) => file.host === host)
                  .map((file) => (
                    <li key={file.id}>
                      <button
                        onClick={() => setSelected(file.id)}
                        className={`w-full rounded px-2 py-1.5 text-left ${
                          current?.id === file.id
                            ? "bg-slate-800 text-white"
                            : "text-slate-700 hover:bg-slate-100"
                        }`}
                      >
                        <span className="block truncate font-mono text-xs">{file.path}</span>
                        <span
                          className={`block text-[11px] ${
                            current?.id === file.id ? "text-slate-300" : "text-slate-400"
                          }`}
                        >
                          {file.exists ? file.hint : "existiert noch nicht"}
                        </span>
                      </button>
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="flex min-w-0 flex-1 flex-col">
          {current ? (
            <>
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="truncate font-mono text-xs text-slate-500" title={current.path}>
                  {current.path}
                </p>
                <div className="flex items-center gap-2">
                  {status && !dirty ? (
                    <span className="text-xs text-emerald-600">{status}</span>
                  ) : null}
                  <button
                    onClick={() => void save()}
                    disabled={!dirty}
                    className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-40"
                  >
                    Speichern
                  </button>
                </div>
              </div>
              {error ? <ErrorBox message={error} /> : null}
              <textarea
                value={content}
                onChange={(event) => {
                  setContent(event.target.value);
                  setDirty(true);
                  setStatus("");
                }}
                spellCheck={false}
                placeholder={
                  current.exists ? "" : "Datei existiert noch nicht — Speichern legt sie an."
                }
                className="min-h-0 flex-1 resize-none rounded-lg border border-slate-300 bg-white p-3 font-mono text-xs leading-5"
              />
            </>
          ) : (
            <p className="text-sm text-slate-400">Keine Agent-Configs bekannt.</p>
          )}
        </div>
      </div>
    </LoadingBoundary>
  );
}
