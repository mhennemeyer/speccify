import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { copyPrompt } from "../lib/prompt";

export default function WorkspaceAgentContext({ revision }: { revision: number }) {
  const [context, setContext] = useState<{ root: string; revision: number; markdown: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    let disposed = false;
    void invoke<{ root: string; revision: number; markdown: string }>("workspace_agent_context")
      .then(value => { if (!disposed) { setContext(value); setError(null); setCopied(false); } })
      .catch(reason => { if (!disposed) { setContext(null); setError(String(reason)); } });
    return () => { disposed = true; };
  }, [revision]);
  return <details className="mx-3 my-1 text-xs text-slate-400">
    <summary className="cursor-pointer">Workspace-Kontext · Vorschau für den nächsten Start</summary>
    {error && <p role="alert">{error}</p>}
    {context && <>
      <p>Stand {context.revision} · Laufende Sitzungen behalten ihren Startkontext. „Neu starten“ lädt die aktuelle Zuordnung.</p>
      <button className="my-1 rounded border border-slate-600 px-2 py-1" onClick={() => void copyPrompt(context.root, context.markdown).then(() => setCopied(true)).catch(reason => setError(String(reason)))}>{copied ? "Kontext kopiert" : "Workspace-Kontext kopieren"}</button>
      <pre className="max-h-40 overflow-auto whitespace-pre-wrap text-[10px]">{context.markdown}</pre>
    </>}
  </details>;
}
