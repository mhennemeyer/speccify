// Workflow-Setup-Banner (Plan projektfenster.md, P5/W1): zeigt, ob die
// Agent-Einweisung (Policy-Block, Spec-Skills, Scaffold, Host-Verweise)
// fehlt oder veraltet ist — Einrichten bewusst per Knopf, nie automatisch,
// weil in Projektdateien geschrieben wird.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { trackActivity } from "../../lib/activity";
import { useAsync } from "../../components/ui";

interface WorkflowStatus {
  state: "missing" | "outdated" | "current";
  installed_version: number | null;
  current_version: number;
  pending: string[];
  issues?: { path: string; kind: string; action: "install" | "manual"; message: string }[];
}

export default function WorkflowBanner({ project, refresh }: { project: string; refresh?: number }) {
  const { data, reload } = useAsync(
    () => invoke<WorkflowStatus>("project_workflow_status", { project }),
    `workflow:${project}`,
  );
  useEffect(() => {
    if (refresh) void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!data || data.state === "current") return null;

  // Manuell zu prüfende Punkte kann install nicht beheben — trennen.
  const issues = data.issues ?? data.pending.map((message) => ({
    path: message, kind: "legacy", action: message.includes("manuell") ? "manual" : "install", message,
  }));
  const manual = issues.filter((entry) => entry.action === "manual");
  const installable = issues.filter((entry) => entry.action === "install");

  const install = async () => {
    setBusy(true);
    setError(null);
    try {
      await trackActivity("setup", "Workflow einrichten", () =>
        invoke("project_workflow_install", { project }),
      );
      await reload();
    } catch (e) {
      setError(String(e));
      await reload();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="text-xs text-amber-900">
          <p className="font-semibold">
            {data.state === "missing"
              ? "Agent-Workflow ist noch nicht eingerichtet."
              : data.installed_version !== null && data.installed_version < data.current_version
                ? `Agent-Workflow aktualisieren (v${data.installed_version} → v${data.current_version}).`
                : "Workflow-Einrichtung braucht Prüfung."}
          </p>
          {installable.length > 0 ? (
            <p className="mt-1">
              Einrichten: {installable.map((entry) => entry.message).join(" · ")}.
              Bekannte Vorlagen werden aktualisiert; eigene Änderungen bleiben erhalten.
            </p>
          ) : null}
          {manual.map((entry) => (
            <p key={entry.path} className="mt-1 text-amber-700">
              ⚠ {entry.message}
            </p>
          ))}
          {error ? <p className="mt-1 text-red-700">{error}</p> : null}
        </div>
        {installable.length > 0 ? (
          <button
            onClick={() => void install()}
            disabled={busy}
            className="shrink-0 rounded bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {busy ? "Richtet ein…" : "Einrichten"}
          </button>
        ) : null}
      </div>
    </div>
  );
}
