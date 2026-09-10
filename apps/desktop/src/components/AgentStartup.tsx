import { useEffect, useRef, useState } from "react";
import { fetchAgentStartup, type AgentStartupReport } from "../lib/system";

export function StartupDetails({ report }: { report: AgentStartupReport }) {
  const source = { workspace: "Projekt-venv", engine: "App-Engine", shell: "Login-Shell" }[report.runtime_source];
  return (
    <div className="space-y-1 break-words text-xs">
      {report.error ? <p role="alert" className="text-red-500">{report.error}</p> : null}
      <p>Shell: <code>{report.shell}</code></p>
      <p>Agent: <code>{report.host_path ?? (report.host === "shell" ? "nur Shell" : "nicht geprüft")}</code>{report.host_version ? ` · ${report.host_version}` : ""}</p>
      <p>Speccify ({source}): <code>{report.effective_cli ?? "nicht gefunden"}</code></p>
      {report.shell_cli && report.shell_cli !== report.effective_cli ? <p>Shell-Installation: <code>{report.shell_cli}</code></p> : null}
      {report.effective_cli && report.missing_commands.length === 0 ? <p>expand, export, link und tool verfügbar.</p> : null}
      {report.warnings.map(warning => <p key={warning} className="text-amber-600">{warning}</p>)}
    </div>
  );
}

export default function AgentStartup({ project, command }: { project: string; command: string }) {
  const [report, setReport] = useState<AgentStartupReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  useEffect(() => {
    generation.current++;
    setReport(null);
    setError(null);
    setBusy(false);
    return () => { generation.current++; };
  }, [project, command]);
  const check = async () => {
    const current = ++generation.current;
    setBusy(true);
    setError(null);
    try {
      const result = await fetchAgentStartup(project, command);
      if (current === generation.current) setReport(result);
    } catch (e) {
      if (current === generation.current) setError(String(e));
    } finally {
      if (current === generation.current) setBusy(false);
    }
  };
  return (
    <div className="mt-3 space-y-2 text-xs">
      <button type="button" disabled={busy} onClick={() => void check()} className="rounded border border-slate-400 px-2 py-1 disabled:opacity-50">
        {busy ? "Startumgebung wird geprüft…" : "Startumgebung prüfen"}
      </button>
      {error ? <p role="alert" className="text-red-500">{error}</p> : null}
      {report ? <StartupDetails report={report} /> : null}
    </div>
  );
}
